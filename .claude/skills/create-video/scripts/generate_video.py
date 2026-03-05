#!/usr/bin/env python3
"""
Generate complete videos from AI-generated scenes using Veo 3.1.

This script reads a VDL (Video Decision List) and:
1. Generates each scene using Veo 3.1
2. Generates voiceover for each scene (ElevenLabs)
3. Mixes voiceover into each scene individually
4. Generates background music (if enabled)
5. Assembles scenes with transitions
6. Adds intro/outro and SFX
7. Renders final video

Usage:
    source .claude/skills/edit-video/venv/bin/activate
    python generate_video.py vdl.json [-o output.mp4]

Environment:
    Uses edit-video venv for MoviePy and dependencies.
    Requires Veo authentication (see create-veo-video skill).
    Requires ELEVENLABS_API_KEY for voiceover.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any

# Skill directories
SKILL_DIR = Path(__file__).parent.parent
EDIT_VIDEO_SKILL = SKILL_DIR.parent / 'edit-video'
VEO_SKILL = SKILL_DIR.parent / 'create-veo-video'
RUBY_ROOT = SKILL_DIR.parent.parent.parent

# Load environment
from dotenv import load_dotenv
load_dotenv(RUBY_ROOT / '.env')

# ElevenLabs config
DEFAULT_VOICE_ID = "${ELEVENLABS_VOICE_ID}"
ELEVENLABS_MODEL = "eleven_multilingual_v2"

# Add edit-video venv to path for MoviePy
venv_site_packages = EDIT_VIDEO_SKILL / 'venv' / 'lib'
for p in venv_site_packages.glob('python*/site-packages'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
)
from moviepy import afx
import numpy as np


def generate_tts(text: str, output_path: str, voice_id: str = None) -> Optional[str]:
    """Generate TTS audio using ElevenLabs.

    Args:
        text: Text to convert to speech (max 14 words recommended)
        output_path: Output audio file path
        voice_id: ElevenLabs voice ID (default: from env)

    Returns:
        Path to generated audio or None on failure
    """
    try:
        from elevenlabs import ElevenLabs
    except ImportError:
        print("    Warning: elevenlabs not installed, skipping voiceover")
        return None

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("    Warning: ELEVENLABS_API_KEY not set, skipping voiceover")
        return None

    voice_id = voice_id or DEFAULT_VOICE_ID

    # Validate word count
    word_count = len(text.split())
    if word_count > 30:
        print(f"    Warning: Narration has {word_count} words (max 25 recommended)")

    try:
        client = ElevenLabs(api_key=api_key)
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=ELEVENLABS_MODEL
        )

        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)

        return output_path
    except Exception as e:
        print(f"    TTS error: {e}")
        return None


def mix_voiceover_into_scene(
    video_path: str,
    voiceover_path: str,
    output_path: str,
    video_volume: float = 0.2,
    voiceover_volume: float = 2.5
) -> str:
    """Mix voiceover into a scene video.

    Args:
        video_path: Source video
        voiceover_path: Voiceover audio
        output_path: Output video path
        video_volume: Volume for video audio (default 0.6 = 60%)
        voiceover_volume: Volume for voiceover (default 1.0 = 100%)

    Returns:
        Path to output video
    """
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', voiceover_path,
        '-filter_complex',
        f'[0:a]volume={video_volume}[video_audio];'
        f'[1:a]volume={voiceover_volume}[voiceover];'
        f'[video_audio][voiceover]amix=inputs=2:duration=first[audio_out]',
        '-map', '0:v', '-map', '[audio_out]',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    Mix error: {result.stderr[:200]}")
        return video_path  # Return original on failure

    return output_path


def generate_explain_scene(
    scene: Dict[str, Any],
    output_dir: str,
    aspect_ratio: str = '16:9',
    voice_id: str = None,
    video_volume: float = 0.2,
    voiceover_volume: float = 2.5
) -> Optional[str]:
    """Generate an 'explain' scene: static image with Ken Burns effect.

    Uses Nano Banana (Gemini 2.5 Flash) for image generation, then applies
    slow zoom/pan for movement.

    Args:
        scene: Scene definition with image_prompt and optional narration
        output_dir: Directory to save generated video
        aspect_ratio: Video aspect ratio
        voice_id: ElevenLabs voice ID for narration
        video_volume: Volume for scene audio when mixing voiceover
        voiceover_volume: Volume for voiceover

    Returns:
        Path to generated video (with voiceover mixed in if narration provided)
    """
    scene_id = scene.get('id', 'scene')
    image_prompt = scene.get('image_prompt', '')
    narration = scene.get('narration', '')
    duration = scene.get('duration', 8.0)

    if not image_prompt:
        print(f"  Warning: No image_prompt for {scene_id}, skipping")
        return None

    # Generate image using Nano Banana script
    nano_script = RUBY_ROOT / '.claude' / 'scripts' / 'nano_banana.py'
    image_path = os.path.join(output_dir, f'{scene_id}.png')

    # Determine size based on aspect ratio
    if aspect_ratio == '9:16':
        size = '768x1344'
    elif aspect_ratio == '1:1':
        size = '1024x1024'
    else:  # 16:9
        size = '1344x768'

    print(f"    Generating image: {image_prompt[:60]}...")

    try:
        cmd = [
            sys.executable,
            str(nano_script),
            image_prompt,
            '-o', image_path,
            '-s', size
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0 or not os.path.exists(image_path):
            print(f"    Image generation failed: {result.stderr[:200]}")
            return None

        print(f"    Image generated: {os.path.basename(image_path)}")

    except subprocess.TimeoutExpired:
        print(f"    Image generation timed out")
        return None
    except Exception as e:
        print(f"    Image generation error: {e}")
        return None

    # Apply Ken Burns effect (slow zoom in)
    video_path = os.path.join(output_dir, f'{scene_id}_kb.mp4')

    # Ken Burns: start at 100%, end at 110% (slow zoom in)
    # Use ffmpeg zoompan filter
    zoom_speed = 0.001  # Slow zoom
    fps = 30

    try:
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', image_path,
            '-vf', f"zoompan=z='min(zoom+{zoom_speed},1.1)':d={int(duration*fps)}:s=1920x1080:fps={fps}",
            '-t', str(duration),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0 or not os.path.exists(video_path):
            print(f"    Ken Burns failed: {result.stderr[:200]}")
            return None

        print(f"    Ken Burns effect applied")

    except Exception as e:
        print(f"    Ken Burns error: {e}")
        return None

    # Add silent audio track (for consistent mixing later)
    video_with_audio = os.path.join(output_dir, f'{scene_id}_silent.mp4')
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=stereo:d={duration}',
            '-c:v', 'copy', '-c:a', 'aac', '-shortest',
            video_with_audio
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if os.path.exists(video_with_audio):
            video_path = video_with_audio
    except Exception:
        pass  # Continue without silent audio if it fails

    # Mix voiceover if narration provided
    if narration and narration.strip():
        print(f"    Narration: \"{narration[:50]}...\"")

        tts_path = os.path.join(output_dir, f'{scene_id}_vo.mp3')
        if generate_tts(narration, tts_path, voice_id):
            mixed_path = os.path.join(output_dir, f'{scene_id}_mixed.mp4')
            video_path = mix_voiceover_into_scene(
                video_path, tts_path, mixed_path,
                video_volume=video_volume,
                voiceover_volume=voiceover_volume
            )
            print(f"    Mixed voiceover into scene")

    return video_path


def generate_scene_video(
    scene: Dict[str, Any],
    output_dir: str,
    style: str = 'diorama',
    aspect_ratio: str = '16:9',
    fast: bool = False,
    voice_id: str = None,
    video_volume: float = 0.2,
    voiceover_volume: float = 2.5
) -> Optional[str]:
    """Generate a single scene video using Veo 3.1, with optional voiceover.

    Args:
        scene: Scene definition with visual_prompt and optional narration
        output_dir: Directory to save generated video
        style: Visual style (diorama, cinematic, etc.)
        aspect_ratio: Video aspect ratio
        fast: Use fast model
        voice_id: ElevenLabs voice ID for narration
        video_volume: Volume for scene audio when mixing voiceover (default 0.6 = 60%)
        voiceover_volume: Volume for voiceover (default 1.0 = 100%)

    Returns:
        Path to generated video (with voiceover mixed in if narration provided)
    """
    scene_id = scene.get('id', 'scene')
    visual_prompt = scene.get('visual_prompt', '')
    narration = scene.get('narration', '')
    duration = scene.get('duration', 8.0)
    style_override = scene.get('style_override') or style

    if not visual_prompt:
        print(f"  Warning: No visual_prompt for {scene_id}, skipping")
        return None

    # Append silent video instruction to prevent Veo from generating audio
    # that would conflict with our ElevenLabs voiceover
    visual_prompt = visual_prompt.rstrip('. ') + '. No music, no voices, no speech, silent video.'

    # Use the generate_broll_video.py from edit-video skill
    generate_script = EDIT_VIDEO_SKILL / 'scripts' / 'generate_broll_video.py'

    if not generate_script.exists():
        print(f"  Error: Veo script not found: {generate_script}")
        return None

    # Build command
    cmd = [
        sys.executable,
        str(generate_script),
        scene.get('description', 'Generated scene'),
        '-o', output_dir,
        '--id', scene_id,
        '-d', str(duration),
        '--style', style_override,
        '--visual', visual_prompt
    ]

    if fast:
        cmd.append('--fast')

    aspect_map = {'16:9': '16:9', '9:16': '9:16', '1:1': '1:1'}
    if aspect_ratio in aspect_map:
        cmd.extend(['--aspect', aspect_map[aspect_ratio]])

    print(f"    Prompt: {visual_prompt[:80]}...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        video_path = None
        if result.returncode == 0:
            try:
                output_data = json.loads(result.stdout)
                if output_data.get('success') and output_data.get('video_path'):
                    video_path = output_data['video_path']
            except json.JSONDecodeError:
                pass

            if not video_path:
                expected_path = os.path.join(output_dir, f'broll_{scene_id}.mp4')
                if os.path.exists(expected_path):
                    video_path = expected_path

        if not video_path:
            if result.stderr:
                print(f"    Veo error: {result.stderr[:300]}")
            return None

        # Mix voiceover if narration provided
        if narration and narration.strip():
            print(f"    Narration: \"{narration[:50]}...\"")

            # Generate TTS
            tts_path = os.path.join(output_dir, f'{scene_id}_vo.mp3')
            if generate_tts(narration, tts_path, voice_id):
                # Mix into video
                mixed_path = os.path.join(output_dir, f'{scene_id}_mixed.mp4')
                video_path = mix_voiceover_into_scene(
                    video_path, tts_path, mixed_path,
                    video_volume=video_volume,
                    voiceover_volume=voiceover_volume
                )
                print(f"    Mixed voiceover into scene")

        return video_path

    except subprocess.TimeoutExpired:
        print(f"    Scene generation timed out (10 minutes)")
        return None
    except Exception as e:
        print(f"    Scene generation error: {e}")
        return None


def generate_music(
    vdl: Dict[str, Any],
    output_dir: str,
    video_duration: float
) -> Optional[str]:
    """Generate AI background music."""
    audio_config = vdl.get('audio', {})

    if not audio_config.get('music_generate', True):
        return None

    generate_script = EDIT_VIDEO_SKILL / 'scripts' / 'generate_music.py'

    if not generate_script.exists():
        print(f"  Warning: Music script not found: {generate_script}")
        return None

    output_path = os.path.join(output_dir, 'background_music.mp3')

    title = vdl.get('title', 'Generated video')
    scenes = vdl.get('scenes', [])
    context_parts = [title]
    for scene in scenes:
        if scene.get('description'):
            context_parts.append(scene['description'])
    context = '. '.join(context_parts)

    cmd = [
        sys.executable,
        str(generate_script),
        context[:2000],
        '-o', output_path,
        '-d', str(video_duration),
        '--json'
    ]

    if audio_config.get('music_style'):
        cmd.extend(['--style', audio_config['music_style']])
    if audio_config.get('music_mood'):
        cmd.extend(['--mood', audio_config['music_mood']])

    print(f"  Generating AI music...")
    print(f"    Context: {context[:100]}...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=700)

        if result.returncode == 0:
            try:
                output_data = json.loads(result.stdout)
                if output_data.get('success') and output_data.get('music_path'):
                    print(f"    Generated: {output_data.get('title', 'Background Music')}")
                    return output_data['music_path']
            except json.JSONDecodeError:
                pass

            if os.path.exists(output_path):
                return output_path

        if result.stderr:
            print(f"    Music error: {result.stderr[:300]}")
        return None

    except subprocess.TimeoutExpired:
        print(f"    Music generation timed out")
        return None
    except Exception as e:
        print(f"    Music generation error: {e}")
        return None


def resolve_asset_path(asset_name: str, asset_type: str = 'intros') -> Optional[str]:
    """Resolve asset path from name.

    Checks:
    1. Absolute path
    2. create-video skill assets (for series-specific intros like 'explained_ai')
    3. edit-video skill assets (for generic intros)

    Args:
        asset_name: Asset name or path
        asset_type: 'intros', 'outros', 'sfx', 'music'

    Returns:
        Full path to asset or None
    """
    if not asset_name:
        return None

    if os.path.isabs(asset_name) and os.path.exists(asset_name):
        return asset_name

    # Check create-video skill assets first (series-specific)
    skill_assets = SKILL_DIR / 'assets' / asset_type
    for ext in ['', '.mp4', '.mov', '.mp3', '.wav', '.m4a']:
        candidate = skill_assets / (asset_name + ext)
        if candidate.exists():
            return str(candidate)

    # Check edit-video skill assets (generic)
    edit_assets = EDIT_VIDEO_SKILL / 'assets' / asset_type
    for ext in ['', '.mp4', '.mov', '.mp3', '.wav', '.m4a']:
        candidate = edit_assets / (asset_name + ext)
        if candidate.exists():
            return str(candidate)

    # For intros, also check edit-video intros folder for outros
    if asset_type == 'outros':
        edit_intros = EDIT_VIDEO_SKILL / 'assets' / 'intros'
        for ext in ['', '.mp4', '.mov']:
            candidate = edit_intros / (asset_name + ext)
            if candidate.exists():
                return str(candidate)

    return None


def assemble_video(
    scene_videos: List[str],
    vdl: Dict[str, Any],
    music_path: Optional[str],
    output_path: str,
    tmpdir: str
) -> str:
    """Assemble generated scenes into final video."""
    if not scene_videos:
        raise ValueError("No scene videos to assemble")

    print(f"\n{'='*50}")
    print("Assembling Video")
    print(f"{'='*50}")
    print(f"  Scenes: {len(scene_videos)}")

    clips = []
    total_duration = 0

    for i, video_path in enumerate(scene_videos):
        print(f"  Loading scene {i+1}: {os.path.basename(video_path)}")
        clip = VideoFileClip(video_path)
        clips.append(clip)
        total_duration += clip.duration

    target_size = clips[0].size
    target_fps = clips[0].fps or 30

    print(f"  Target size: {target_size[0]}x{target_size[1]}")
    print(f"  Target FPS: {target_fps}")

    transitions = vdl.get('transitions', {})
    transition_type = transitions.get('type', 'crossfade')
    transition_duration = transitions.get('duration', 0.5)

    audio_config = vdl.get('audio', {})
    sfx_name = audio_config.get('sfx_between_scenes')
    sfx_volume = audio_config.get('sfx_volume', 0.12)
    music_volume = audio_config.get('music_volume', 0.10)
    music_fade_in = audio_config.get('music_fade_in', 3.0)
    music_fade_out = audio_config.get('music_fade_out', 3.0)

    structure = vdl.get('structure', {})
    intro_name = structure.get('intro')
    outro_name = structure.get('outro')

    audio_clips = []

    if transition_type == 'crossfade' and transition_duration > 0:
        print(f"  Applying crossfade transitions ({transition_duration}s)")

        final_clips = [clips[0]]
        current_time = clips[0].duration - transition_duration

        for i, clip in enumerate(clips[1:], 1):
            from moviepy.video.fx import FadeIn, FadeOut

            prev_clip = final_clips[-1]
            prev_faded = prev_clip.with_effects([FadeOut(transition_duration)])
            final_clips[-1] = prev_faded

            curr_faded = clip.with_effects([FadeIn(transition_duration)])
            final_clips.append(curr_faded)

            if sfx_name:
                sfx_path = resolve_asset_path(sfx_name, 'sfx')
                if sfx_path:
                    try:
                        sfx_clip = AudioFileClip(sfx_path)
                        sfx_clip = sfx_clip.with_volume_scaled(sfx_volume)
                        # Fire SFX at midpoint of transition (not before)
                        sfx_clip = sfx_clip.with_start(current_time + (transition_duration / 2))
                        audio_clips.append(sfx_clip)
                    except Exception as e:
                        print(f"    Warning: Could not add SFX: {e}")

            current_time += clip.duration - transition_duration

        main_video = concatenate_videoclips(final_clips, method='compose')
    else:
        print("  Concatenating scenes")
        main_video = concatenate_videoclips(clips)

        if sfx_name:
            sfx_path = resolve_asset_path(sfx_name, 'sfx')
            if sfx_path:
                current_time = 0
                for i, clip in enumerate(clips[:-1]):
                    current_time += clip.duration
                    try:
                        sfx_clip = AudioFileClip(sfx_path)
                        sfx_clip = sfx_clip.with_volume_scaled(sfx_volume)
                        # Fire SFX at cut point (no transition, so no midpoint)
                        sfx_clip = sfx_clip.with_start(current_time)
                        audio_clips.append(sfx_clip)
                    except Exception as e:
                        print(f"    Warning: Could not add SFX: {e}")

    main_duration = main_video.duration
    print(f"  Main content duration: {main_duration:.2f}s")

    intro_duration = 0.0
    outro_duration = 0.0

    # Transition duration for intro/outro (slightly longer than scene transitions)
    intro_outro_transition = transitions.get('intro_outro_duration', 0.8)

    if intro_name:
        intro_path = resolve_asset_path(intro_name, 'intros')
        if intro_path:
            print(f"  Adding intro: {intro_name} ({intro_path})")
            try:
                from moviepy.video.fx import FadeIn, FadeOut

                intro_clip = VideoFileClip(intro_path)
                if intro_clip.size != target_size:
                    intro_clip = intro_clip.resized(target_size)
                intro_duration = intro_clip.duration

                # Apply crossfade: intro fades out, main fades in
                if intro_outro_transition > 0:
                    print(f"    Crossfade intro→content ({intro_outro_transition}s)")
                    intro_faded = intro_clip.with_effects([FadeOut(intro_outro_transition)])
                    main_faded = main_video.with_effects([FadeIn(intro_outro_transition)])
                    main_video = concatenate_videoclips([intro_faded, main_faded], method='compose')
                else:
                    main_video = concatenate_videoclips([intro_clip, main_video])
            except Exception as e:
                print(f"    Warning: Could not add intro: {e}")

    if outro_name:
        outro_path = resolve_asset_path(outro_name, 'outros')
        if outro_path:
            print(f"  Adding outro: {outro_name} ({outro_path})")
            try:
                from moviepy.video.fx import FadeIn, FadeOut

                outro_clip = VideoFileClip(outro_path)
                if outro_clip.size != target_size:
                    outro_clip = outro_clip.resized(target_size)
                outro_duration = outro_clip.duration

                # Apply crossfade: main fades out, outro fades in
                if intro_outro_transition > 0:
                    print(f"    Crossfade content→outro ({intro_outro_transition}s)")
                    main_faded = main_video.with_effects([FadeOut(intro_outro_transition)])
                    outro_faded = outro_clip.with_effects([FadeIn(intro_outro_transition)])
                    main_video = concatenate_videoclips([main_faded, outro_faded], method='compose')
                else:
                    main_video = concatenate_videoclips([main_video, outro_clip])
            except Exception as e:
                print(f"    Warning: Could not add outro: {e}")

    final_duration = main_video.duration
    print(f"  Final duration: {final_duration:.2f}s")

    if main_video.audio:
        audio_clips.insert(0, main_video.audio)

    if music_path and os.path.exists(music_path):
        print(f"  Adding background music (vol: {music_volume})")
        try:
            music_clip = AudioFileClip(music_path)
            music_needed = main_duration

            if music_clip.duration < music_needed:
                loops = int(music_needed / music_clip.duration) + 1
                print(f"    Looping music {loops} times")

                loop_clips = []
                crossfade = 2.0
                for i in range(loops):
                    loop = AudioFileClip(music_path)
                    if i > 0:
                        loop = loop.with_effects([afx.AudioFadeIn(crossfade)])
                    if i < loops - 1:
                        loop = loop.with_effects([afx.AudioFadeOut(crossfade)])
                    loop = loop.with_start(i * (music_clip.duration - crossfade))
                    loop_clips.append(loop)

                music_clip = CompositeAudioClip(loop_clips)

            music_clip = music_clip.subclipped(0, music_needed)
            music_clip = music_clip.with_volume_scaled(music_volume)
            music_clip = music_clip.with_effects([
                afx.AudioFadeIn(music_fade_in),
                afx.AudioFadeOut(music_fade_out)
            ])
            music_clip = music_clip.with_start(intro_duration)
            audio_clips.append(music_clip)

        except Exception as e:
            print(f"    Warning: Could not add music: {e}")

    if audio_clips:
        print(f"  Mixing {len(audio_clips)} audio tracks")
        final_audio = CompositeAudioClip(audio_clips)
        main_video = main_video.with_audio(final_audio)

    print(f"\n  Encoding to: {output_path}")
    print("    Codec: libx264, CRF 15")
    print("    Audio: AAC 256k")

    main_video.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='aac',
        audio_bitrate='256k',
        fps=target_fps,
        preset='medium',
        ffmpeg_params=['-crf', '15', '-profile:v', 'high'],
        logger='bar'
    )

    main_video.close()
    for clip in clips:
        clip.close()

    return output_path


def generate_complete_video(vdl: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """Main function to generate a complete video from VDL."""
    print(f"\n{'='*60}")
    print("CREATE-VIDEO: AI-Generated Explainer Video")
    print(f"{'='*60}")

    title = vdl.get('title', 'Generated Video')
    style = vdl.get('style', 'diorama')
    aspect_ratio = vdl.get('aspect_ratio', '16:9')
    fast = vdl.get('fast', False)
    scenes = vdl.get('scenes', [])

    # Audio settings for per-scene voiceover mixing
    audio_config = vdl.get('audio', {})
    voice_id = audio_config.get('voice_id', DEFAULT_VOICE_ID)
    video_volume = audio_config.get('scene_video_volume', 0.2)
    voiceover_volume = audio_config.get('voiceover_volume', 2.5)

    output = output_path or vdl.get('output', {}).get('path', '/tmp/generated_video.mp4')

    print(f"  Title: {title}")
    print(f"  Style: {style}")
    print(f"  Aspect: {aspect_ratio}")
    print(f"  Scenes: {len(scenes)}")
    print(f"  Fast mode: {fast}")
    print(f"  Voice ID: {voice_id}")
    print(f"  Output: {output}")

    # Check for narration in scenes
    scenes_with_narration = sum(1 for s in scenes if s.get('narration'))
    if scenes_with_narration:
        print(f"  Scenes with narration: {scenes_with_narration}")

    if not scenes:
        raise ValueError("No scenes defined in VDL")

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n{'='*50}")
        print("Generating Scene Videos")
        print(f"{'='*50}")

        scene_videos = []

        for i, scene in enumerate(scenes):
            scene_id = scene.get('id', f'scene_{i:02d}')
            description = scene.get('description', '')
            scene_type = scene.get('type', 'visualize')  # Default to visualize (Veo)

            print(f"\n  [{i+1}/{len(scenes)}] {scene_id} ({scene_type}): {description[:50]}...")

            if scene_type == 'explain':
                # Static image with Ken Burns effect
                video_path = generate_explain_scene(
                    scene=scene,
                    output_dir=tmpdir,
                    aspect_ratio=aspect_ratio,
                    voice_id=voice_id,
                    video_volume=video_volume,
                    voiceover_volume=voiceover_volume
                )
            else:
                # Veo 3.1 animated B-roll (default)
                video_path = generate_scene_video(
                    scene=scene,
                    output_dir=tmpdir,
                    style=style,
                    aspect_ratio=aspect_ratio,
                    fast=fast,
                    voice_id=voice_id,
                    video_volume=video_volume,
                    voiceover_volume=voiceover_volume
                )

            if video_path and os.path.exists(video_path):
                scene_videos.append(video_path)
                print(f"    Generated: {os.path.basename(video_path)}")
            else:
                print(f"    FAILED - skipping scene")

        if not scene_videos:
            raise RuntimeError("All scene generations failed")

        print(f"\n  Successfully generated {len(scene_videos)}/{len(scenes)} scenes")

        audio_config = vdl.get('audio', {})
        music_path = None

        if audio_config.get('music_generate', True):
            print(f"\n{'='*50}")
            print("Generating Background Music")
            print(f"{'='*50}")

            estimated_duration = len(scene_videos) * 8.0

            music_path = generate_music(vdl, tmpdir, estimated_duration)

            if music_path:
                print(f"  Music generated: {os.path.basename(music_path)}")
            else:
                print("  Music generation failed, continuing without music")

        final_path = assemble_video(
            scene_videos=scene_videos,
            vdl=vdl,
            music_path=music_path,
            output_path=output,
            tmpdir=tmpdir
        )

    print(f"\n{'='*60}")
    print(f"SUCCESS! Video generated: {final_path}")
    print(f"{'='*60}")

    return final_path


def main():
    parser = argparse.ArgumentParser(
        description='Generate complete videos from AI-generated scenes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example VDL structure:
{
  "title": "How AI Memory Works",
  "style": "diorama",
  "scenes": [
    {
      "id": "scene_01",
      "description": "Introduction",
      "visual_prompt": "Miniature diorama of...",
      "narration": "Every second, billions of operations happen."
    }
  ],
  "audio": {
    "music_generate": true,
    "voice_id": "${ELEVENLABS_VOICE_ID}",
    "scene_video_volume": 0.2,
    "voiceover_volume": 2.5,
    "sfx_between_scenes": "whoosh_fast_transition"
  },
  "structure": {
    "intro": "explained_ai",
    "outro": "explained_ai"
  },
  "output": {"path": "/tmp/video.mp4"}
}
"""
    )
    parser.add_argument('vdl', help='VDL (Video Decision List) JSON file')
    parser.add_argument('-o', '--output', help='Output video path (overrides VDL)')
    parser.add_argument('--dry-run', action='store_true', help='Parse VDL and show plan only')

    args = parser.parse_args()

    vdl_path = Path(args.vdl)
    if not vdl_path.exists():
        print(f"Error: VDL file not found: {vdl_path}", file=sys.stderr)
        sys.exit(1)

    try:
        vdl = json.loads(vdl_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in VDL: {e}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("VDL Summary:")
        print(f"  Title: {vdl.get('title', 'Untitled')}")
        print(f"  Style: {vdl.get('style', 'diorama')}")
        print(f"  Scenes: {len(vdl.get('scenes', []))}")
        for i, scene in enumerate(vdl.get('scenes', [])):
            narration = scene.get('narration', '')
            word_count = len(narration.split()) if narration else 0
            print(f"    {i+1}. {scene.get('description', 'No description')}")
            if narration:
                print(f"       Narration ({word_count} words): \"{narration[:50]}...\"")
        print(f"  Music: {'Yes' if vdl.get('audio', {}).get('music_generate', True) else 'No'}")
        print(f"  Intro: {vdl.get('structure', {}).get('intro', 'None')}")
        print(f"  Outro: {vdl.get('structure', {}).get('outro', 'None')}")
        sys.exit(0)

    try:
        output = generate_complete_video(vdl, args.output)
        print(f"\nVideo created: {output}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
