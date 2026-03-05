#!/usr/bin/env python3
"""
Execute video edits from EDL using FFmpeg - V2 Single-Pass Architecture.

Key differences from v1:
- Single FFmpeg command for all B-roll insertions (no cascading re-encodes)
- Audio stream copy (no re-encoding = no artifacts, perfect sync)
- Video encoded only once at the end (maximum quality)
- No concat operations (no cumulative timing drift)

Supports:
- Insert B-roll (overlay with time-based enable)
- Cut segments
- Speed adjustments
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Tuple


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


def get_video_info(video_path: str) -> dict:
    """Get video resolution, framerate, and duration."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,r_frame_rate',
        '-show_entries', 'format=duration',
        '-of', 'json', video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    stream = data['streams'][0]
    return {
        'width': stream['width'],
        'height': stream['height'],
        'framerate': stream['r_frame_rate'],
        'duration': float(data['format']['duration'])
    }


def resolve_asset_path(asset_path: str) -> str:
    """Resolve asset path relative to assets directory."""
    if os.path.isabs(asset_path) and os.path.exists(asset_path):
        return asset_path

    assets_dir = Path(__file__).parent.parent.parent / 'resources' / 'assets'
    full_path = assets_dir / asset_path
    if full_path.exists():
        return str(full_path)

    for ext in ['', '.mp4', '.mov', '.webm']:
        candidate = assets_dir / 'broll' / (asset_path + ext)
        if candidate.exists():
            return str(candidate)

    return asset_path


def generate_broll_on_demand(
    context: str,
    output_dir: str,
    segment_id: str,
    duration: float = 3.0,
    effect: str = 'ken_burns_in'
) -> Optional[str]:
    """Generate AI B-roll when no suitable asset exists."""
    generate_script = Path(__file__).parent / 'generate_broll_image.py'

    if not generate_script.exists():
        print(f"  Warning: B-roll generation script not found: {generate_script}")
        return None

    os.makedirs(output_dir, exist_ok=True)

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
            try:
                output_data = json.loads(result.stdout)
                if output_data.get('success') and output_data.get('video_path'):
                    return output_data['video_path']
            except json.JSONDecodeError:
                pass

            expected_path = os.path.join(output_dir, f'broll_{segment_id}.mp4')
            if os.path.exists(expected_path):
                return expected_path

        print(f"    B-roll generation failed: {result.stderr[:200] if result.stderr else 'Unknown error'}")
        return None

    except subprocess.TimeoutExpired:
        print("    B-roll generation timed out (120s)")
        return None
    except Exception as e:
        print(f"    B-roll generation error: {e}")
        return None


def prepare_broll_assets(
    broll_edits: List[dict],
    tmpdir: str
) -> List[Tuple[dict, str]]:
    """
    Prepare all B-roll assets upfront (download, generate AI, etc.)
    Returns list of (edit, asset_path) tuples for valid assets.
    """
    prepared = []

    for i, edit in enumerate(broll_edits):
        at = parse_timestamp(edit['at'])
        asset_path = resolve_asset_path(edit.get('asset_path') or edit.get('asset', ''))

        if not os.path.exists(asset_path):
            print(f"  [{i+1}/{len(broll_edits)}] Asset not found: {asset_path}")
            print(f"    Attempting AI generation...")

            context = edit.get('context', '') or edit.get('reason', '') or f"B-roll for {edit.get('asset', 'visual content')}"
            segment_id = f"gen_{i}_{int(at)}"
            effect = edit.get('effect', 'ken_burns_in')
            duration = edit.get('duration', 3.0)

            generated_path = generate_broll_on_demand(
                context=context,
                output_dir=tmpdir,
                segment_id=segment_id,
                duration=duration,
                effect=effect
            )

            if generated_path and os.path.exists(generated_path):
                asset_path = generated_path
                print(f"    Generated: {asset_path}")
            else:
                print(f"    Skipping B-roll at {edit['at']} (no asset)")
                continue
        else:
            print(f"  [{i+1}/{len(broll_edits)}] Found asset: {os.path.basename(asset_path)}")

        prepared.append((edit, asset_path))

    return prepared


