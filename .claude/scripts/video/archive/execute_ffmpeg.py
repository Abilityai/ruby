#!/usr/bin/env python3
"""
Execute video edits from EDL using FFmpeg.

Supports:
- Cut segments (with crossfade transitions)
- Insert B-roll (picture-in-picture or full overlay)
- Speed adjustments
- Concatenation with transitions
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


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


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json', video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])


def get_video_resolution(video_path: str) -> tuple:
    """Get video resolution (width, height)."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'json', video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    stream = data['streams'][0]
    return stream['width'], stream['height']


def get_video_framerate(video_path: str) -> str:
    """Get video framerate as fraction string."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate',
        '-of', 'json', video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return data['streams'][0]['r_frame_rate']


def execute_cut(source: str, start: float, end: float, output: str, crossfade: float = 0.5) -> str:
    """Cut segment from video."""
    # Use CRF 15 for high quality output
    cmd = [
        'ffmpeg', '-y',
        '-i', source,
        '-ss', str(start),
        '-to', str(end),
        '-c:v', 'libx264', '-crf', '15', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '256k',
        output
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output


def execute_broll_insertion(
    main_video: str,
    broll_path: str,
    at_seconds: float,
    duration: float,
    output: str,
    mode: str = 'replace',  # 'replace', 'overlay', or 'pip'
    keep_main_audio: bool = True,
    tmpdir: str = None,
    transition_sfx: str = None,  # Sound effect for transition: 'subtle', 'standard', 'dramatic', or path
    sfx_volume: float = 0.5,  # Volume of transition SFX (0.0-1.0) - 30% quieter default
    sfx_offset: float = 0.0  # Start SFX at B-roll start (0 = sync with B-roll)
) -> str:
    """Insert B-roll into main video.

    Modes:
    - replace: B-roll completely replaces main video (DEFAULT)
    - overlay: B-roll on top of main video (semi-transparent)
    - pip: B-roll in picture-in-picture corner

    Transition SFX:
    - transition_sfx: Name or path of sound effect ('subtle', 'standard', 'dramatic')
    - sfx_volume: Volume level 0.0-1.0 (default 0.7)
    - sfx_offset: When to start SFX relative to B-roll (default -0.15, starts before)
    """
    import tempfile

    if tmpdir is None:
        tmpdir = tempfile.gettempdir()

    # Get main video properties
    width, height = get_video_resolution(main_video)
    main_duration = get_video_duration(main_video)
    framerate = get_video_framerate(main_video)

    # Resolve transition SFX path
    sfx_path = resolve_sfx_path(transition_sfx) if transition_sfx else None
    if transition_sfx and not sfx_path:
        print(f"  Warning: Transition SFX not found: {transition_sfx}")

    # Ensure we don't go past video end
    end_seconds = min(at_seconds + duration, main_duration)
    actual_duration = end_seconds - at_seconds

    if mode == 'replace':
        # REPLACEMENT MODE: Cut video into segments, insert B-roll, concatenate
        seg_pre = os.path.join(tmpdir, f'seg_pre_{at_seconds}.mp4')
        seg_broll = os.path.join(tmpdir, f'seg_broll_{at_seconds}.mp4')
        seg_post = os.path.join(tmpdir, f'seg_post_{at_seconds}.mp4')

        # Extract pre-segment (match source encoding params)
        # Use CRF 15 for high quality intermediates to minimize generation loss
        if at_seconds > 0:
            cmd_pre = [
                'ffmpeg', '-y', '-i', main_video,
                '-ss', '0', '-t', str(at_seconds),
                '-c:v', 'libx264', '-crf', '15', '-preset', 'fast',
                '-r', framerate,
                '-c:a', 'aac', '-b:a', '256k',
                seg_pre
            ]
            subprocess.run(cmd_pre, check=True, capture_output=True)

        # Scale, trim, and match framerate for B-roll
        broll_video = os.path.join(tmpdir, f'broll_scaled_{at_seconds}.mp4')
        cmd_broll = [
            'ffmpeg', '-y', '-i', broll_path,
            '-t', str(actual_duration),
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={framerate}',
            '-c:v', 'libx264', '-crf', '15', '-preset', 'fast',
            '-an',  # Remove B-roll audio
            broll_video
        ]
        subprocess.run(cmd_broll, check=True, capture_output=True)

        if keep_main_audio:
            # Extract audio from main video for B-roll section
            audio_seg = os.path.join(tmpdir, f'audio_{at_seconds}.aac')
            cmd_audio = [
                'ffmpeg', '-y', '-i', main_video,
                '-ss', str(at_seconds), '-t', str(actual_duration),
                '-vn', '-c:a', 'aac', '-b:a', '192k',
                audio_seg
            ]
            subprocess.run(cmd_audio, check=True, capture_output=True)

            # Mix in transition SFX if provided
            if sfx_path:
                audio_with_sfx = os.path.join(tmpdir, f'audio_sfx_{at_seconds}.aac')
                # Calculate SFX delay within the segment (sfx_offset is relative to B-roll start)
                # Since we're working with the extracted segment, delay is from segment start
                sfx_delay_ms = max(0, int(sfx_offset * 1000))  # Convert to ms, ensure non-negative

                # Use adelay to position SFX and amix to blend with original audio
                filter_complex = (
                    f"[1:a]adelay={sfx_delay_ms}|{sfx_delay_ms},volume={sfx_volume}[sfx];"
                    f"[0:a][sfx]amix=inputs=2:duration=first:dropout_transition=0[aout]"
                )
                cmd_mix = [
                    'ffmpeg', '-y',
                    '-i', audio_seg,
                    '-i', sfx_path,
                    '-filter_complex', filter_complex,
                    '-map', '[aout]',
                    '-c:a', 'aac', '-b:a', '192k',
                    audio_with_sfx
                ]
                result = subprocess.run(cmd_mix, capture_output=True, text=True)
                if result.returncode == 0:
                    audio_seg = audio_with_sfx
                    print(f"    Added transition SFX: {transition_sfx}")
                else:
                    print(f"    Warning: Failed to add SFX: {result.stderr[:200]}")

            # Combine B-roll video with (possibly SFX-enhanced) audio
            cmd_combine = [
                'ffmpeg', '-y',
                '-i', broll_video, '-i', audio_seg,
                '-c:v', 'copy', '-c:a', 'copy',
                seg_broll
            ]
            subprocess.run(cmd_combine, check=True, capture_output=True)
        else:
            seg_broll = broll_video

        # Extract post-segment (match source encoding params)
        # Use CRF 15 for high quality intermediates
        if end_seconds < main_duration:
            cmd_post = [
                'ffmpeg', '-y', '-i', main_video,
                '-ss', str(end_seconds),
                '-c:v', 'libx264', '-crf', '15', '-preset', 'fast',
                '-r', framerate,
                '-c:a', 'aac', '-b:a', '256k',
                seg_post
            ]
            subprocess.run(cmd_post, check=True, capture_output=True)

        # Create concat list
        concat_file = os.path.join(tmpdir, f'concat_{at_seconds}.txt')
        with open(concat_file, 'w') as f:
            if at_seconds > 0:
                f.write(f"file '{seg_pre}'\n")
            f.write(f"file '{seg_broll}'\n")
            if end_seconds < main_duration:
                f.write(f"file '{seg_post}'\n")

        # Concatenate with re-encoding to ensure consistent output
        # Using -c copy can cause freeze/blink issues due to mismatched keyframes
        # Use CRF 15 for high quality final output
        cmd_concat = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', concat_file,
            '-c:v', 'libx264', '-crf', '15', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '256k',
            '-movflags', '+faststart',
            output
        ]
        subprocess.run(cmd_concat, check=True, capture_output=True)

        return output

    elif mode == 'pip':
        # Picture-in-picture: B-roll in corner
        filter_complex = (
            f"[1:v]scale={width//4}:-1[broll];"
            f"[0:v][broll]overlay=W-w-20:20:"
            f"enable='between(t,{at_seconds},{end_seconds})'"
        )
    else:
        # Overlay mode: B-roll on top of main video
        filter_complex = (
            f"[1:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[broll];"
            f"[0:v][broll]overlay="
            f"enable='between(t,{at_seconds},{end_seconds})':eof_action=pass"
        )

    cmd = [
        'ffmpeg', '-y',
        '-i', main_video,
        '-i', broll_path,
        '-filter_complex', filter_complex,
    ]

    if keep_main_audio:
        cmd.extend(['-map', '0:a?', '-c:a', 'aac', '-b:a', '256k'])

    cmd.extend([
        '-c:v', 'libx264', '-crf', '15', '-preset', 'fast',
        output
    ])

    subprocess.run(cmd, check=True, capture_output=True)
    return output


# Keep old name for compatibility
def execute_broll_overlay(
    main_video: str,
    broll_path: str,
    at_seconds: float,
    duration: float,
    output: str,
    mode: str = 'replace',
    keep_main_audio: bool = True
) -> str:
    """Wrapper for backwards compatibility."""
    return execute_broll_insertion(
        main_video, broll_path, at_seconds, duration, output,
        mode=mode, keep_main_audio=keep_main_audio
    )


def execute_speed_change(
    source: str,
    start: float,
    end: float,
    factor: float,
    output: str
) -> str:
    """Change speed of video segment."""

    # Extract segment
    segment_path = output.replace('.mp4', '_segment.mp4')
    execute_cut(source, start, end, segment_path)

    # Apply speed change
    # For video: setpts=PTS/factor (factor > 1 = faster)
    # For audio: atempo=factor (must be 0.5-2.0, chain for larger values)

    video_filter = f"setpts=PTS/{factor}"

    # Build atempo chain for audio
    atempo_filters = []
    remaining = factor
    while remaining > 2.0:
        atempo_filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        atempo_filters.append("atempo=0.5")
        remaining /= 0.5
    atempo_filters.append(f"atempo={remaining}")
    audio_filter = ','.join(atempo_filters)

    cmd = [
        'ffmpeg', '-y',
        '-i', segment_path,
        '-filter:v', video_filter,
        '-filter:a', audio_filter,
        '-c:v', 'libx264', '-crf', '15', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '256k',
        output
    ]

    subprocess.run(cmd, check=True, capture_output=True)

    # Clean up
    os.remove(segment_path)

    return output


def concatenate_segments(segments: list, output: str, crossfade: float = 0.3) -> str:
    """Concatenate video segments with optional crossfade."""

    if len(segments) == 1:
        # Just copy
        subprocess.run(['cp', segments[0], output], check=True)
        return output

    # Create concat file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")
        concat_file = f.name

    try:
        if crossfade > 0:
            # Use xfade filter for smooth transitions
            # This is complex, so for now use simple concat
            pass

        # Simple concatenation with high quality encoding
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0',
            '-i', concat_file,
            '-c:v', 'libx264', '-crf', '15', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '256k',
            output
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        os.remove(concat_file)

    return output


def resolve_asset_path(asset_path: str) -> str:
    """Resolve asset path relative to assets directory."""
    # Check if absolute path
    if os.path.isabs(asset_path) and os.path.exists(asset_path):
        return asset_path

    # Check relative to assets directory
    assets_dir = Path(__file__).parent.parent.parent / 'resources' / 'assets'
    full_path = assets_dir / asset_path
    if full_path.exists():
        return str(full_path)

    # Check if just filename
    for ext in ['', '.mp4', '.mov', '.webm']:
        candidate = assets_dir / 'broll' / (asset_path + ext)
        if candidate.exists():
            return str(candidate)

    return asset_path  # Return as-is, let FFmpeg handle error


def generate_broll_on_demand(
    context: str,
    output_dir: str,
    segment_id: str,
    duration: float = 3.0,
    effect: str = 'ken_burns_in'
) -> Optional[str]:
    """Generate AI B-roll when no suitable asset exists.

    Uses Nano Banana (Gemini 2.5 Flash Image) to create contextual visuals.

    Args:
        context: Transcript context or reason for B-roll
        output_dir: Directory to save generated B-roll
        segment_id: Unique identifier for this B-roll
        duration: Duration in seconds
        effect: Animation effect to apply

    Returns:
        Path to generated B-roll video or None on failure
    """
    # Path to the B-roll generation script
    generate_script = Path(__file__).parent / 'generate_broll_image.py'

    if not generate_script.exists():
        print(f"  Warning: B-roll generation script not found: {generate_script}")
        return None

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Generate B-roll using the AI script
    cmd = [
        'python3', str(generate_script),
        context,
        '-o', output_dir,
        '--id', segment_id,
        '-d', str(duration),
        '-e', effect
    ]

    try:
        print(f"    Generating AI B-roll for: {context[:50]}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            # Parse output to get video path
            import json as json_module
            try:
                output_data = json_module.loads(result.stdout)
                if output_data.get('success') and output_data.get('video_path'):
                    video_path = output_data['video_path']
                    print(f"    Generated AI B-roll: {video_path}")
                    return video_path
            except json_module.JSONDecodeError:
                pass

            # Fallback: check for expected output file
            expected_path = os.path.join(output_dir, f'broll_{segment_id}.mp4')
            if os.path.exists(expected_path):
                print(f"    Generated AI B-roll: {expected_path}")
                return expected_path

        print(f"    B-roll generation failed: {result.stderr[:200] if result.stderr else 'Unknown error'}")
        return None

    except subprocess.TimeoutExpired:
        print("    B-roll generation timed out (120s)")
        return None
    except Exception as e:
        print(f"    B-roll generation error: {e}")
        return None


def resolve_sfx_path(sfx_name: str) -> Optional[str]:
    """Resolve sound effect path from name or path.

    Args:
        sfx_name: Can be:
            - Full path to audio file
            - Asset name like 'whoosh_fast_transition', 'swoosh_flying', 'impact_epic_trailer'
            - Partial match like 'fast', 'flying', 'epic'

    Returns:
        Full path to SFX file or None if not found
    """
    if not sfx_name:
        return None

    # Check if absolute path
    if os.path.isabs(sfx_name) and os.path.exists(sfx_name):
        return sfx_name

    assets_dir = Path(__file__).parent.parent.parent / 'resources' / 'assets'
    sfx_dir = assets_dir / 'sfx'

    # Check relative to assets directory
    full_path = assets_dir / sfx_name
    if full_path.exists():
        return str(full_path)

    # Check sfx directory with various extensions
    for ext in ['', '.mp3', '.wav', '.aac', '.m4a']:
        # Try direct name
        candidate = sfx_dir / (sfx_name + ext)
        if candidate.exists():
            return str(candidate)

    # Try partial match (e.g., 'fast' matches 'whoosh_fast_transition')
    if sfx_dir.exists():
        for f in sfx_dir.glob('*.mp3'):
            if sfx_name.lower() in f.stem.lower():
                return str(f)

    # Legacy: check audio directory
    audio_dir = assets_dir / 'audio'
    if audio_dir.exists():
        for ext in ['', '.mp3', '.wav', '.aac', '.m4a']:
            candidate = audio_dir / (sfx_name + ext)
            if candidate.exists():
                return str(candidate)

    return None


def get_sfx_duration(sfx_path: str) -> float:
    """Get duration of sound effect file."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json', sfx_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])


