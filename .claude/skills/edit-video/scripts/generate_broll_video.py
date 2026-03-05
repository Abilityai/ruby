#!/usr/bin/env python3
"""
Generate cinematic B-roll videos using Google Veo 3.1 via Vertex AI.

This is the PRIMARY B-roll generation method for edit-video skill.
Generates 8-second cinematic clips with motion and audio.

Usage:
    python generate_broll_video.py <context> -o <output_dir> --id <segment_id>

Options:
    --visual PROMPT    Agent-written visual prompt (used directly)
    --style STYLE      B-roll style: cinematic, abstract, tech, minimal, diorama (default)
    --duration SECS    Target duration (will trim from 8s Veo output)
    --aspect RATIO     Aspect ratio: 16:9 (default), 9:16
    --fast             Use faster model (lower quality)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Skill directory (parent of scripts/)
SKILL_DIR = Path(__file__).parent.parent

# Veo generation script location
VEO_SKILL_DIR = SKILL_DIR.parent / "create-veo-video"
VEO_SCRIPT = VEO_SKILL_DIR / "scripts" / "generate_video.py"
VEO_VENV = VEO_SKILL_DIR / ".venv" / "bin" / "python"


# the creator's B-roll style guidelines for Veo
BROLL_STYLE_TEMPLATES = {
    "cinematic": """Cinematic B-roll for a tech video. Dark moody atmosphere with dramatic lighting.
Professional documentary-style footage.

VISUAL: {concept}