def build_overlay_filter(
    main_info: dict,
    broll_assets: List[Tuple[dict, str]],
    tmpdir: str
) -> Tuple[str, List[str]]:
    """
    Build a single complex filter for all B-roll overlays.

    Returns:
        (filter_complex_string, list_of_input_files)
    """
    width = main_info['width']
    height = main_info['height']
    framerate = main_info['framerate']

    if not broll_assets:
        return "", []

    input_files = []
    filter_parts = []

    # Scale and prepare each B-roll input
    # CRITICAL: Use setpts to shift B-roll timestamps to match when they should appear
    # Without this, B-roll at t=10s would try to read frame 10 from a 3s video (doesn't exist)
    for i, (edit, asset_path) in enumerate(broll_assets):
        input_files.append(asset_path)
        input_idx = i + 1  # 0 is main video
        at = parse_timestamp(edit['at'])

        # Scale B-roll to match main video, convert to same framerate
        # setpts=PTS-STARTPTS+{at}/TB shifts the B-roll so frame 0 appears at time {at}
        filter_parts.append(
            f"[{input_idx}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={framerate},"
            f"setpts=PTS-STARTPTS+{at:.3f}/TB[b{i}]"
        )

    # Chain overlays: [0:v][b0]overlay[v0]; [v0][b1]overlay[v1]; ...
    current_video = "0:v"
    for i, (edit, _) in enumerate(broll_assets):
        at = parse_timestamp(edit['at'])
        duration = edit.get('duration', 3.0)
        end = at + duration

        output_label = f"v{i}"

        # Use overlay with enable to show B-roll only during specified time
        # eof_action=pass continues showing main video when B-roll ends
        filter_parts.append(
            f"[{current_video}][b{i}]overlay=eof_action=pass:enable='between(t,{at:.3f},{end:.3f})'[{output_label}]"
        )

        current_video = output_label

    filter_complex = ";".join(filter_parts)
    final_video_label = f"v{len(broll_assets) - 1}"

    return filter_complex, input_files, final_video_label


def execute_broll_single_pass(
    source_video: str,
    broll_assets: List[Tuple[dict, str]],
    output_path: str,
    crf: int = 15,
    audio_bitrate: str = '256k'
) -> str:
    """
    Execute all B-roll insertions in a single FFmpeg pass.

    Key benefits:
    - Audio is stream-copied (no re-encoding = no artifacts)
    - Video encoded only once (no quality degradation)
    - No concat operations (no timing drift)
    """
    main_info = get_video_info(source_video)

    print(f"\nSource video: {main_info['width']}x{main_info['height']} @ {main_info['framerate']} fps")
    print(f"Duration: {main_info['duration']:.2f}s")
    print(f"B-roll insertions: {len(broll_assets)}")

    if not broll_assets:
        print("No B-roll to insert, copying source")
        subprocess.run(['cp', source_video, output_path], check=True)
        return output_path

    # Build the complex filter
    with tempfile.TemporaryDirectory() as tmpdir:
        filter_complex, input_files, final_label = build_overlay_filter(
            main_info, broll_assets, tmpdir
        )

        # Build FFmpeg command
        cmd = ['ffmpeg', '-y']

        # Add main video input
        cmd.extend(['-i', source_video])

        # Add all B-roll inputs
        for f in input_files:
            cmd.extend(['-i', f])

        # Add the complex filter
        cmd.extend(['-filter_complex', filter_complex])

        # Map the final video and original audio
        cmd.extend([
            '-map', f'[{final_label}]',  # Final overlayed video
            '-map', '0:a',                # Original audio (stream copy)
        ])

        # Video encoding settings (single pass, high quality)
        cmd.extend([
            '-c:v', 'libx264',
            '-crf', str(crf),
            '-preset', 'medium',  # Better quality than 'fast'
            '-profile:v', 'high',
            '-level', '4.1',
        ])

        # Audio: stream copy to preserve original (no re-encoding!)
        cmd.extend(['-c:a', 'copy'])

        # Output
        cmd.extend(['-movflags', '+faststart', output_path])

        print(f"\nExecuting single-pass FFmpeg command...")
        print(f"Filter complexity: {len(broll_assets)} overlay operations")
        print(f"\nFirst overlay filter sample:")
        # Show first filter for debugging
        filter_lines = filter_complex.split(';')
        for line in filter_lines[:4]:
            print(f"  {line}")
        if len(filter_lines) > 4:
            print(f"  ... and {len(filter_lines) - 4} more filter operations")

        # Run FFmpeg
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr[-2000:]}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)

        print(f"\nSuccess! Output: {output_path}")
        return output_path


