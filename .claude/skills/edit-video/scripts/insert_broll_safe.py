#!/usr/bin/env python3
"""
Insert B-roll into video using the trim+concat filter method.

This is the CORRECT way to insert B-roll that preserves A/V sync.
It avoids the concat demuxer which causes timestamp drift.

Usage:
    python3 insert_broll_safe.py input.mp4 output.mp4 --broll broll.mp4:40:3 --broll broll2.mp4:70:3

    Each --broll argument is: path:start_time:duration
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def get_video_info(video_path: str) -> dict:
    """Get video properties."""
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
        'fps': stream['r_frame_rate'],
        'duration': float(data['format']['duration'])
    }


def insert_broll(
    input_video: str,
    output_video: str,
    broll_insertions: list,  # [(broll_path, start_time, duration), ...]
    tmpdir: str = None
) -> str:
    """
    Insert B-roll using the trim+concat filter method.

    This method:
    1. Trims main video into segments around B-roll points
    2. Scales B-roll to match main video
    3. Extracts audio from main video for B-roll sections
    4. Concatenates all using the concat FILTER (not demuxer)
    """

    if tmpdir is None:
        tmpdir = tempfile.mkdtemp(prefix='broll_')

    # Get main video info
    info = get_video_info(input_video)
    width, height = info['width'], info['height']
    fps = info['fps']
    duration = info['duration']

    print(f"Main video: {width}x{height} @ {fps} fps, {duration:.2f}s")

    # Sort insertions by start time
    insertions = sorted(broll_insertions, key=lambda x: x[1])

    # Calculate segment boundaries
    segments = []  # [(type, path, start, end), ...]

    last_end = 0
    for i, (broll_path, start_time, broll_duration) in enumerate(insertions):
        # Main segment before this B-roll
        if start_time > last_end:
            segments.append(('main', None, last_end, start_time))

        # B-roll segment
        segments.append(('broll', broll_path, start_time, start_time + broll_duration))

        last_end = start_time + broll_duration

    # Final main segment
    if last_end < duration:
        segments.append(('main', None, last_end, duration))

    print(f"\nSegments to process: {len(segments)}")

    # Create segment files
    segment_files = []

    for i, (seg_type, broll_path, start, end) in enumerate(segments):
        seg_duration = end - start
        seg_file = os.path.join(tmpdir, f'seg_{i:02d}.mp4')

        if seg_type == 'main':
            # Extract main video segment
            print(f"  Segment {i}: main video {start:.2f}s - {end:.2f}s")
            cmd = [
                'ffmpeg', '-y', '-i', input_video,
                '-ss', str(start), '-t', str(seg_duration),
                '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
                '-c:a', 'aac', '-b:a', '192k',
                seg_file
            ]
            subprocess.run(cmd, capture_output=True, check=True)

        else:
            # Create B-roll segment with original audio
            print(f"  Segment {i}: B-roll at {start:.2f}s ({seg_duration:.2f}s)")

            # Scale B-roll to match main video
            broll_scaled = os.path.join(tmpdir, f'broll_scaled_{i}.mp4')
            cmd_scale = [
                'ffmpeg', '-y', '-i', broll_path,
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,'
                       f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps}',
                '-t', str(seg_duration),
                '-an',
                '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
                broll_scaled
            ]
            subprocess.run(cmd_scale, capture_output=True, check=True)

            # Combine B-roll video with audio from main video
            cmd_combine = [
                'ffmpeg', '-y',
                '-i', broll_scaled,
                '-i', input_video,
                '-filter_complex',
                f'[1:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[aud]',
                '-map', '0:v', '-map', '[aud]',
                '-t', str(seg_duration),
                '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
                '-c:a', 'aac', '-b:a', '192k',
                seg_file
            ]
            subprocess.run(cmd_combine, capture_output=True, check=True)

        segment_files.append(seg_file)

    # Build concat filter command
    print(f"\nConcatenating {len(segment_files)} segments with concat filter...")

    # Build input args
    input_args = []
    for f in segment_files:
        input_args.extend(['-i', f])

    # Build filter string
    n = len(segment_files)
    filter_inputs = ''.join(f'[{i}:v][{i}:a]' for i in range(n))
    filter_str = f'{filter_inputs}concat=n={n}:v=1:a=1[outv][outa]'

    cmd_concat = [
        'ffmpeg', '-y',
        *input_args,
        '-filter_complex', filter_str,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'libx264', '-crf', '18', '-preset', 'medium',
        '-c:a', 'aac', '-b:a', '192k',
        '-movflags', '+faststart',
        output_video
    ]

    subprocess.run(cmd_concat, capture_output=True, check=True)

    print(f"\nOutput: {output_video}")
    return output_video


def main():
    parser = argparse.ArgumentParser(
        description='Insert B-roll using sync-safe trim+concat method'
    )
    parser.add_argument('input', help='Input video file')
    parser.add_argument('output', help='Output video file')
    parser.add_argument(
        '--broll', '-b',
        action='append',
        required=True,
        help='B-roll insertion: path:start_seconds:duration (can specify multiple)'
    )
    parser.add_argument(
        '--keep-temp',
        action='store_true',
        help='Keep temporary files'
    )

    args = parser.parse_args()

    # Parse B-roll arguments
    insertions = []
    for broll_arg in args.broll:
        parts = broll_arg.split(':')
        if len(parts) != 3:
            print(f"Error: Invalid B-roll format: {broll_arg}")
            print("Expected: path:start_seconds:duration")
            sys.exit(1)

        path, start, duration = parts
        if not os.path.exists(path):
            print(f"Error: B-roll file not found: {path}")
            sys.exit(1)

        insertions.append((path, float(start), float(duration)))

    # Create temp directory
    if args.keep_temp:
        tmpdir = tempfile.mkdtemp(prefix='broll_')
        print(f"Temp directory: {tmpdir}")
    else:
        tmpdir = None

    try:
        insert_broll(args.input, args.output, insertions, tmpdir)
        print("\nSuccess!")
    except subprocess.CalledProcessError as e:
        print(f"Error: FFmpeg failed")
        if e.stderr:
            print(e.stderr.decode())
        sys.exit(1)


if __name__ == '__main__':
    main()
