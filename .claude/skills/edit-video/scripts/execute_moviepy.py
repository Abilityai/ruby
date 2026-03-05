#!/usr/bin/env python3
"""
Execute video edits from EDL using MoviePy.

Benefits over raw FFmpeg:
- Clean overlay compositing with CompositeVideoClip
- Automatic audio mixing with CompositeAudioClip
- Easy to add whoosh/transition SFX at B-roll timestamps
- Single encoding pass
- Maintains audio sync

Usage:
    source .claude/skills/edit-video/venv/bin/activate
    python execute_moviepy.py edl.json -o output.mp4
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple

# Skill directory (parent of scripts/)
SKILL_DIR = Path(__file__).parent.parent

# Add venv to path if needed
venv_site_packages = SKILL_DIR / 'venv' / 'lib'
for p in venv_site_packages.glob('python*/site-packages'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    TextClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    concatenate_audioclips,
)
from moviepy.video.fx import Resize, FadeIn, FadeOut
from moviepy import afx
import numpy as np
from scipy.ndimage import gaussian_filter


def apply_overlay_effect(clip, effect: str, duration: float):
    """Apply MoviePy-based overlay transition effects.

    These control how the B-roll enters/exits the frame, separate from
    the internal animation (ken_burns, drift, etc.) baked into the video.

    Effects:
    - slide_left: Slide in from the left
    - slide_right: Slide in from the right
    - slide_up: Slide in from below
    - slide_down: Slide in from above
    - scale_in: Start small, grow to full size
    - fade_in: Simple fade (default behavior)
    - none: No overlay effect
    """
    width, height = clip.size
    transition_time = 0.4  # Duration of the transition effect

    if effect == 'slide_left':
        # Start off-screen left, slide to center
        def position(t):
            if t < transition_time:
                progress = t / transition_time
                # Ease out cubic
                progress = 1 - (1 - progress) ** 3
                x = -width + (width * progress)
            else:
                x = 0
            return (x, 0)
        return clip.with_position(position)

    elif effect == 'slide_right':
        # Start off-screen right, slide to center
        def position(t):
            if t < transition_time:
                progress = t / transition_time
                progress = 1 - (1 - progress) ** 3
                x = width - (width * progress)
            else:
                x = 0
            return (x, 0)
        return clip.with_position(position)

    elif effect == 'slide_up':
        # Start below, slide up
        def position(t):
            if t < transition_time:
                progress = t / transition_time
                progress = 1 - (1 - progress) ** 3
                y = height - (height * progress)
            else:
                y = 0
            return (0, y)
        return clip.with_position(position)

    elif effect == 'slide_down':
        # Start above, slide down
        def position(t):
            if t < transition_time:
                progress = t / transition_time
                progress = 1 - (1 - progress) ** 3
                y = -height + (height * progress)
            else:
                y = 0
            return (0, y)
        return clip.with_position(position)

    elif effect == 'scale_in':
        # Start small, grow to full size
        def resize_func(t):
            if t < transition_time:
                progress = t / transition_time
                # Ease out back (slight overshoot)
                progress = 1 + 1.5 * ((progress - 1) ** 3) + 1.0 * ((progress - 1) ** 2)
                scale = 0.3 + (0.7 * min(progress, 1.0))
            else:
                scale = 1.0
            return scale

        # Apply dynamic resize
        original_clip = clip
        def make_frame(t):
            scale = resize_func(t)
            if scale < 1.0:
                # Resize and center
                new_w, new_h = int(width * scale), int(height * scale)
                resized = original_clip.get_frame(t)
                # Use numpy to resize
                from PIL import Image
                img = Image.fromarray(resized)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                # Create black canvas and paste centered
                canvas = Image.new('RGB', (width, height), (0, 0, 0))
                x = (width - new_w) // 2
                y = (height - new_h) // 2
                canvas.paste(img, (x, y))
                return np.array(canvas)
            return original_clip.get_frame(t)

        from moviepy import VideoClip
        return VideoClip(make_frame, duration=clip.duration).with_fps(clip.fps if hasattr(clip, 'fps') and clip.fps else 30)

    # Default: no overlay effect (internal fade from FFmpeg is enough)
    return clip


def create_zoom_buildup(clip, start_time: float, duration: float, end_zoom: float = 1.08):
    """Create a slow zoom effect on a video segment leading up to B-roll.

    This creates anticipation by slowly zooming into the talking head
    before cutting to B-roll.

    Args:
        clip: Source video clip
        start_time: When the zoom starts (seconds)
        duration: How long the zoom lasts (seconds)
        end_zoom: Final zoom level (1.08 = 8% zoom)

    Returns:
        A clip with progressive zoom applied, positioned at start_time
    """
    # Extract the segment to zoom
    end_time = start_time + duration
    if end_time > clip.duration:
        end_time = clip.duration
        duration = end_time - start_time

    if duration <= 0:
        return None

    segment = clip.subclipped(start_time, end_time)
    width, height = segment.size

    # Create zoom function - starts at 1.0, ends at end_zoom
    def zoom_frame(get_frame, t):
        progress = t / duration if duration > 0 else 0
        # Ease-in-out for smooth acceleration
        progress = progress * progress * (3 - 2 * progress)
        current_zoom = 1.0 + (end_zoom - 1.0) * progress

        frame = get_frame(t)

        # Calculate crop dimensions for zoom effect
        new_w = int(width / current_zoom)
        new_h = int(height / current_zoom)
        x = (width - new_w) // 2
        y = (height - new_h) // 2

        # Crop and resize back to original dimensions
        from PIL import Image
        img = Image.fromarray(frame)
        cropped = img.crop((x, y, x + new_w, y + new_h))
        resized = cropped.resize((width, height), Image.Resampling.LANCZOS)

        return np.array(resized)

    # Apply the zoom transformation
    zoomed = segment.transform(zoom_frame)
    zoomed = zoomed.with_start(start_time)

    return zoomed


def analyze_video_color(clip, at_time: float, sample_duration: float = 1.0) -> dict:
    """Analyze color characteristics of video at a specific timestamp.

    Returns dict with brightness, contrast estimates for color matching.
    """
    try:
        # Sample a few frames around the timestamp
        start = max(0, at_time - sample_duration / 2)
        end = min(clip.duration, at_time + sample_duration / 2)

        # Get frame at the timestamp
        frame = clip.get_frame(at_time)

        # Convert to float for analysis
        frame_float = frame.astype(np.float32) / 255.0

        # Calculate average brightness (luminance)
        # Using standard luminance formula: 0.299*R + 0.587*G + 0.114*B
        luminance = 0.299 * frame_float[:, :, 0] + 0.587 * frame_float[:, :, 1] + 0.114 * frame_float[:, :, 2]
        avg_brightness = np.mean(luminance)

        # Calculate contrast (standard deviation of luminance)
        contrast = np.std(luminance)

        # Calculate color temperature hint (warm vs cool)
        avg_r = np.mean(frame_float[:, :, 0])
        avg_b = np.mean(frame_float[:, :, 2])
        warmth = avg_r - avg_b  # Positive = warm, negative = cool

        return {
            'brightness': avg_brightness,
            'contrast': contrast,
            'warmth': warmth,
            'avg_r': avg_r,
            'avg_g': np.mean(frame_float[:, :, 1]),
            'avg_b': avg_b,
        }
    except Exception as e:
        print(f"    Warning: Color analysis failed: {e}")
        return {'brightness': 0.5, 'contrast': 0.2, 'warmth': 0.0}


def apply_color_correction(clip, target_brightness: float = 0.5, target_warmth: float = 0.0):
    """Apply color correction to match target brightness and warmth.

    For AI-generated B-roll (typically high contrast, pure black background),
    this adjusts to better match talking-head footage.
    """
    def color_correct_frame(frame):
        # Convert to float
        frame_float = frame.astype(np.float32) / 255.0

        # Analyze current frame
        luminance = 0.299 * frame_float[:, :, 0] + 0.587 * frame_float[:, :, 1] + 0.114 * frame_float[:, :, 2]
        current_brightness = np.mean(luminance)

        # Calculate brightness adjustment (subtle - don't over-correct)
        if current_brightness > 0.01:  # Avoid division by zero
            brightness_factor = (target_brightness / current_brightness) ** 0.3  # Dampened adjustment
            brightness_factor = np.clip(brightness_factor, 0.7, 1.4)  # Limit range
        else:
            brightness_factor = 1.0

        # Apply brightness adjustment
        frame_float = frame_float * brightness_factor

        # Apply warmth adjustment (subtle tint)
        warmth_adjust = target_warmth * 0.05  # Very subtle
        frame_float[:, :, 0] = frame_float[:, :, 0] + warmth_adjust  # Add red for warmth
        frame_float[:, :, 2] = frame_float[:, :, 2] - warmth_adjust  # Reduce blue for warmth

        # Clip and convert back
        frame_float = np.clip(frame_float, 0, 1)
        return (frame_float * 255).astype(np.uint8)

    return clip.image_transform(color_correct_frame)


def create_text_overlay(
    main_clip,
    text: str,
    start_time: float,
    duration: float,
    font_size: int = 70,
    font_color: str = 'white',
    position: str = 'center',
    blur_amount: float = 15.0,
    darken: float = 0.4,
    animation: str = 'fade',
    font: str = None,
    text_align: str = 'center',
    style: str = 'blur',
    accent_color: str = '#00ffff',
    stroke_width: int = 2
):
    """Create a text overlay with various background styles.

    Args:
        main_clip: Source video clip
        text: Text to display (supports newlines for lists)
        start_time: When to show the text (seconds)
        duration: How long to show (seconds)
        font_size: Text size in points
        font_color: Text color (name, hex, or RGB tuple)
        position: 'center', 'bottom', 'top', 'lower_third', 'upper_third',
                  'left', 'right', 'bottom_left', 'bottom_right', or tuple (x, y)
        blur_amount: Gaussian blur sigma (higher = more blur)
        darken: Darken factor (0-1, lower = darker)
        animation: 'fade', 'slide_up', 'slide_left', 'slide_right', 'scale',
                   'typewriter', 'pop', or 'none'
        font: Path to font file (None = default)
        text_align: 'center', 'left', or 'right'
        style: 'blur' (blurred bg), 'box' (solid bg box), 'gradient' (gradient bg),
               'outline' (text only with outline), 'lower_third' (news-style bar)
        accent_color: Color for accent elements (bars, highlights)
        stroke_width: Width of text stroke/outline

    Returns:
        List of clips to add to composition (bg clips + text clips)
    """
    clip_size = main_clip.size
    width, height = clip_size
    clips = []

    # Sanitize text - replace Unicode bullets with ASCII equivalents
    text = text.replace('•', '-').replace('✓', '*').replace('→', '>').replace('📍', '*').replace('📝', '*').replace('📧', '*')

    # Extract the segment for background effects
    end_time = min(start_time + duration, main_clip.duration)

    # Safe margins from edges (pixels)
    margin_top = 60
    margin_bottom = 60
    margin_left = 50
    margin_right = 50

    # Calculate text width based on position
    if position in ['left', 'bottom_left']:
        text_width = int(width * 0.45)
    elif position in ['right', 'bottom_right']:
        text_width = int(width * 0.45)
    elif position == 'lower_third':
        text_width = int(width * 0.6)
    else:
        text_width = width - margin_left - margin_right

    # Apply background style
    if style == 'blur':
        # Full-screen blurred/darkened background
        segment = main_clip.subclipped(start_time, end_time)

        def blur_and_darken(frame):
            blurred = np.zeros_like(frame)
            for i in range(3):
                blurred[:, :, i] = gaussian_filter(frame[:, :, i], sigma=blur_amount)
            darkened = (blurred * darken).astype(np.uint8)
            return darkened

        blurred_segment = segment.image_transform(blur_and_darken)
        blurred_segment = blurred_segment.with_start(start_time)
        clips.append(blurred_segment)

    elif style == 'gradient':
        # Create gradient overlay (dark at edges, transparent center)
        segment = main_clip.subclipped(start_time, end_time)

        def apply_gradient(frame):
            # Create radial gradient mask
            y_indices, x_indices = np.ogrid[:height, :width]
            center_y, center_x = height // 2, width // 2
            dist = np.sqrt((x_indices - center_x)**2 + (y_indices - center_y)**2)
            max_dist = np.sqrt(center_x**2 + center_y**2)
            gradient = np.clip(dist / max_dist, 0, 1)

            # Apply gradient darkening
            result = frame.copy().astype(np.float32)
            for i in range(3):
                result[:, :, i] = result[:, :, i] * (1 - gradient * 0.7)
            return result.astype(np.uint8)

        gradient_segment = segment.image_transform(apply_gradient)
        gradient_segment = gradient_segment.with_start(start_time)
        clips.append(gradient_segment)

    elif style == 'lower_third':
        # Create a news-style lower third bar
        from moviepy import ColorClip

        bar_height = int(height * 0.12)
        bar_y = int(height * 0.78)

        # Main bar (semi-transparent dark)
        bar_clip = ColorClip(size=(width, bar_height), color=(20, 20, 20))
        bar_clip = bar_clip.with_opacity(0.85)
        bar_clip = bar_clip.with_duration(duration)
        bar_clip = bar_clip.with_position((0, bar_y))
        bar_clip = bar_clip.with_start(start_time)

        # Accent bar (colored stripe)
        accent_height = 4
        # Parse accent color
        if accent_color.startswith('#'):
            r = int(accent_color[1:3], 16)
            g = int(accent_color[3:5], 16)
            b = int(accent_color[5:7], 16)
            accent_rgb = (r, g, b)
        else:
            accent_rgb = (0, 255, 255)  # Default cyan

        accent_clip = ColorClip(size=(width, accent_height), color=accent_rgb)
        accent_clip = accent_clip.with_duration(duration)
        accent_clip = accent_clip.with_position((0, bar_y))
        accent_clip = accent_clip.with_start(start_time)

        clips.append(bar_clip)
        clips.append(accent_clip)

        # Override position for lower third
        position = (0.05, 0.80)

    elif style == 'box':
        # Semi-transparent box behind text (size determined after text creation)
        pass  # Box will be created after text clip

    # Create text clip
    # IMPORTANT: margin parameter prevents stroke from being cut off (GitHub issue #2268)
    # Margin should be large enough to account for stroke + font descenders/ascenders
    text_margin = max(stroke_width * 3 + 15, 25)  # Generous margin to prevent any clipping

    try:
        txt_clip = TextClip(
            text=text,
            font_size=font_size,
            color=font_color,
            font=font,
            stroke_color='black',
            stroke_width=stroke_width,
            method='caption',
            size=(text_width, None),
            text_align=text_align,
            margin=(text_margin, text_margin)  # Prevents stroke clipping
        )
    except Exception as e:
        txt_clip = TextClip(
            text=text,
            font_size=font_size,
            color=font_color,
            stroke_color='black',
            stroke_width=stroke_width,
            method='caption',
            size=(text_width, None),
            text_align=text_align,
            margin=(text_margin, text_margin)  # Prevents stroke clipping
        )

    # Set duration FIRST (required before applying effects)
    txt_clip = txt_clip.with_duration(duration)

    # Get actual text dimensions for proper positioning
    txt_w, txt_h = txt_clip.size

    # Calculate PIXEL positions (not relative) that ensure text stays within frame
    # This prevents clipping at edges
    if position == 'center':
        pos_x = (width - txt_w) // 2
        pos_y = (height - txt_h) // 2
    elif position == 'bottom':
        pos_x = (width - txt_w) // 2
        pos_y = height - txt_h - margin_bottom
    elif position == 'top':
        pos_x = (width - txt_w) // 2
        pos_y = margin_top
    elif position == 'lower_third':
        pos_x = margin_left
        pos_y = int(height * 0.78)
    elif position == 'upper_third':
        pos_x = (width - txt_w) // 2
        pos_y = int(height * 0.20)
    elif position == 'left':
        pos_x = margin_left
        pos_y = (height - txt_h) // 2
    elif position == 'right':
        pos_x = width - txt_w - margin_right
        pos_y = (height - txt_h) // 2
    elif position == 'bottom_left':
        pos_x = margin_left
        pos_y = height - txt_h - margin_bottom
    elif position == 'bottom_right':
        pos_x = width - txt_w - margin_right
        pos_y = height - txt_h - margin_bottom
    elif isinstance(position, tuple):
        # Tuple is still relative (0-1), convert to pixels
        pos_x = int(position[0] * width)
        pos_y = int(position[1] * height)
        # Clamp to stay within bounds
        pos_x = max(margin_left, min(pos_x, width - txt_w - margin_right))
        pos_y = max(margin_top, min(pos_y, height - txt_h - margin_bottom))
    else:
        pos_x = (width - txt_w) // 2
        pos_y = (height - txt_h) // 2

    # Ensure text stays within frame bounds
    pos_x = max(margin_left, min(pos_x, width - txt_w - margin_right))
    pos_y = max(margin_top, min(pos_y, height - txt_h - margin_bottom))

    # Store final position for animations
    final_pos = (pos_x, pos_y)

    # Apply position using absolute pixel coordinates
    txt_clip = txt_clip.with_position(final_pos)

    # Apply animation
    fade_duration = min(0.4, duration / 5)

    if animation == 'fade':
        txt_clip = txt_clip.with_effects([
            FadeIn(fade_duration),
            FadeOut(fade_duration)
        ])

    elif animation == 'scale':
        def scale_func(t):
            if t < fade_duration:
                return 0.5 + 0.5 * (t / fade_duration)
            elif t > duration - fade_duration:
                return 0.5 + 0.5 * ((duration - t) / fade_duration)
            return 1.0
        txt_clip = txt_clip.resized(scale_func)
        txt_clip = txt_clip.with_effects([FadeIn(fade_duration), FadeOut(fade_duration)])

    elif animation == 'pop':
        # Pop in with overshoot, then fade out
        def scale_func(t):
            if t < fade_duration:
                progress = t / fade_duration
                # Overshoot to 1.1 then settle to 1.0
                return 0.3 + 0.8 * progress + 0.1 * np.sin(progress * np.pi)
            elif t > duration - fade_duration:
                return 1.0 - 0.5 * ((t - (duration - fade_duration)) / fade_duration)
            return 1.0
        txt_clip = txt_clip.resized(scale_func)
        txt_clip = txt_clip.with_effects([FadeIn(fade_duration * 0.5), FadeOut(fade_duration)])

    elif animation == 'slide_up':
        # Use pixel positions - slide from below
        slide_distance = 100  # pixels
        target_x, target_y = final_pos
        def pos_func(t):
            if t < fade_duration:
                progress = t / fade_duration
                y = target_y + slide_distance * (1 - progress)
            elif t > duration - fade_duration:
                progress = (t - (duration - fade_duration)) / fade_duration
                y = target_y - 30 * progress
            else:
                y = target_y
            return (target_x, int(y))
        txt_clip = txt_clip.with_position(pos_func)
        txt_clip = txt_clip.with_effects([FadeIn(fade_duration), FadeOut(fade_duration)])

    elif animation == 'slide_left':
        # Slide in from left
        slide_distance = 150  # pixels
        target_x, target_y = final_pos
        def pos_func(t):
            if t < fade_duration:
                progress = t / fade_duration
                x = target_x - slide_distance * (1 - progress)
            else:
                x = target_x
            return (int(x), target_y)
        txt_clip = txt_clip.with_position(pos_func)
        txt_clip = txt_clip.with_effects([FadeIn(fade_duration), FadeOut(fade_duration)])

    elif animation == 'slide_right':
        # Slide in from right
        slide_distance = 150  # pixels
        target_x, target_y = final_pos
        def pos_func(t):
            if t < fade_duration:
                progress = t / fade_duration
                x = target_x + slide_distance * (1 - progress)
            else:
                x = target_x
            return (int(x), target_y)
        txt_clip = txt_clip.with_position(pos_func)
        txt_clip = txt_clip.with_effects([FadeIn(fade_duration), FadeOut(fade_duration)])

    elif animation == 'none':
        pass  # No animation

    # Set start time
    txt_clip = txt_clip.with_start(start_time)

    # Add box background if style is 'box' (after text so we know size)
    if style == 'box':
        from moviepy import ColorClip
        txt_w, txt_h = txt_clip.size
        padding = 20
        box_w = txt_w + padding * 2
        box_h = txt_h + padding * 2

        box_clip = ColorClip(size=(box_w, box_h), color=(0, 0, 0))
        box_clip = box_clip.with_opacity(0.7)
        box_clip = box_clip.with_duration(duration)
        box_clip = box_clip.with_start(start_time)

        # Position box at same location as text, offset by padding (using pixel coords)
        box_x = final_pos[0] - padding
        box_y = final_pos[1] - padding
        box_clip = box_clip.with_position((box_x, box_y))

        box_clip = box_clip.with_effects([FadeIn(fade_duration), FadeOut(fade_duration)])
        clips.append(box_clip)

    clips.append(txt_clip)

    return clips


def resolve_intro_path(intro_name: str) -> Optional[str]:
    """Resolve intro template path from name."""
    if not intro_name:
        return None

    if os.path.isabs(intro_name) and os.path.exists(intro_name):
        return intro_name

    # Check local assets
    assets_dir = SKILL_DIR / 'assets' / 'intros'
    for ext in ['', '.mp4', '.mov']:
        candidate = assets_dir / (intro_name + ext)
        if candidate.exists():
            return str(candidate)

    return None


def resolve_outro_path(outro_name: str) -> Optional[str]:
    """Resolve outro template path from name."""
    if not outro_name:
        return None

    if os.path.isabs(outro_name) and os.path.exists(outro_name):
        return outro_name

    # Check local assets - outros stored in same dir as intros
    assets_dir = SKILL_DIR / 'assets' / 'intros'
    for ext in ['', '.mp4', '.mov']:
        candidate = assets_dir / (outro_name + ext)
        if candidate.exists():
            return str(candidate)

    # Also check for outro_ prefix
    for ext in ['', '.mp4', '.mov']:
        candidate = assets_dir / ('outro_' + outro_name + ext)
        if candidate.exists():
            return str(candidate)

    return None


def resolve_music_path(music_name: str) -> Optional[str]:
    """Resolve background music path from name."""
    if not music_name:
        return None

    if os.path.isabs(music_name) and os.path.exists(music_name):
        return music_name

    assets_dir = SKILL_DIR / 'assets' / 'music'
    for ext in ['', '.mp3', '.wav', '.m4a', '.aac']:
        candidate = assets_dir / (music_name + ext)
        if candidate.exists():
            return str(candidate)

    return None


def generate_ai_music(
    transcript: str,
    video_duration: float,
    output_dir: str,
    style: Optional[str] = None,
    mood: Optional[str] = None,
    model: str = "V5"
) -> Optional[str]:
    """Generate AI background music using kie.ai Suno API.

    This function calls the generate_music.py script to create
    appropriate background music based on video content.

    Args:
        transcript: Video transcript or context description
        video_duration: Video duration in seconds
        output_dir: Directory to save generated music
        style: Optional style override (e.g., "Ambient, Electronic")
        mood: Optional mood override (e.g., "inspiring", "thoughtful")
        model: Suno model (V3_5, V4, V4_5, V4_5PLUS, V4_5ALL, V5)

    Returns:
        Path to generated music file or None on failure.
    """
    import subprocess

    generate_script = Path(__file__).parent / 'generate_music.py'

    if not generate_script.exists():
        print(f"  Warning: Music generation script not found: {generate_script}")
        return None

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'background_music.mp3')

    # Build command
    cmd = [
        sys.executable, str(generate_script),
        transcript[:2000],  # Limit transcript length
        '-o', output_path,
        '-d', str(video_duration),
        '--model', model,
        '--json'
    ]

    if style:
        cmd.extend(['--style', style])
    if mood:
        cmd.extend(['--mood', mood])

    print(f"\n{'='*50}")
    print("Generating AI Background Music (Suno API)")
    print(f"{'='*50}")
    print(f"  Model: {model}")
    if style:
        print(f"  Style: {style}")
    if mood:
        print(f"  Mood: {mood}")
    print(f"  Video duration: {video_duration:.1f}s")

    try:
        # Music generation can take 2-5 minutes
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=700)

        if result.returncode == 0:
            try:
                output_data = json.loads(result.stdout)
                if output_data.get('success') and output_data.get('music_path'):
                    print(f"  Generated: {output_data.get('title', 'Background Music')}")
                    print(f"  Duration: {output_data.get('duration', 'Unknown')}s")
                    return output_data['music_path']
            except json.JSONDecodeError:
                pass

            # Check if file exists even without JSON output
            if os.path.exists(output_path):
                return output_path

        # Print error details
        if result.stderr:
            print(f"  Music generation error: {result.stderr[:500]}")
        if result.stdout and 'error' in result.stdout.lower():
            print(f"  Output: {result.stdout[:500]}")

        return None

    except subprocess.TimeoutExpired:
        print("  Music generation timed out (10+ minutes)")
        return None
    except Exception as e:
        print(f"  Music generation error: {e}")
        return None


def is_vfr_video(video_path: str) -> bool:
    """Check if video has variable frame rate (VFR).

    VFR videos cause A/V sync issues with MoviePy because the audio
    timing doesn't match the reconstructed video frames.
    """
    import subprocess
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=r_frame_rate,avg_frame_rate',
             '-of', 'csv=p=0', video_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return False

        lines = result.stdout.strip().split('\n')
        if not lines or not lines[0]:
            return False

        parts = lines[0].split(',')
        if len(parts) != 2:
            return False

        # Parse frame rates as fractions
        def parse_fraction(s):
            if '/' in s:
                num, den = s.split('/')
                return float(num) / float(den)
            return float(s)

        r_frame_rate = parse_fraction(parts[0])
        avg_frame_rate = parse_fraction(parts[1])

        # If they differ by more than 0.005 fps, it's likely VFR
        # Even tiny differences cause cumulative sync drift over minutes
        # (0.008 fps drift = ~1 second desync per 2 minutes of video)
        return abs(r_frame_rate - avg_frame_rate) > 0.005
    except Exception:
        return False


def convert_to_cfr(video_path: str, output_dir: str, target_fps: float = None) -> str:
    """Convert VFR video to constant frame rate (CFR) to prevent A/V sync issues.

    Args:
        video_path: Path to source video
        output_dir: Directory for temporary CFR video
        target_fps: Target frame rate (auto-detected if None)

    Returns:
        Path to CFR video (or original path if conversion not needed/failed)
    """
    import subprocess

    if not is_vfr_video(video_path):
        return video_path

    print(f"  Source is VFR - converting to CFR for sync stability...")

    # Get average frame rate if not specified
    if target_fps is None:
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream=avg_frame_rate',
                 '-of', 'csv=p=0', video_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and '/' in result.stdout:
                num, den = result.stdout.strip().split('/')
                target_fps = round(float(num) / float(den))
            else:
                target_fps = 30
        except Exception:
            target_fps = 30

    cfr_path = os.path.join(output_dir, 'source_cfr.mp4')

    try:
        # Convert to CFR using ffmpeg - copy audio, re-encode video at constant fps
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', video_path,
             '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
             '-r', str(target_fps), '-vsync', 'cfr',
             '-c:a', 'copy',
             cfr_path],
            capture_output=True, text=True, timeout=600
        )

        if result.returncode == 0 and os.path.exists(cfr_path):
            print(f"  Converted to CFR at {target_fps} fps")
            return cfr_path
        else:
            print(f"  Warning: CFR conversion failed, using original")
            if result.stderr:
                print(f"    {result.stderr[:200]}")
            return video_path
    except Exception as e:
        print(f"  Warning: CFR conversion error: {e}")
        return video_path


def parse_timestamp(ts: str) -> float:
    """Convert timestamp string to seconds."""
    ts = ts.strip().replace(',', '.')
    parts = ts.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    else:
        return float(parts[0])


def resolve_asset_path(asset_path: str) -> str:
    """Resolve asset path relative to assets directory."""
    if os.path.isabs(asset_path) and os.path.exists(asset_path):
        return asset_path

    assets_dir = SKILL_DIR / 'assets'
    full_path = assets_dir / asset_path
    if full_path.exists():
        return str(full_path)

    for ext in ['', '.mp4', '.mov', '.webm']:
        candidate = assets_dir / 'broll' / (asset_path + ext)
        if candidate.exists():
            return str(candidate)

    return asset_path


def resolve_sfx_path(sfx_name: str) -> Optional[str]:
    """Resolve sound effect path from name or path."""
    if not sfx_name:
        return None

    if os.path.isabs(sfx_name) and os.path.exists(sfx_name):
        return sfx_name

    assets_dir = SKILL_DIR / 'assets'
    sfx_dir = assets_dir / 'sfx'

    # Try direct path
    for ext in ['', '.mp3', '.wav', '.aac', '.m4a']:
        candidate = sfx_dir / (sfx_name + ext)
        if candidate.exists():
            return str(candidate)

    # Try partial match
    if sfx_dir.exists():
        for f in sfx_dir.glob('*.mp3'):
            if sfx_name.lower() in f.stem.lower():
                return str(f)

    return None


def generate_veo_broll_on_demand(
    visual_prompt: str,
    context: str,
    output_dir: str,
    segment_id: str,
    duration: float = 8.0,
    style: str = 'cinematic',
    fast: bool = False
) -> Optional[str]:
    """Generate cinematic B-roll video using Veo 3.1.

    This is the PRIMARY B-roll generation method - uses AI video generation
    for motion and cinematic quality.

    Args:
        visual_prompt: The visual description written by the agent
        context: The transcript context (for auto-generation if no prompt)
        output_dir: Directory to save generated files
        segment_id: Unique identifier for filenames
        duration: B-roll duration in seconds (trims from 8s Veo output)
        style: B-roll style (cinematic, abstract, tech, minimal)
        fast: Use faster model (lower quality)

    Returns:
        Path to generated video or None on failure.
    """
    import subprocess

    generate_script = Path(__file__).parent / 'generate_broll_video.py'

    if not generate_script.exists():
        print(f"  Warning: Veo B-roll script not found: {generate_script}")
        return None

    os.makedirs(output_dir, exist_ok=True)

    # Build command
    cmd = [
        sys.executable, str(generate_script),
        context,
        '-o', output_dir,
        '--id', segment_id,
        '-d', str(duration),
        '--style', style
    ]

    if visual_prompt:
        cmd.extend(['--visual', visual_prompt])
        print(f"    Generating Veo B-roll: {visual_prompt[:60]}...")
    else:
        print(f"    Generating Veo B-roll from context: {context[:50]}...")

    if fast:
        cmd.append('--fast')

    try:
        # Veo generation can take 2-5 minutes
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode == 0:
            try:
                output_data = json.loads(result.stdout)
                if output_data.get('success') and output_data.get('video_path'):
                    return output_data['video_path']
            except json.JSONDecodeError:
                pass

            expected_path = os.path.join(output_dir, f'broll_{segment_id}.mp4')
            if os.path.exists(expected_path):
                return expected_path

        print(f"    Veo B-roll generation failed: {result.stderr[:300] if result.stderr else 'Unknown error'}")
        return None

    except subprocess.TimeoutExpired:
        print("    Veo B-roll generation timed out (10 minutes)")
        return None
    except Exception as e:
        print(f"    Veo B-roll generation error: {e}")
        return None


def generate_image_broll_on_demand(
    visual_prompt: str,
    context: str,
    output_dir: str,
    segment_id: str,
    duration: float = 3.0,
    effect: str = 'ken_burns_in'
) -> Optional[str]:
    """Generate static image B-roll using Nano Banana (Gemini).

    This is the FALLBACK method for B-roll - generates a static image
    and converts it to video with Ken Burns effect.

    Best for: diagrams, frameworks, schematic visuals.

    Args:
        visual_prompt: The visual description written by the agent (used with --visual)
        context: The transcript context (used as fallback if no visual_prompt)
        output_dir: Directory to save generated files
        segment_id: Unique identifier for filenames
        duration: B-roll duration in seconds
        effect: Animation effect (ken_burns_in, drift, etc.)

    Returns:
        Path to generated video or None on failure.
    """
    import subprocess

    generate_script = Path(__file__).parent / 'generate_broll_image.py'

    if not generate_script.exists():
        print(f"  Warning: Image B-roll script not found: {generate_script}")
        return None

    os.makedirs(output_dir, exist_ok=True)

    # Build command - use visual_prompt if provided, otherwise fall back to context
    cmd = [
        sys.executable, str(generate_script),
        context,  # context is the first positional arg
        '-o', output_dir,
        '--id', segment_id,
        '-d', str(duration),
        '-e', effect
    ]

    # If agent provided a visual_prompt, use it directly via --visual
    if visual_prompt:
        cmd.extend(['--visual', visual_prompt])
        print(f"    Generating image B-roll: {visual_prompt[:60]}...")
    else:
        print(f"    Generating image B-roll from context: {context[:50]}...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            try:
                output_data = json.loads(result.stdout)
                if output_data.get('success') and output_data.get('video_path'):
                    return output_data['video_path']
            except json.JSONDecodeError:
                pass

            expected_path = os.path.join(output_dir, f'broll_{segment_id}.mp4')
            if os.path.exists(expected_path):
                return expected_path

        print(f"    Image B-roll generation failed: {result.stderr[:200] if result.stderr else 'Unknown error'}")
        return None

    except subprocess.TimeoutExpired:
        print("    Image B-roll generation timed out (120s)")
        return None
    except Exception as e:
        print(f"    Image B-roll generation error: {e}")
        return None


def generate_broll_on_demand(
    visual_prompt: str,
    context: str,
    output_dir: str,
    segment_id: str,
    duration: float = 8.0,
    effect: str = 'ken_burns_in',
    source: str = 'veo',
    style: str = 'cinematic',
    fast: bool = False
) -> Optional[str]:
    """Generate AI B-roll using specified source.

    Args:
        visual_prompt: The visual description written by the agent
        context: The transcript context (for auto-generation)
        output_dir: Directory to save generated files
        segment_id: Unique identifier for filenames
        duration: B-roll duration in seconds
        effect: Animation effect for image source (ken_burns_in, etc.)
        source: B-roll source - "veo" (default) or "image" (Nano Banana)
        style: Veo style (cinematic, abstract, tech, minimal)
        fast: Use faster Veo model

    Returns:
        Path to generated video or None on failure.
    """
    if source == 'image':
        # Use static image generation (Nano Banana)
        return generate_image_broll_on_demand(
            visual_prompt=visual_prompt,
            context=context,
            output_dir=output_dir,
            segment_id=segment_id,
            duration=duration,
            effect=effect
        )
    else:
        # Default: Use Veo video generation
        result = generate_veo_broll_on_demand(
            visual_prompt=visual_prompt,
            context=context,
            output_dir=output_dir,
            segment_id=segment_id,
            duration=duration,
            style=style,
            fast=fast
        )

        # Fallback to image if Veo fails
        if result is None:
            print(f"    Veo failed, falling back to image B-roll...")
            return generate_image_broll_on_demand(
                visual_prompt=visual_prompt,
                context=context,
                output_dir=output_dir,
                segment_id=segment_id,
                duration=duration,
                effect=effect
            )

        return result


def prepare_broll_assets(
    broll_edits: List[dict],
    tmpdir: str,
    default_source: str = 'veo',
    default_style: str = 'cinematic',
    fast_mode: bool = False
) -> List[Tuple[dict, str]]:
    """Prepare all B-roll assets upfront.

    Supports three modes:
    1. Pre-existing assets: Uses asset_path from EDL
    2. Veo video generation (DEFAULT): Uses visual_prompt to generate cinematic video B-roll
    3. Image generation: Uses visual_prompt to generate static image B-roll with Ken Burns

    The visual_prompt field is the key differentiator - it should be written
    by the agent based on context analysis, NOT auto-generated from keywords.

    Args:
        broll_edits: List of B-roll edit definitions from EDL
        tmpdir: Temporary directory for generated files
        default_source: Default B-roll source - "veo" (default) or "image"
        default_style: Default Veo style (cinematic, abstract, tech, minimal)
        fast_mode: Use faster Veo model (lower quality)
    """
    prepared = []

    for i, edit in enumerate(broll_edits):
        at = parse_timestamp(edit['at'])

        # Check if a specific asset is provided
        asset_ref = edit.get('asset_path') or edit.get('asset', '')
        asset_path = resolve_asset_path(asset_ref) if asset_ref else ''

        # Need to generate if: no asset provided, path doesn't exist, or path is a directory
        needs_generation = (
            not asset_ref or
            not asset_path or
            not os.path.exists(asset_path) or
            os.path.isdir(asset_path)
        )

        if needs_generation:
            # No pre-existing asset - generate using AI
            # Determine source: per-edit override or default
            source = edit.get('broll_source', default_source)
            style = edit.get('broll_style', default_style)

            source_label = "Veo" if source == 'veo' else "Image"
            print(f"  [{i+1}/{len(broll_edits)}] Generating {source_label} B-roll at {edit['at']}...")

            # visual_prompt is the agent-written prompt (preferred)
            # context is what the speaker is saying (used as context)
            visual_prompt = edit.get('visual_prompt', '')
            context = edit.get('context', '') or edit.get('reason', '') or f"B-roll for video content"

            segment_id = f"gen_{i}_{int(at)}"
            effect = edit.get('effect', 'ken_burns_in')
            duration = edit.get('duration', 8.0)  # Full Veo output by default

            generated_path = generate_broll_on_demand(
                visual_prompt=visual_prompt,
                context=context,
                output_dir=tmpdir,
                segment_id=segment_id,
                duration=duration,
                effect=effect,
                source=source,
                style=style,
                fast=fast_mode
            )

            if generated_path and os.path.exists(generated_path):
                asset_path = generated_path
                print(f"    Generated: {asset_path}")
            else:
                print(f"    Skipping B-roll at {edit['at']} (generation failed)")
                continue
        else:
            print(f"  [{i+1}/{len(broll_edits)}] Found asset: {os.path.basename(asset_path)}")

        prepared.append((edit, asset_path))

    return prepared


def execute_edl_moviepy(
    edl: dict,
    output_path: Optional[str] = None,
    dry_run: bool = False,
    default_sfx: Optional[str] = None,
    sfx_volume: float = 0.5,
    intro: Optional[str] = None,
    outro: Optional[str] = None,
    music: Optional[str] = None,
    music_volume: float = 0.1
) -> str:
    """
    Execute all edits in EDL using MoviePy.

    Key features:
    - Single encoding pass
    - Audio mixing with CompositeAudioClip
    - Transition SFX support
    - Intro prepending
    - Outro appending
    - Background music
    - Maintains perfect audio sync
    """
    source_video = edl['source_video']
    if not os.path.exists(source_video):
        raise FileNotFoundError(f"Source video not found: {source_video}")

    output = output_path or edl['output']['path']
    edits = edl.get('edits', [])

    # Get default SFX from EDL or parameter
    default_transition_sfx = edl.get('default_transition_sfx') or default_sfx
    default_sfx_volume = edl.get('default_sfx_volume', sfx_volume)

    # Get intro/outro/music from EDL or parameter
    intro_template = intro or edl.get('intro')
    outro_template = outro or edl.get('outro')  # outro from CLI or EDL
    bg_music = music or edl.get('background_music')
    bg_music_volume = edl.get('music_volume', music_volume)

    # Check for AI music generation
    music_generate = edl.get('music_generate', False)
    music_style = edl.get('music_style')
    music_mood = edl.get('music_mood')
    music_model = edl.get('music_model', 'V5')
    music_transcript = edl.get('music_transcript', '')  # Transcript for music generation

    # Group edits by type
    broll_edits = [e for e in edits if e['type'] == 'insert_broll']
    cut_edits = [e for e in edits if e['type'] == 'cut']
    text_edits = [e for e in edits if e['type'] == 'insert_text']

    print(f"EDL Summary:")
    print(f"  B-roll insertions: {len(broll_edits)}")
    print(f"  Text overlays: {len(text_edits)}")
    print(f"  Cuts: {len(cut_edits)}")
    print(f"  Default SFX: {default_transition_sfx or 'None'}")
    print(f"  Intro: {intro_template or 'None'}")
    print(f"  Outro: {outro_template or 'None'}")
    print(f"  Background music: {bg_music or 'None'}")

    if dry_run:
        print("\nDry run - no changes made")
        return output

    # Check if there's anything to do beyond edits
    color_correction = edl.get('color_correction', {})
    has_color_correction = color_correction.get('warmth', 0.0) != 0.0 or color_correction.get('brightness', 1.0) != 1.0

    if not edits and not intro_template and not outro_template and not bg_music and not music_generate and not has_color_correction:
        print("No edits to apply, copying source to output")
        import shutil
        shutil.copy(source_video, output)
        return output

    with tempfile.TemporaryDirectory() as tmpdir:
        # Convert VFR to CFR if needed to prevent A/V sync issues
        print(f"\nLoading source video: {source_video}")
        actual_source = convert_to_cfr(source_video, tmpdir)

        # Load main video
        main_clip = VideoFileClip(actual_source)
        main_size = main_clip.size
        main_duration = main_clip.duration

        print(f"  Size: {main_size[0]}x{main_size[1]}")
        print(f"  Duration: {main_duration:.2f}s")
        print(f"  FPS: {main_clip.fps}")

        # Apply global color correction if specified
        color_correction = edl.get('color_correction', {})
        if color_correction:
            warmth = color_correction.get('warmth', 0.0)
            brightness = color_correction.get('brightness', 1.0)
            if warmth != 0.0 or brightness != 1.0:
                print(f"\nApplying color correction to main video...")
                print(f"  Warmth: {warmth:+.2f}")
                print(f"  Brightness: {brightness:.2f}")

                def apply_warmth_correction(frame):
                    """Apply warmth and brightness to frame."""
                    result = frame.astype(np.float32) / 255.0

                    # Apply brightness
                    if brightness != 1.0:
                        result = result * brightness

                    # Apply warmth (add red, reduce blue)
                    if warmth != 0.0:
                        result[:, :, 0] = result[:, :, 0] + warmth  # Red channel
                        result[:, :, 2] = result[:, :, 2] - warmth  # Blue channel

                    # Clip and convert back
                    result = np.clip(result, 0, 1)
                    return (result * 255).astype(np.uint8)

                main_clip = main_clip.image_transform(apply_warmth_correction)
                print("  Color correction applied")

        # Generate AI music if requested
        if music_generate and not bg_music:
            print("\nAI Music generation requested...")
            generated_music_path = generate_ai_music(
                transcript=music_transcript or f"Video content about technology, {main_duration:.0f} seconds",
                video_duration=main_duration,
                output_dir=tmpdir,
                style=music_style,
                mood=music_mood,
                model=music_model
            )
            if generated_music_path:
                bg_music = generated_music_path
                print(f"  AI music will be added: {bg_music}")
            else:
                print("  Warning: AI music generation failed, continuing without music")

        # Prepare B-roll assets
        # Get B-roll generation settings from EDL (with defaults)
        default_broll_source = edl.get('broll_source', 'veo')  # veo (default) or image
        default_broll_style = edl.get('broll_style', 'cinematic')  # cinematic, abstract, tech, minimal
        broll_fast_mode = edl.get('broll_fast', False)  # Use faster Veo model

        if broll_edits:
            source_label = "Veo video" if default_broll_source == 'veo' else "Image"
            print(f"\nPreparing {len(broll_edits)} B-roll assets ({source_label} mode)...")
            broll_assets = prepare_broll_assets(
                broll_edits,
                tmpdir,
                default_source=default_broll_source,
                default_style=default_broll_style,
                fast_mode=broll_fast_mode
            )
        else:
            broll_assets = []

        # Build video composition
        video_clips = [main_clip]
        audio_clips = [main_clip.audio] if main_clip.audio else []

        print(f"\nBuilding composition with {len(broll_assets)} B-roll overlays...")

        # Get global zoom buildup settings from EDL
        default_zoom_buildup = edl.get('zoom_buildup', 4.0)  # seconds before B-roll
        default_zoom_amount = edl.get('zoom_amount', 1.06)  # 6% zoom
        default_zoom_overlap = edl.get('zoom_overlap', 0)  # seconds into B-roll to continue zoom

        for i, (edit, asset_path) in enumerate(broll_assets):
            at = parse_timestamp(edit['at'])
            duration = edit.get('duration', 3.0)

            print(f"  [{i+1}/{len(broll_assets)}] B-roll at {at:.2f}s for {duration:.2f}s")

            # Create zoom buildup on talking head before B-roll
            zoom_duration = edit.get('zoom_buildup', default_zoom_buildup)
            zoom_amount = edit.get('zoom_amount', default_zoom_amount)
            zoom_overlap = edit.get('zoom_overlap', default_zoom_overlap)
            if zoom_duration > 0:
                zoom_start = max(0, at - zoom_duration)
                # Total zoom duration includes overlap into B-roll
                total_zoom_duration = (at - zoom_start) + zoom_overlap
                try:
                    zoom_clip = create_zoom_buildup(
                        main_clip,
                        start_time=zoom_start,
                        duration=min(total_zoom_duration, main_clip.duration - zoom_start),
                        end_zoom=zoom_amount
                    )
                    if zoom_clip:
                        video_clips.append(zoom_clip)
                        overlap_msg = f" + {zoom_overlap:.1f}s overlap" if zoom_overlap > 0 else ""
                        print(f"    Zoom buildup: {zoom_duration:.1f}s before{overlap_msg}, {zoom_amount:.0%} zoom")
                except Exception as e:
                    print(f"    Warning: Zoom buildup failed: {e}")

            # Load B-roll clip
            try:
                if asset_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    broll_clip = ImageClip(asset_path).with_duration(duration)
                else:
                    broll_clip = VideoFileClip(asset_path)
                    # Trim to specified duration
                    if broll_clip.duration > duration:
                        broll_clip = broll_clip.subclipped(0, duration)
                    elif broll_clip.duration < duration:
                        # Loop if needed
                        broll_clip = broll_clip.with_duration(duration)
            except Exception as e:
                print(f"    Error loading B-roll: {e}")
                continue

            # Resize to match main video
            if broll_clip.size != main_size:
                broll_clip = broll_clip.resized(main_size)

            # Apply color correction to match main video at insertion point
            try:
                main_color = analyze_video_color(main_clip, at)
                broll_clip = apply_color_correction(
                    broll_clip,
                    target_brightness=main_color['brightness'],
                    target_warmth=main_color['warmth']
                )
                print(f"    Color corrected (brightness: {main_color['brightness']:.2f}, warmth: {main_color['warmth']:+.2f})")
            except Exception as e:
                print(f"    Warning: Color correction failed: {e}")

            # Apply overlay transition effect (how B-roll enters the frame)
            overlay_effect = edit.get('overlay_effect', 'none')
            if overlay_effect and overlay_effect != 'none':
                try:
                    broll_clip = apply_overlay_effect(broll_clip, overlay_effect, duration)
                    print(f"    Overlay effect: {overlay_effect}")
                except Exception as e:
                    print(f"    Warning: Overlay effect failed: {e}")

            # Set start time for overlay
            broll_clip = broll_clip.with_start(at)

            # Add to video composition
            video_clips.append(broll_clip)

            # Add transition SFX if configured
            sfx_name = edit.get('transition_sfx') or default_transition_sfx
            if sfx_name:
                sfx_path = resolve_sfx_path(sfx_name)
                if sfx_path:
                    try:
                        sfx_vol = edit.get('sfx_volume', default_sfx_volume)
                        sfx_offset = edit.get('sfx_offset', 0.0)

                        sfx_clip = AudioFileClip(sfx_path)
                        sfx_clip = sfx_clip.with_volume_scaled(sfx_vol)
                        sfx_clip = sfx_clip.with_start(at + sfx_offset)

                        audio_clips.append(sfx_clip)
                        print(f"    Added SFX: {sfx_name} at {at + sfx_offset:.2f}s (vol: {sfx_vol})")
                    except Exception as e:
                        print(f"    Warning: Failed to add SFX: {e}")

        # Process text overlays (with various background styles)
        if text_edits:
            print(f"\nBuilding {len(text_edits)} text overlays...")
            for i, edit in enumerate(text_edits):
                at = parse_timestamp(edit['at'])
                duration = edit.get('duration', 3.0)
                text = edit.get('text', '')

                if not text:
                    print(f"  [{i+1}/{len(text_edits)}] Skipping empty text overlay")
                    continue

                style = edit.get('style', 'blur')
                position = edit.get('position', 'center')
                animation = edit.get('animation', 'fade')
                print(f"  [{i+1}/{len(text_edits)}] Text at {at:.2f}s for {duration:.2f}s")
                print(f"    Style: {style}, Position: {position}, Animation: {animation}")
                print(f"    Text: \"{text[:50]}{'...' if len(text) > 50 else ''}\"")

                try:
                    overlay_clips = create_text_overlay(
                        main_clip=main_clip,
                        text=text,
                        start_time=at,
                        duration=duration,
                        font_size=edit.get('font_size', 70),
                        font_color=edit.get('font_color', 'white'),
                        position=position,
                        blur_amount=edit.get('blur_amount', 15.0),
                        darken=edit.get('darken', 0.4),
                        animation=animation,
                        font=edit.get('font'),
                        text_align=edit.get('text_align', 'center'),
                        style=style,
                        accent_color=edit.get('accent_color', '#00ffff'),
                        stroke_width=edit.get('stroke_width', 2)
                    )
                    video_clips.extend(overlay_clips)
                    print(f"    Added {len(overlay_clips)} clips for text overlay")
                except Exception as e:
                    print(f"    Warning: Failed to create text overlay: {e}")

        # Create composite video with explicit fps to prevent VFR sync issues
        print(f"\nCompositing {len(video_clips)} video layers...")
        target_fps = main_clip.fps
        final_video = CompositeVideoClip(video_clips, size=main_size).with_fps(target_fps)

        # Create composite audio
        if audio_clips:
            print(f"Mixing {len(audio_clips)} audio tracks...")
            final_audio = CompositeAudioClip(audio_clips)
            final_video = final_video.with_audio(final_audio)

        # Track intro duration for music offset
        intro_duration = 0.0

        # Prepend intro if specified (BEFORE adding music so we know the offset)
        if intro_template:
            intro_path = resolve_intro_path(intro_template)
            if intro_path:
                print(f"\nPrepending intro: {intro_template}")
                try:
                    intro_clip = VideoFileClip(intro_path)
                    # Resize intro to match main video
                    if intro_clip.size != main_size:
                        intro_clip = intro_clip.resized(main_size)
                    intro_duration = intro_clip.duration
                    # Concatenate intro + main video
                    final_video = concatenate_videoclips([intro_clip, final_video])
                    print(f"  Intro duration: {intro_duration:.2f}s")
                    print(f"  Total duration: {final_video.duration:.2f}s")
                except Exception as e:
                    print(f"  Warning: Failed to add intro: {e}")
            else:
                print(f"  Warning: Intro not found: {intro_template}")

        # Append outro if specified
        outro_duration = 0.0  # Track for music timing
        if outro_template:
            outro_path = resolve_outro_path(outro_template)
            if outro_path:
                print(f"\nAppending outro: {outro_template}")
                try:
                    outro_clip = VideoFileClip(outro_path)
                    # Resize outro to match main video
                    if outro_clip.size != main_size:
                        outro_clip = outro_clip.resized(main_size)
                    outro_duration = outro_clip.duration
                    # Concatenate main video + outro
                    final_video = concatenate_videoclips([final_video, outro_clip])
                    print(f"  Outro duration: {outro_duration:.2f}s")
                    print(f"  Total duration: {final_video.duration:.2f}s")
                except Exception as e:
                    print(f"  Warning: Failed to add outro: {e}")
            else:
                print(f"  Warning: Outro not found: {outro_template}")

        # Add background music AFTER intro/outro (so it fades in at the right time)
        if bg_music:
            music_path = resolve_music_path(bg_music)
            if music_path:
                music_fade_in = edl.get('music_fade_in', 3.0)  # Default 3s fade-in
                music_fade_out = edl.get('music_fade_out', 3.0)  # Default 3s fade-out
                print(f"\nAdding background music: {os.path.basename(music_path)} (vol: {bg_music_volume})")
                print(f"  Fade in: {music_fade_in}s after intro | Fade out: {music_fade_out}s before outro")
                try:
                    music_clip = AudioFileClip(music_path)
                    original_music_duration = music_clip.duration

                    # Loop music if shorter than video (with crossfade for smooth transitions)
                    # Music plays only during main content (after intro, before outro)
                    music_needed_duration = final_video.duration - intro_duration - outro_duration
                    crossfade_duration = 2.0  # seconds overlap between loops

                    if music_clip.duration < music_needed_duration:
                        loops_needed = int(music_needed_duration / (music_clip.duration - crossfade_duration)) + 1
                        print(f"  Music loops needed: {loops_needed} (crossfade: {crossfade_duration}s)")

                        if loops_needed > 1:
                            # Create crossfaded loops using CompositeAudioClip
                            loop_clips = []
                            for i in range(loops_needed):
                                # Create a copy for this loop
                                loop_clip = AudioFileClip(music_path)

                                # Apply fade-out to all clips except the last
                                if i < loops_needed - 1:
                                    loop_clip = loop_clip.with_effects([afx.AudioFadeOut(crossfade_duration)])

                                # Apply fade-in to all clips except the first
                                if i > 0:
                                    loop_clip = loop_clip.with_effects([afx.AudioFadeIn(crossfade_duration)])

                                # Calculate start time with overlap for crossfade
                                start_time = i * (original_music_duration - crossfade_duration)
                                loop_clip = loop_clip.with_start(start_time)
                                loop_clips.append(loop_clip)

                            # Composite all loops (overlapping regions will blend)
                            music_clip = CompositeAudioClip(loop_clips)
                        else:
                            # Single loop, no crossfade needed
                            pass

                    # Trim to fit from intro end to outro start
                    music_clip = music_clip.subclipped(0, music_needed_duration)

                    # Apply volume and fades using afx effects
                    music_clip = music_clip.with_volume_scaled(bg_music_volume)
                    music_clip = music_clip.with_effects([
                        afx.AudioFadeIn(music_fade_in),
                        afx.AudioFadeOut(music_fade_out)
                    ])

                    # Start music after intro
                    music_clip = music_clip.with_start(intro_duration)

                    # Mix with existing audio
                    if final_video.audio:
                        mixed = CompositeAudioClip([final_video.audio, music_clip])
                        final_video = final_video.with_audio(mixed)
                    else:
                        final_video = final_video.with_audio(music_clip)
                    music_end_time = intro_duration + music_needed_duration
                    print(f"  Music: {intro_duration:.2f}s - {music_end_time:.2f}s (duration: {music_needed_duration:.2f}s)")
                except Exception as e:
                    print(f"  Warning: Failed to add music: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"  Warning: Music not found: {bg_music}")

        # Write output
        print(f"\nEncoding to: {output}")
        print("  Codec: libx264, CRF 15")
        print("  Audio: AAC 256k")

        final_video.write_videofile(
            output,
            codec='libx264',
            audio_codec='aac',
            audio_bitrate='256k',
            fps=main_clip.fps,
            preset='medium',
            ffmpeg_params=['-crf', '15', '-profile:v', 'high'],
            logger='bar'
        )

        # Cleanup
        main_clip.close()
        final_video.close()

    print(f"\n{'='*50}")
    print(f"Success! Output: {output}")
    print(f"{'='*50}")

    return output


def main():
    parser = argparse.ArgumentParser(
        description='Execute video edits from EDL using MoviePy'
    )
    parser.add_argument('edl', help='EDL JSON file')
    parser.add_argument('-o', '--output', help='Output video path')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--sfx', help='Default transition SFX (e.g., "whoosh", "swoosh")')
    parser.add_argument('--sfx-volume', type=float, default=0.5, help='SFX volume 0.0-1.0')
    parser.add_argument('--intro', help='Intro template name (e.g., "grow_blur_short")')
    parser.add_argument('--outro', help='Outro template name (e.g., "curves_v2")')
    parser.add_argument('--music', help='Background music track name or path')
    parser.add_argument('--music-volume', type=float, default=0.1, help='Music volume 0.0-1.0 (default 0.1)')
    parser.add_argument('--generate-music', action='store_true',
                       help='Generate AI background music using Suno API')
    parser.add_argument('--music-style', help='Music style for AI generation (e.g., "Ambient, Electronic")')
    parser.add_argument('--music-mood', help='Music mood for AI generation (e.g., "inspiring", "thoughtful")')
    parser.add_argument('--music-transcript', help='Transcript/context for AI music generation')

    args = parser.parse_args()

    edl_path = Path(args.edl)
    if not edl_path.exists():
        print(f"Error: EDL file not found: {edl_path}", file=sys.stderr)
        sys.exit(1)

    edl = json.loads(edl_path.read_text())

    # Merge CLI music generation args into EDL
    if args.generate_music:
        edl['music_generate'] = True
    if args.music_style:
        edl['music_style'] = args.music_style
    if args.music_mood:
        edl['music_mood'] = args.music_mood
    if args.music_transcript:
        edl['music_transcript'] = args.music_transcript

    try:
        output = execute_edl_moviepy(
            edl,
            args.output,
            args.dry_run,
            default_sfx=args.sfx,
            sfx_volume=args.sfx_volume,
            intro=args.intro,
            outro=args.outro,
            music=args.music,
            music_volume=args.music_volume
        )
        if not args.dry_run:
            print(f"\nSuccess! Output: {output}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