CINEMATOGRAPHY:
- Slow, purposeful camera movement
- Shallow depth of field
- Dramatic rim lighting or volumetric rays
- Dark environment with selective illumination
- Color palette: Deep blacks, electric blues (#00ffff), subtle white highlights

AUDIO: Ambient atmospheric sound, subtle technology hum, no music

Make it feel like a frame from a Netflix documentary about technology.""",

    "abstract": """Abstract technology visualization B-roll.

VISUAL: {concept}

Create flowing, abstract digital elements:
- Particle systems moving through dark space
- Geometric shapes transforming and connecting
- Neural network-like patterns with glowing nodes
- Data visualization aesthetic
- Color palette: Electric cyan (#00ffff), white, on pure black

Movement should be smooth and hypnotic. No recognizable text or UI elements.
Silent or subtle ambient sound.""",

    "tech": """Technology-focused B-roll for business content.

VISUAL: {concept}

Show sleek, modern technology:
- Clean lines and minimal design
- Soft glow on edges and screens
- Dark environment with selective lighting
- Professional, corporate aesthetic
- Color palette: Black, white, cyan accents (#00ffff)

Camera: Slow dolly or orbit movement. Macro-style details.
Audio: Quiet room ambiance, subtle tech sounds.""",

    "minimal": """Minimal, elegant B-roll visualization.

VISUAL: {concept}

Create a simple, focused composition:
- Single subject or concept
- Lots of negative space (dark/black)
- Subtle, elegant motion
- High contrast lighting
- Monochromatic with cyan (#00ffff) accent

Camera: Very slow push-in or static with subtle movement in frame.
Audio: Near silence, perhaps soft ambient tone.""",

    # "diorama" style: Agent writes complete prompts following .claude/skills/broll-diorama-style/SKILL.md
    # No template needed here - prompts are passed through unchanged
    "diorama": None,
}


def build_veo_prompt(context: str, visual_prompt: str = None, style: str = "cinematic") -> str:
    """Build a Veo-optimized prompt for B-roll generation.

    Args:
        context: What the speaker is saying (for context)
        visual_prompt: Agent-written visual description (used if provided)
        style: B-roll style preset

    Returns:
        Complete prompt for Veo generation
    """
    # DIORAMA STYLE: Agent writes complete prompts following the style guide
    # Pass through unchanged - no cinematic wrapper (diorama has warm lighting, not dark)
    # Style guide: .claude/skills/broll-diorama-style/SKILL.md
    if style == "diorama":
        if visual_prompt:
            # Agent already wrote complete diorama prompt - use as-is
            return visual_prompt
        else:
            # Fallback: basic diorama guidance if no visual prompt provided
            return f"""Create a miniature diorama B-roll video.

Context: {context}

Create a tiny handcrafted world inside a shoebox or similar container.
Include wire-and-bead workers, craft materials (cardboard, ribbon, toothpicks),
and a red game-piece figure as foreman.
Warm desk lamp lighting, tilt-shift shallow depth of field.
Slow camera movement. 8 seconds. Whimsical, educational mood."""

    # If agent provided a complete visual prompt, enhance it with style guidance
    if visual_prompt:
        # Agent prompts should be detailed, but add cinematic guidance
        return f"""Create B-roll video for a tech talking-head video.

{visual_prompt}

MANDATORY STYLE REQUIREMENTS:
- Dark/black background environment
- Professional cinematic quality
- Color accents: Electric cyan (#00ffff), white highlights
- Slow, purposeful camera movement
- Dramatic lighting (rim lights, volumetric rays)
- NO text, NO UI elements, NO faces
- 8 seconds, seamless loop-friendly

This should look like footage from a premium tech documentary."""

    # Use style template with context
    template = BROLL_STYLE_TEMPLATES.get(style, BROLL_STYLE_TEMPLATES["cinematic"])

    # Extract key concepts from context for better targeting
    context_summary = context[:150] if len(context) > 150 else context

    return template.format(concept=context_summary)


def generate_veo_broll(
    prompt: str,
    output_path: str,
    aspect_ratio: str = "16:9",
    fast: bool = False
) -> bool:
    """Generate video using Veo.

    Args:
        prompt: Complete Veo prompt
        output_path: Where to save the video
        aspect_ratio: 16:9 or 9:16
        fast: Use fast model (lower quality)

    Returns:
        True if successful
    """
    if not VEO_SCRIPT.exists():
        print(f"Error: Veo script not found: {VEO_SCRIPT}")
        return False

    # Find Python - prefer venv
    python_cmd = str(VEO_VENV) if VEO_VENV.exists() else sys.executable

    # Build command
    model = "veo-3.1-fast-generate-preview" if fast else "veo-3.1-generate-preview"
    cmd = [
        python_cmd,
        str(VEO_SCRIPT),
        prompt,
        output_path,
        "--model", model,
        "--aspect", aspect_ratio
    ]

    print(f"Generating Veo B-roll ({model})...")
    print(f"Prompt: {prompt[:100]}...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode == 0 and os.path.exists(output_path):
            print(f"Generated: {output_path}")
            return True
        else:
            print(f"Veo generation failed: {result.stderr[:500] if result.stderr else 'Unknown error'}")
            return False

    except subprocess.TimeoutExpired:
        print("Veo generation timed out (10 minutes)")
        return False
    except Exception as e:
        print(f"Veo generation error: {e}")
        return False


def trim_video(input_path: str, output_path: str, duration: float) -> bool:
    """Trim video to specified duration.

    Veo generates ~8 second videos. We trim to the exact duration needed.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-t", str(duration),
        "-c:v", "copy",
        "-c:a", "copy",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"Trimmed to {duration}s: {output_path}")
            return True
        else:
            print(f"Trim failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Trim error: {e}")
        return False


def generate_broll_for_segment(
    context: str,
    output_dir: str,
    visual_prompt: str = None,
    style: str = "cinematic",
    duration: float = 8.0,
    segment_id: str = None,
    aspect_ratio: str = "16:9",
    fast: bool = False
) -> dict:
    """Generate a complete Veo B-roll video for a segment.

    Args:
        context: What the speaker is saying
        output_dir: Directory to save output
        visual_prompt: Agent-written visual description
        style: B-roll style preset
        duration: Target duration (trims from 8s Veo output)
        segment_id: Unique ID for filenames
        aspect_ratio: 16:9 or 9:16
        fast: Use fast model

    Returns:
        dict with video_path and metadata
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique ID if not provided
    if not segment_id:
        import hashlib
        segment_id = hashlib.md5(context.encode()).hexdigest()[:8]

    # Paths
    raw_video_path = output_dir / f"broll_{segment_id}_raw.mp4"
    final_video_path = output_dir / f"broll_{segment_id}.mp4"

    # Build prompt
    prompt = build_veo_prompt(context, visual_prompt, style)

    # Generate with Veo
    print(f"Generating Veo B-roll for: {context[:50]}...")
    success = generate_veo_broll(
        prompt=prompt,
        output_path=str(raw_video_path),
        aspect_ratio=aspect_ratio,
        fast=fast
    )

    if not success:
        return {"error": "Veo generation failed", "context": context[:100]}

    # Trim to target duration
    if duration < 8.0:
        success = trim_video(str(raw_video_path), str(final_video_path), duration)
        if success:
            # Remove raw file
            raw_video_path.unlink(missing_ok=True)
        else:
            # Use raw file if trim fails
            raw_video_path.rename(final_video_path)
    else:
        # No trim needed
        raw_video_path.rename(final_video_path)

    return {
        "success": True,
        "video_path": str(final_video_path),
        "duration": duration,
        "style": style,
        "context": context[:100],
        "prompt": prompt[:200] + "...",
        "source": "veo"
    }


def main():
    parser = argparse.ArgumentParser(
        description='Generate cinematic B-roll videos using Veo 3.1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
B-Roll Styles:
  cinematic  Dark, dramatic, documentary-style (default)
  abstract   Flowing particles, neural networks, data viz
  tech       Clean technology, modern gadgets, screens
  minimal    Simple, single subject, lots of negative space

Examples:
  %(prog)s "AI agents collaborating" -o /tmp/broll --id broll_01
  %(prog)s "Neural networks" --style abstract --duration 5.0
  %(prog)s "Remote work" --visual "Person typing on laptop, soft lamp light"
"""
    )
    parser.add_argument('context', help='Context/transcript segment to generate B-roll for')
    parser.add_argument('-o', '--output-dir', default='/tmp/broll', help='Output directory')
    parser.add_argument('--id', help='Segment ID for filename')
    parser.add_argument('--visual', help='Specific visual prompt (bypasses auto-generation)')
    parser.add_argument('--style', default='cinematic',
                        choices=['cinematic', 'abstract', 'tech', 'minimal', 'diorama'],
                        help='B-roll style (default: cinematic)')
    parser.add_argument('-d', '--duration', type=float, default=8.0,
                        help='Target duration in seconds (default: 8.0, full Veo output)')
    parser.add_argument('--aspect', default='16:9', choices=['16:9', '9:16'],
                        help='Aspect ratio (default: 16:9)')
    parser.add_argument('--fast', action='store_true',
                        help='Use fast model (lower quality, faster generation)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    result = generate_broll_for_segment(
        context=args.context,
        output_dir=args.output_dir,
        visual_prompt=args.visual,
        style=args.style,
        duration=args.duration,
        segment_id=args.id,
        aspect_ratio=args.aspect,
        fast=args.fast
    )

    print(json.dumps(result, indent=2))

    if "error" in result:
        sys.exit(1)


if __name__ == '__main__':
    main()