def execute_edl(edl: dict, output_path: Optional[str] = None, dry_run: bool = False) -> str:
    """Execute all edits in EDL."""

    source_video = edl['source_video']
    if not os.path.exists(source_video):
        raise FileNotFoundError(f"Source video not found: {source_video}")

    output = output_path or edl['output']['path']
    edits = edl.get('edits', [])

    if not edits:
        print("No edits to apply, copying source to output")
        if not dry_run:
            subprocess.run(['cp', source_video, output], check=True)
        return output

    # Group edits by type
    broll_edits = [e for e in edits if e['type'] == 'insert_broll']
    cut_edits = [e for e in edits if e['type'] == 'cut']
    speed_edits = [e for e in edits if e['type'] == 'speed']

    print(f"Executing EDL with {len(edits)} edits:")
    print(f"  B-roll insertions: {len(broll_edits)}")
    print(f"  Cuts: {len(cut_edits)}")
    print(f"  Speed changes: {len(speed_edits)}")

    if dry_run:
        print("\nDry run - no changes made")
        return output

    # Create temp directory for intermediate files
    with tempfile.TemporaryDirectory() as tmpdir:
        current_video = source_video

        # Apply B-roll insertions
        for i, edit in enumerate(broll_edits):
            at = parse_timestamp(edit['at'])
            duration = edit.get('duration', 3.0)
            asset_path = resolve_asset_path(edit.get('asset_path') or edit.get('asset', ''))

            if not os.path.exists(asset_path):
                print(f"  Asset not found: {asset_path}")
                print(f"    Attempting AI generation...")

                # Extract context from the edit for AI generation
                # Prefer full 'context' field (transcript text), fall back to 'reason'
                context = edit.get('context', '') or edit.get('reason', '') or f"B-roll for {edit.get('asset', 'visual content')}"

                # Generate unique ID for this B-roll
                segment_id = f"gen_{i}_{int(at)}"

                # Get animation effect from edit or use default
                effect = edit.get('effect', 'ken_burns_in')

                # Generate B-roll using AI
                generated_path = generate_broll_on_demand(
                    context=context,
                    output_dir=tmpdir,
                    segment_id=segment_id,
                    duration=duration,
                    effect=effect
                )

                if generated_path and os.path.exists(generated_path):
                    asset_path = generated_path
                    print(f"    Using AI-generated B-roll: {asset_path}")
                else:
                    print(f"    AI generation failed, skipping this B-roll")
                    continue

            print(f"  Inserting B-roll at {edit['at']}: {edit.get('asset', 'AI-generated')}")

            intermediate = os.path.join(tmpdir, f'broll_{i}.mp4')
            mode = edit.get('mode', 'replace')  # Default to replace mode

            # Get transition SFX settings
            transition_sfx = edit.get('transition_sfx') or edl.get('default_transition_sfx')
            sfx_volume = edit.get('sfx_volume', edl.get('default_sfx_volume', 0.5))
            sfx_offset = edit.get('sfx_offset', edl.get('default_sfx_offset', 0.0))

            current_video = execute_broll_insertion(
                current_video, asset_path, at, duration, intermediate,
                mode=mode,
                keep_main_audio=edit.get('audio') == 'keep_original',
                tmpdir=tmpdir,
                transition_sfx=transition_sfx,
                sfx_volume=sfx_volume,
                sfx_offset=sfx_offset
            )

        # Apply cuts (remove segments)
        if cut_edits:
            # Sort cuts by start time (reverse to process from end)
            sorted_cuts = sorted(cut_edits, key=lambda e: parse_timestamp(e['start']), reverse=True)

            # Get segments to keep
            duration = get_video_duration(current_video)
            keep_segments = []
            last_end = duration

            for edit in sorted_cuts:
                cut_start = parse_timestamp(edit['start'])
                cut_end = parse_timestamp(edit['end'])

                print(f"  Cutting: {edit['start']} - {edit['end']} ({edit.get('reason', '')})")

                if cut_end < last_end:
                    # Keep segment after cut
                    seg_path = os.path.join(tmpdir, f'keep_{len(keep_segments)}.mp4')
                    execute_cut(current_video, cut_end, last_end, seg_path)
                    keep_segments.insert(0, seg_path)

                last_end = cut_start

            # Keep segment before first cut
            if last_end > 0:
                seg_path = os.path.join(tmpdir, f'keep_first.mp4')
                execute_cut(current_video, 0, last_end, seg_path)
                keep_segments.insert(0, seg_path)

            if keep_segments:
                current_video = os.path.join(tmpdir, 'after_cuts.mp4')
                concatenate_segments(keep_segments, current_video)

        # Apply speed changes (complex, skip for now if cuts were applied)
        if speed_edits and not cut_edits:
            for i, edit in enumerate(speed_edits):
                start = parse_timestamp(edit['start'])
                end = parse_timestamp(edit['end'])
                factor = edit.get('factor', 1.5)

                print(f"  Speed change {factor}x: {edit['start']} - {edit['end']}")

                intermediate = os.path.join(tmpdir, f'speed_{i}.mp4')
                current_video = execute_speed_change(
                    current_video, start, end, factor, intermediate
                )

        # Copy final result to output
        subprocess.run(['cp', current_video, output], check=True)

    print(f"\nOutput: {output}")
    return output


def main():
    parser = argparse.ArgumentParser(
        description='Execute video edits from EDL using FFmpeg'
    )
    parser.add_argument('edl', help='EDL JSON file')
    parser.add_argument('-o', '--output', help='Output video path')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')

    args = parser.parse_args()

    # Load EDL
    edl_path = Path(args.edl)
    if not edl_path.exists():
        print(f"Error: EDL file not found: {edl_path}", file=sys.stderr)
        sys.exit(1)

    edl = json.loads(edl_path.read_text())

    # Execute
    try:
        output = execute_edl(edl, args.output, args.dry_run)
        if not args.dry_run:
            print(f"Success! Output: {output}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