def execute_cuts(source_video: str, cut_edits: List[dict], output_path: str) -> str:
    """
    Apply cuts by extracting segments to keep and concatenating.
    Uses Transport Stream intermediate to avoid sync issues.
    """
    if not cut_edits:
        return source_video

    duration = get_video_duration(source_video)

    # Sort cuts by start time
    sorted_cuts = sorted(cut_edits, key=lambda e: parse_timestamp(e['start']))

    # Calculate segments to keep
    keep_segments = []
    last_end = 0.0

    for edit in sorted_cuts:
        cut_start = parse_timestamp(edit['start'])
        cut_end = parse_timestamp(edit['end'])

        if cut_start > last_end:
            keep_segments.append((last_end, cut_start))
        last_end = cut_end

    # Keep final segment
    if last_end < duration:
        keep_segments.append((last_end, duration))

    if not keep_segments:
        raise ValueError("All content would be cut!")

    print(f"\nApplying {len(cut_edits)} cuts, keeping {len(keep_segments)} segments")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract segments as Transport Stream (better for concat)
        ts_files = []
        for i, (start, end) in enumerate(keep_segments):
            ts_path = os.path.join(tmpdir, f'segment_{i}.ts')
            cmd = [
                'ffmpeg', '-y',
                '-i', source_video,
                '-ss', str(start),
                '-to', str(end),
                '-c', 'copy',
                '-bsf:v', 'h264_mp4toannexb',
                '-f', 'mpegts',
                ts_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            ts_files.append(ts_path)
            print(f"  Segment {i+1}: {start:.2f}s - {end:.2f}s")

        # Concatenate TS files back to MP4
        concat_input = "concat:" + "|".join(ts_files)
        cmd = [
            'ffmpeg', '-y',
            '-i', concat_input,
            '-c', 'copy',
            '-bsf:a', 'aac_adtstoasc',
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    return output_path


def execute_edl(edl: dict, output_path: Optional[str] = None, dry_run: bool = False) -> str:
    """Execute all edits in EDL using single-pass architecture."""

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

    print(f"EDL Summary:")
    print(f"  B-roll insertions: {len(broll_edits)}")
    print(f"  Cuts: {len(cut_edits)}")
    print(f"  Speed changes: {len(speed_edits)}")

    if dry_run:
        print("\nDry run - no changes made")
        return output

    current_video = source_video

    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Apply cuts first (if any)
        if cut_edits:
            cut_output = os.path.join(tmpdir, 'after_cuts.mp4')
            current_video = execute_cuts(current_video, cut_edits, cut_output)
            print(f"Cuts applied: {current_video}")

        # Step 2: Prepare all B-roll assets (generate AI ones upfront)
        if broll_edits:
            print(f"\nPreparing {len(broll_edits)} B-roll assets...")
            broll_assets = prepare_broll_assets(broll_edits, tmpdir)

            if broll_assets:
                # Step 3: Apply all B-roll in single pass
                broll_output = os.path.join(tmpdir, 'after_broll.mp4') if speed_edits else output
                current_video = execute_broll_single_pass(
                    current_video, broll_assets, broll_output
                )

        # Step 4: Apply speed changes (if any) - requires re-encoding
        if speed_edits:
            print(f"\nApplying {len(speed_edits)} speed changes...")
            # Speed changes are complex and less common, keep simple for now
            for edit in speed_edits:
                print(f"  Warning: Speed changes not yet implemented in v2")

        # Copy final result to output if not already there
        if current_video != output:
            subprocess.run(['cp', current_video, output], check=True)

    print(f"\n{'='*50}")
    print(f"Final output: {output}")
    print(f"{'='*50}")

    return output


def main():
    parser = argparse.ArgumentParser(
        description='Execute video edits from EDL using FFmpeg (V2 Single-Pass)'
    )
    parser.add_argument('edl', help='EDL JSON file')
    parser.add_argument('-o', '--output', help='Output video path')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--crf', type=int, default=15, help='CRF quality (default: 15, lower = better)')

    args = parser.parse_args()

    edl_path = Path(args.edl)
    if not edl_path.exists():
        print(f"Error: EDL file not found: {edl_path}", file=sys.stderr)
        sys.exit(1)

    edl = json.loads(edl_path.read_text())

    try:
        output = execute_edl(edl, args.output, args.dry_run)
        if not args.dry_run:
            print(f"\nSuccess! Output: {output}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
