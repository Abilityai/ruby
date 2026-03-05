#!/usr/bin/env python3
"""
Generate contextual B-roll images using Nano Banana (Gemini 2.5 Flash Image).

Given a transcript segment or context, generates a relevant visual that can be
used as B-roll in video editing.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def fetch_brand_style() -> str:
    """Fetch the brand style prompt fresh from Google Drive.

    Downloads Brand_Broll_Style_Prompt.md and extracts the style block.
    Falls back to minimal style if fetch fails.
    """
    import tempfile

    # Google Drive file ID for the creator_Broll_Style_Prompt.md
    BROLL_STYLE_FILE_ID = "YOUR_BROLL_STYLE_ID"

    # Path to Google Drive API script (in .claude/scripts/google/)
    skill_dir = Path(__file__).parent.parent
    gdrive_script = skill_dir.parent.parent / "scripts" / "google" / "google_drive.py"

    if not gdrive_script.exists():
        print("Warning: Google Drive script not found, using fallback style", file=sys.stderr)
        return get_fallback_style()

    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            tmp_path = f.name

        # Download fresh from Google Drive
        cmd = ["python3", str(gdrive_script), "download", BROLL_STYLE_FILE_ID, tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"Warning: Failed to download style from Drive: {result.stderr}", file=sys.stderr)
            return get_fallback_style()

        # Read and extract the style block
        with open(tmp_path, 'r') as f:
            content = f.read()

        os.remove(tmp_path)

        # Extract the style block from the markdown
        # Look for the "Prompt Template" section with the style requirements
        if "STYLE REQUIREMENTS" in content:
            # Find the code block with style requirements
            import re
            match = re.search(r'```\n(STYLE REQUIREMENTS.*?)```', content, re.DOTALL)
            if match:
                return match.group(1).strip()

        # If no code block found, extract key rules from the document
        return extract_style_from_markdown(content)

    except Exception as e:
        print(f"Warning: Error fetching brand style: {e}", file=sys.stderr)
        return get_fallback_style()


def extract_style_from_markdown(content: str) -> str:
    """Extract style rules from the markdown document."""
    # Build style block from document sections
    style_parts = ["STYLE REQUIREMENTS (the creator's brand - MANDATORY):"]

    # Extract color palette
    if "#000000" in content:
        style_parts.append("- Background: Pure black (#000000) - NO gradients, NO dark blue")
    if "#ffffff" in content:
        style_parts.append("- Primary text: White (#ffffff)")
    if "#9da2bc" in content:
        style_parts.append("- Secondary text: Gray-blue (#9da2bc) for subtitles/captions")
    if "#22c55e" in content:
        style_parts.append("- Success indicators: Green (#22c55e) for checkmarks")
    if "#ef4444" in content:
        style_parts.append("- Error indicators: Red (#ef4444) for X marks")
    if "#333333" in content:
        style_parts.append("- Borders: Dark gray (#333333) - subtle, not prominent")

    # Add standard rules
    style_parts.extend([
        "- Font: DM Sans or clean sans-serif, bold (700-800) for titles",
        "- Text size: VERY LARGE for titles (60-80% of frame width)",
        "- Composition: Clean, minimal, maximum 10 elements, plenty of negative space",
        "- Quality: High contrast, mobile-optimized, professional"
    ])

    return "\n".join(style_parts)


def get_fallback_style() -> str:
    """Fallback style if Google Drive fetch fails."""
    return """STYLE REQUIREMENTS (the creator's brand - MANDATORY):
- Background: Pure black (#000000) - NO gradients, NO dark blue
- Primary text: White (#ffffff)
- Secondary text: Gray-blue (#9da2bc) for subtitles/captions
- Success indicators: Green (#22c55e) for checkmarks
- Error indicators: Red (#ef4444) for X marks
- Borders: Dark gray (#333333) - subtle, not prominent
- Font: DM Sans or clean sans-serif, bold (700-800) for titles
- Text size: VERY LARGE for titles (60-80% of frame width)
- Composition: Clean, minimal, maximum 10 elements, plenty of negative space
- Quality: High contrast, mobile-optimized, professional"""


import random

# Visual variety pools for dynamic prompt generation
VISUAL_STYLES = [
    "photorealistic cinematic",
    "high-quality 3D render",
    "abstract geometric",
    "minimalist tech aesthetic",
    "futuristic holographic",
    "dramatic documentary style",
]

COMPOSITION_APPROACHES = [
    "floating elements in dark void",
    "single central focal point with radiating elements",
    "layered depth with parallax suggestion",
    "symmetrical balanced composition",
    "dynamic diagonal arrangement",
    "organic flowing structure",
]

LIGHTING_STYLES = [
    "volumetric light rays piercing darkness",
    "soft bioluminescent glow",
    "dramatic rim lighting",
    "subtle ambient illumination",
    "neon edge highlights",
    "ethereal backlight bloom",
]

COLOR_ACCENTS = [
    "electric blue and cyan",
    "deep blue with white highlights",
    "cyan with subtle purple undertones",
    "cool blue with green accents",
    "pure white on black",
    "gradient from blue to teal",
]


def generate_broll_prompt(context: str, topic: str = None, visual_description: str = None, variety_seed: int = None) -> str:
    """Generate an optimized prompt for B-roll image generation.

    Fetches fresh brand style from Google Drive (Brand_Broll_Style_Prompt.md).
    Follows Nano Banana best practices with VARIETY:
    - Uses context to create unique visuals (not just theme matching)
    - Randomizes style elements for diversity
    - Narrative descriptions (not keywords)
    - Simple, focused composition (max 10 elements)
    - the creator's brand styling (pure black theme)

    Args:
        context: The transcript segment or context being visualized
        topic: Optional topic hint for better targeting
        visual_description: Optional specific visual description to use directly
        variety_seed: Optional seed for consistent randomization
    """
    # Set seed for reproducibility if provided
    if variety_seed is not None:
        random.seed(variety_seed)
    else:
        # Use context hash for semi-consistent but varied results
        random.seed(hash(context) % 10000)

    # If a specific visual description is provided, use it directly WITHOUT wrapping
    # The agent is responsible for providing complete, valid prompts
    if visual_description:
        return visual_description

    # AUTO-GENERATION FALLBACK (only used when no visual_description provided)
    # Fetch brand style for auto-generated prompts
    brand_style = fetch_brand_style()

    # Analyze context and generate appropriate visual
    context_lower = context.lower()

    # Detect primary theme from context
    themes_detected = []

    # Video/content creation
    if any(word in context_lower for word in ['video', 'edit', 'editing', 'footage', 'clip', 'content', 'youtube', 'recording', 'camera']):
        themes_detected.append('video_production')

    # Social media
    if any(word in context_lower for word in ['social', 'instagram', 'tiktok', 'twitter', 'linkedin', 'post', 'viral', 'engagement']):
        themes_detected.append('social_media')

    # AI/Technology
    if any(word in context_lower for word in ['ai', 'artificial', 'intelligence', 'agent', 'model', 'neural', 'machine', 'learning', 'algorithm', 'automation']):
        themes_detected.append('ai_tech')

    # Coding/Development
    if any(word in context_lower for word in ['code', 'coding', 'programming', 'developer', 'software', 'script', 'terminal', 'api']):
        themes_detected.append('coding')

    # Collaboration/Remote work
    if any(word in context_lower for word in ['team', 'remote', 'collaborate', 'work', 'contractor', 'hire', 'job', 'position']):
        themes_detected.append('collaboration')

    # Learning/Growth
    if any(word in context_lower for word in ['learn', 'grow', 'curious', 'understand', 'capable', 'skill']):
        themes_detected.append('growth')

    # Business/Enterprise
    if any(word in context_lower for word in ['enterprise', 'business', 'company', 'professional', 'corporate']):
        themes_detected.append('business')

    # Generate visual description based on detected themes
    visual_descriptions = {
        'video_production': """A sleek professional video editing workspace visualization. Multiple floating holographic
screens showing video timelines, waveforms, and color grading panels. The screens emit soft blue and cyan light
against a dark environment. Think of a futuristic editing bay with volumetric lighting. No actual readable text
on screens - just abstract UI patterns suggesting video editing software. Cinematic depth of field.""",

        'social_media': """An abstract visualization of digital content flowing through interconnected nodes.
Glowing data streams in electric blue and cyan forming a network pattern against deep black. Small geometric
shapes (circles, squares) representing content pieces flowing through luminous pathways. Suggests virality and
reach without showing actual social media logos. Clean, minimal, futuristic aesthetic.""",

        'ai_tech': """A dramatic visualization of artificial intelligence. Abstract neural network rendered as
elegant interconnected nodes with glowing blue synaptic connections pulsing with light. The network forms a
subtle brain-like or crystalline structure floating in dark space. Volumetric light rays pierce through.
Conveys intelligence, complexity, and capability. No text or labels - pure visual metaphor.""",

        'coding': """An artistic interpretation of code and development. Streams of stylized characters and
symbols flowing in parallax layers - not readable code but the aesthetic essence of programming. Dark terminal-like
background with syntax-highlighting colors (blue, cyan, green accents). Matrix-inspired but more elegant and
minimal. Soft glow effects on the character streams.""",

        'collaboration': """A visualization of connected minds working together. Abstract human silhouettes or
geometric figures connected by glowing blue neural-like pathways. Suggests remote collaboration and shared
thinking. Multiple nodes of activity linked across space. Dark background with warm accent lighting on the
connection points. Professional and inspiring mood.""",

        'growth': """An abstract visualization of growth and potential. A luminous tree or plant-like structure
with branches made of light, growing upward through dark space. Or geometric shapes evolving and expanding.
Blue and cyan bioluminescent glow. Suggests learning, capability, and upward trajectory. Organic yet futuristic.""",

        'business': """A minimal futuristic cityscape or abstract architecture representing enterprise and scale.
Clean geometric buildings or structures with glowing blue edge lighting against dark sky. Suggests professionalism,
stability, and ambition. Cinematic wide shot with dramatic lighting. Modern and aspirational."""
    }

    # VARIETY: Pick random style elements
    style = random.choice(VISUAL_STYLES)
    composition = random.choice(COMPOSITION_APPROACHES)
    lighting = random.choice(LIGHTING_STYLES)
    colors = random.choice(COLOR_ACCENTS)

    # Extract key concepts from context for unique visuals
    key_words = [w for w in context.lower().split() if len(w) > 4][:5]
    context_essence = ' '.join(key_words) if key_words else "technology innovation"

    # Select the best matching visual or combine themes WITH VARIETY
    if not themes_detected:
        # Default: context-driven abstract visual
        visual_approach = f"""A {style} visualization inspired by the concept: "{context_essence}"

Create a unique visual metaphor with {composition}. Use {colors} color palette against pure black.
{lighting}. The image should feel like a frame from a premium tech documentary.
One clear focal point suggesting: {context[:80]}"""
    elif len(themes_detected) == 1:
        base_desc = visual_descriptions.get(themes_detected[0], visual_descriptions['ai_tech'])
        # Add variety to base description
        visual_approach = f"""{base_desc}

UNIQUE VARIATION for this segment:
- Visual style: {style}
- Composition: {composition}
- Lighting: {lighting}
- Color accent: {colors}
- Specific context to visualize: "{context[:100]}" """
    else:
        # Combine themes with variety
        primary = themes_detected[0]
        secondary = themes_detected[1] if len(themes_detected) > 1 else None
        visual_approach = f"""{visual_descriptions.get(primary, '')}

BLEND with {secondary.replace('_', ' ') if secondary else 'abstract elements'}:
- Style: {style}
- Composition: {composition}
- Context essence: "{context_essence}"
- Make this visually DISTINCT from other B-rolls"""

    # Add topic enhancement if provided
    topic_note = ""
    if topic:
        topic_note = f"\nThe visual should subtly evoke the concept of: {topic}\n"

    full_prompt = f"""Create a cinematic B-roll image for a talking-head video about AI and technology.

TRANSCRIPT CONTEXT (what the speaker is saying):
"{context[:200]}"

VISUAL TO CREATE:
{visual_approach}
{topic_note}

{brand_style}

CRITICAL REQUIREMENTS:
- NO TEXT whatsoever in the image - purely visual
- 16:9 aspect ratio
- Photorealistic or high-quality 3D render aesthetic
- Should feel like a frame from a Netflix documentary or Apple product video
- Simple composition with one clear focal point (max 5-7 visual elements)
- High contrast for mobile readability
- The image should visually complement the spoken content
"""

    return full_prompt


def generate_image(prompt: str, output_path: str, aspect_ratio: str = "16:9") -> str:
    """Generate image using Nano Banana via the existing skill script."""

    # Use the existing Nano Banana generation script
    skill_script = Path.home() / ".claude/skills/nano-banana-image-generator/scripts/generate_image.py"

    if not skill_script.exists():
        # Fallback to sibling skill in same .claude/skills/ directory
        skill_dir = Path(__file__).parent.parent
        skill_script = skill_dir.parent / "nano-banana-image-generator" / "scripts" / "generate_image.py"

    if skill_script.exists():
        cmd = [
            "python3", str(skill_script),
            prompt,
            output_path,
            "--aspect-ratio", aspect_ratio
        ]
    else:
        # Direct Gemini API call as fallback
        return generate_image_direct(prompt, output_path)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"Generated image: {output_path}")
            return output_path
        else:
            print(f"Image generation failed: {result.stderr}", file=sys.stderr)
            return None
    except subprocess.TimeoutExpired:
        print("Image generation timed out", file=sys.stderr)
        return None


def generate_image_direct(prompt: str, output_path: str) -> str:
    """Direct Gemini API image generation as fallback."""

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY or GEMINI_API_KEY not set", file=sys.stderr)
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        # Use Gemini 2.5 Flash for image generation
        model = genai.GenerativeModel("gemini-2.0-flash-exp")

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="image/png"
            )
        )

        # Save image
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open(output_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    print(f"Generated image: {output_path}")
                    return output_path

        print("No image in response", file=sys.stderr)
        return None

    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        return None


def get_animation_filter(effect: str, duration: float, width: int = 1920, height: int = 1080) -> str:
    """Get FFmpeg filter string for the specified animation effect.

    All effects include fade in (0.3s) and fade out (0.3s) for smooth transitions.

    Available effects:
    - ken_burns_in: Slow zoom in (default)
    - ken_burns_out: Zoom out from close to full
    - ken_burns_pan: Zoom in while panning right
    - pan_left: Pan from right to left
    - pan_right: Pan from left to right
    - pulse: Subtle pulsing/breathing zoom
    - drift: Slow diagonal drift
    - none: Static image with fades
    """
    frames = int(duration * 30)
    fade_duration = 0.3  # Fade in/out duration

    # Base scaling to ensure proper size (used by zoompan effects)
    scale_base = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"

    # For pan effects, we need to scale UP so there's room to pan
    # Scale to 130% width/height so we can pan across the image
    pan_scale = 1.3
    pan_width = int(width * pan_scale)
    pan_height = int(height * pan_scale)

    effects = {
        # Ken Burns zoom in - subtle zoom from 1.0x to 1.08x with fades
        'ken_burns_in': (
            f"{scale_base},"
            f"zoompan=z='min(zoom+0.0008,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps=30,"
            f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={duration-fade_duration}:d={fade_duration}"
        ),

        # Ken Burns zoom out - zoom from 1.1x down to 1.0x with fades
        'ken_burns_out': (
            f"{scale_base},"
            f"zoompan=z='if(lte(zoom,1.0),1.1,max(1.001,zoom-0.001))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps=30,"
            f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={duration-fade_duration}:d={fade_duration}"
        ),

        # Ken Burns with pan - zoom in while panning right
        'ken_burns_pan': (
            f"scale={pan_width}:{pan_height}:force_original_aspect_ratio=decrease,pad={pan_width}:{pan_height}:(ow-iw)/2:(oh-ih)/2,"
            f"zoompan=z='min(zoom+0.0006,1.06)':x='(iw-iw/zoom)/2+(iw/zoom-ow)*on/{frames}/2':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps=30,"
            f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={duration-fade_duration}:d={fade_duration}"
        ),

        # Pan from right to left (starts showing right side, moves to left)
        'pan_left': (
            f"scale={pan_width}:-1,pad={pan_width}:{pan_height}:(ow-iw)/2:(oh-ih)/2,"
            f"zoompan=z=1.001:x='(iw-ow)*(1-on/{frames})':y='(ih-oh)/2':d={frames}:s={width}x{height}:fps=30,"
            f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={duration-fade_duration}:d={fade_duration}"
        ),

        # Pan from left to right (starts showing left side, moves to right)
        'pan_right': (
            f"scale={pan_width}:-1,pad={pan_width}:{pan_height}:(ow-iw)/2:(oh-ih)/2,"
            f"zoompan=z=1.001:x='(iw-ow)*on/{frames}':y='(ih-oh)/2':d={frames}:s={width}x{height}:fps=30,"
            f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={duration-fade_duration}:d={fade_duration}"
        ),

        # Pulse - subtle breathing zoom effect (zoom in and out cyclically)
        'pulse': (
            f"{scale_base},"
            f"zoompan=z='1.02+0.03*sin(on*PI*2/{frames})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps=30,"
            f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={duration-fade_duration}:d={fade_duration}"
        ),

        # Diagonal drift - slow movement from top-left to bottom-right with slight zoom
        'drift': (
            f"scale={pan_width}:{pan_height}:force_original_aspect_ratio=decrease,pad={pan_width}:{pan_height}:(ow-iw)/2:(oh-ih)/2,"
            f"zoompan=z='min(zoom+0.0003,1.03)':x='(iw-ow)*on/{frames}':y='(ih-oh)*on/{frames}':d={frames}:s={width}x{height}:fps=30,"
            f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={duration-fade_duration}:d={fade_duration}"
        ),

        # Static - no animation, just fades
        'none': (
            f"{scale_base},"
            f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={duration-fade_duration}:d={fade_duration}"
        ),
    }

    return effects.get(effect, effects['ken_burns_in'])


def image_to_video(image_path: str, output_path: str, duration: float = 3.0, effect: str = 'ken_burns_in') -> str:
    """Convert a static image to a video with specified duration and animation effect.

    Args:
        image_path: Path to the source image
        output_path: Path for the output video
        duration: Video duration in seconds (default 3.0)
        effect: Animation effect to apply. Options:
            - ken_burns_in: Slow zoom in (default)
            - ken_burns_out: Zoom out from close
            - pan_left: Pan from right to left
            - pan_right: Pan from left to right
            - fade_glow: Fade in with glow effect
            - blur_reveal: Start blurred, reveal sharp
            - pulse: Subtle pulsing zoom
            - drift: Diagonal movement
            - none: Static with fade in

    Returns:
        Path to output video or None on failure.
    """

    filter_complex = get_animation_filter(effect, duration)

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1',
        '-i', image_path,
        '-vf', filter_complex,
        '-t', str(duration),
        '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
        '-pix_fmt', 'yuv420p',
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Created video from image ({effect}): {output_path}")
            return output_path
        else:
            print(f"FFmpeg error: {result.stderr}", file=sys.stderr)
            # Try fallback to simple static if complex filter fails
            if effect != 'none':
                print("Trying fallback to static effect...")
                return image_to_video(image_path, output_path, duration, 'none')
            return None
    except Exception as e:
        print(f"Error creating video: {e}", file=sys.stderr)
        return None


# Available animation effects for B-roll
BROLL_EFFECTS = [
    'ken_burns_in',   # Slow zoom in (default)
    'ken_burns_out',  # Zoom out from close
    'ken_burns_pan',  # Zoom in while panning
    'pan_left',       # Pan from right to left
    'pan_right',      # Pan from left to right
    'pulse',          # Subtle pulsing zoom
    'drift',          # Diagonal movement with zoom
    'none',           # Static with fades
]


def generate_broll_for_segment(
    context: str,
    output_dir: str,
    topic: str = None,
    duration: float = 3.0,
    segment_id: str = None,
    visual_description: str = None,
    effect: str = 'ken_burns_in'
) -> dict:
    """Generate a complete B-roll video for a transcript segment.

    Args:
        context: The transcript segment text being visualized
        output_dir: Directory to save output files
        topic: Optional topic hint for better targeting
        duration: Video duration in seconds (default 3.0)
        segment_id: Unique ID for filenames
        visual_description: Optional specific visual description (bypasses auto-detection)
        effect: Animation effect to apply. Options:
            - ken_burns_in: Slow zoom in (default)
            - ken_burns_out: Zoom out from close
            - pan_left: Pan from right to left
            - pan_right: Pan from left to right
            - fade_glow: Fade in with glow effect
            - blur_reveal: Start blurred, reveal sharp
            - pulse: Subtle pulsing zoom
            - drift: Diagonal movement
            - none: Static with fade in

    Returns dict with image_path, video_path, and metadata.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique ID if not provided
    if not segment_id:
        import hashlib
        segment_id = hashlib.md5(context.encode()).hexdigest()[:8]

    image_path = output_dir / f"broll_{segment_id}.png"
    video_path = output_dir / f"broll_{segment_id}.mp4"

    # Generate the prompt
    prompt = generate_broll_prompt(context, topic, visual_description)

    # Generate the image
    print(f"Generating B-roll image for: {context[:50]}...")
    img_result = generate_image(prompt, str(image_path))

    if not img_result:
        return {"error": "Image generation failed"}

    # Convert to video with specified effect
    print(f"Converting to {duration}s video with '{effect}' effect...")
    vid_result = image_to_video(str(image_path), str(video_path), duration, effect)

    if not vid_result:
        return {"error": "Video conversion failed", "image_path": str(image_path)}

    return {
        "success": True,
        "image_path": str(image_path),
        "video_path": str(video_path),
        "duration": duration,
        "effect": effect,
        "context": context[:100],
        "prompt": prompt[:200] + "..."
    }


def main():
    parser = argparse.ArgumentParser(
        description='Generate contextual B-roll images/videos for video editing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Animation Effects:
  ken_burns_in   Slow zoom in (default)
  ken_burns_out  Zoom out from close
  pan_left       Pan from right to left
  pan_right      Pan from left to right
  fade_glow      Fade in with glow effect
  blur_reveal    Start blurred, reveal sharp
  pulse          Subtle pulsing zoom
  drift          Diagonal movement
  none           Static with fade in

Examples:
  %(prog)s "AI agents working together" -o /tmp/broll --id broll_01
  %(prog)s "Neural networks" --effect blur_reveal -d 4.0
  %(prog)s "Remote collaboration" --visual "Globe with glowing connections" --effect drift
"""
    )
    parser.add_argument('context', help='Context/transcript segment to generate B-roll for')
    parser.add_argument('-o', '--output-dir', default='/tmp/broll', help='Output directory')
    parser.add_argument('-t', '--topic', help='Optional topic hint for better targeting')
    parser.add_argument('-d', '--duration', type=float, default=3.0, help='Video duration in seconds')
    parser.add_argument('-e', '--effect', default='ken_burns_in', choices=BROLL_EFFECTS,
                        help='Animation effect (default: ken_burns_in)')
    parser.add_argument('--image-only', action='store_true', help='Generate image only, no video')
    parser.add_argument('--id', help='Segment ID for filename')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--visual', help='Specific visual description (bypasses auto-detection)')
    parser.add_argument('--list-effects', action='store_true', help='List available effects and exit')

    args = parser.parse_args()

    if args.list_effects:
        print("Available B-roll animation effects (all include fade in/out):")
        print("  ken_burns_in   - Slow zoom in (default)")
        print("  ken_burns_out  - Zoom out from close")
        print("  ken_burns_pan  - Zoom in while panning right")
        print("  pan_left       - Pan from right to left")
        print("  pan_right      - Pan from left to right")
        print("  pulse          - Subtle pulsing/breathing zoom")
        print("  drift          - Diagonal movement with slight zoom")
        print("  none           - Static with fade in/out")
        sys.exit(0)

    if args.image_only:
        # Just generate image
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        segment_id = args.id or "generated"
        image_path = output_dir / f"broll_{segment_id}.png"

        prompt = generate_broll_prompt(args.context, args.topic, args.visual)
        if args.verbose:
            print(f"Prompt:\n{prompt}\n")

        result = generate_image(prompt, str(image_path))
        if result:
            print(json.dumps({"success": True, "image_path": result}))
        else:
            print(json.dumps({"error": "Image generation failed"}))
            sys.exit(1)
    else:
        # Generate full B-roll video
        result = generate_broll_for_segment(
            args.context,
            args.output_dir,
            topic=args.topic,
            duration=args.duration,
            segment_id=args.id,
            visual_description=args.visual,
            effect=args.effect
        )

        print(json.dumps(result, indent=2))

        if "error" in result:
            sys.exit(1)


if __name__ == '__main__':
    main()
