#!/usr/bin/env python3
"""
Generate Edit Decision List (EDL) from video analysis.

Takes analysis output from parse_transcript.py or analyze_video_gemini.py
and generates an EDL JSON file for execute_ffmpeg.py.
"""

import argparse
import json
import os
import re
import subprocess
import sys
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


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def load_asset_manifest() -> dict:
    """Load asset library manifest."""
    # Skill directory is parent of scripts/
    skill_dir = Path(__file__).parent.parent
    manifest_path = skill_dir / 'assets' / 'manifest.json'
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    return {'assets': [], 'tag_synonyms': {}}


def find_matching_asset(keywords: list, manifest: dict) -> Optional[dict]:
    """Find best matching asset for keywords."""
    keywords_lower = [k.lower() for k in keywords]

    # Expand synonyms
    expanded = set(keywords_lower)
    for kw in keywords_lower:
        for canonical, synonyms in manifest.get('tag_synonyms', {}).items():
            if kw == canonical.lower() or kw in [s.lower() for s in synonyms]:
                expanded.add(canonical.lower())
                expanded.update(s.lower() for s in synonyms)

    # Score assets by tag matches
    best_asset = None
    best_score = 0

    for asset in manifest.get('assets', []):
        if asset.get('type') != 'broll':
            continue

        asset_tags = [t.lower() for t in asset.get('tags', [])]
        score = len(expanded.intersection(asset_tags))

        if score > best_score:
            best_score = score
            best_asset = asset

    return best_asset if best_score > 0 else None


def find_keyword_matches_in_segments(segments: list, keywords: list) -> list:
    """Search segments for keyword occurrences."""
    matches = []
    keywords_lower = [k.lower() for k in keywords]

    for seg in segments:
        text_lower = seg.get('text', '').lower()
        for kw in keywords_lower:
            if kw in text_lower:
                ts = seg.get('start_formatted') or seg.get('start', 0)
                if isinstance(ts, (int, float)):
                    m = int(ts // 60)
                    s = ts % 60
                    ts = f"{m:02d}:{s:06.3f}"
                matches.append({
                    'keyword': kw,
                    'timestamp': ts,
                    'start_seconds': seg.get('start', 0),
                    'context': seg.get('text', '')[:100]
                })

    return matches


def generate_ai_broll(context: str, output_dir: str, segment_id: str) -> Optional[dict]:
    """Generate AI B-roll image/video when no asset matches.

    Uses Nano Banana (Gemini 2.5 Flash Image) to generate contextual visuals.
    """
    script_path = Path(__file__).parent / 'generate_broll_image.py'
    if not script_path.exists():
        return None

    try:
        cmd = [
            'python3', str(script_path),
            context,
            '-o', output_dir,
            '--id', segment_id,
            '-d', '3.0'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            try:
                output = json.loads(result.stdout)
                if output.get('success') and output.get('video_path'):
                    return {
                        'id': f'generated_{segment_id}',
                        'path': output['video_path'],
                        'type': 'broll',
                        'generated': True,
                        'duration': output.get('duration', 3.0)
                    }
            except json.JSONDecodeError:
                pass

        return None

    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"AI B-roll generation failed: {e}", file=sys.stderr)
        return None


def generate_broll_edits(analysis: dict, instruction: str, manifest: dict, generate_images: bool = False, output_dir: str = '/tmp/broll') -> list:
    """Generate B-roll insertion edits from analysis."""
    edits = []

    # Extract keywords from instruction (include 2-letter words like AI)
    instruction_keywords = re.findall(r'\b[A-Za-z]{2,}\b', instruction.lower())
    tech_keywords = ['ai', 'code', 'coding', 'programming', 'technology', 'tech',
                     'software', 'computer', 'algorithm', 'neural', 'machine', 'learning',
                     'data', 'server', 'cloud', 'api', 'agent', 'model', 'agents']

    # Find moments from analysis
    moments = analysis.get('moments', [])
    keyword_matches = analysis.get('keyword_matches', [])

    # If no keyword_matches provided, search segments for tech keywords
    if not keyword_matches and analysis.get('segments'):
        # Combine instruction keywords with tech keywords
        search_keywords = list(set(instruction_keywords) & set(tech_keywords))
        if not search_keywords:
            search_keywords = [k for k in instruction_keywords if len(k) > 2][:5]
        if not search_keywords:
            search_keywords = tech_keywords[:5]

        keyword_matches = find_keyword_matches_in_segments(
            analysis['segments'],
            search_keywords
        )

    # Process moments
    for moment in moments:
        ts = moment.get('at') or moment.get('timestamp')
        if not ts:
            continue

        description = moment.get('description', '') or moment.get('text', '')

        # Extract keywords from moment
        moment_keywords = re.findall(r'\b[A-Za-z]{3,}\b', description.lower())
        search_keywords = list(set(moment_keywords) & set(tech_keywords + instruction_keywords))

        if not search_keywords:
            search_keywords = moment_keywords[:3]

        # Find matching asset
        asset = find_matching_asset(search_keywords, manifest)

        if asset:
            edits.append({
                'type': 'insert_broll',
                'at': ts if isinstance(ts, str) else format_timestamp(ts),
                'duration': min(asset.get('duration', 3.0), 4.0),
                'asset': asset['id'],
                'asset_path': asset['path'],
                'audio': 'keep_original',
                'mode': 'replace',
                'reason': f"B-roll for: {description[:50]}"
            })
        elif generate_images:
            # Generate AI B-roll when no asset matches
            segment_id = f"moment_{len(edits)}"
            ai_asset = generate_ai_broll(description, output_dir, segment_id)
            if ai_asset:
                edits.append({
                    'type': 'insert_broll',
                    'at': ts if isinstance(ts, str) else format_timestamp(ts),
                    'duration': ai_asset.get('duration', 3.0),
                    'asset': ai_asset['id'],
                    'asset_path': ai_asset['path'],
                    'audio': 'keep_original',
                    'mode': 'replace',
                    'generated': True,
                    'reason': f"AI-generated B-roll for: {description[:50]}"
                })

    # Process keyword matches
    for match in keyword_matches:
        ts = match.get('timestamp') or match.get('start_formatted')
        if not ts:
            continue

        keyword = match.get('keyword', '')
        asset = find_matching_asset([keyword], manifest)

        # Avoid duplicate timestamps
        existing_ts = [e['at'] for e in edits]
        if ts in existing_ts:
            continue

        # Get context from the transcript for better AI generation
        context = match.get('context', '')

        if asset:
            edits.append({
                'type': 'insert_broll',
                'at': ts,
                'duration': min(asset.get('duration', 3.0), 3.0),
                'asset': asset['id'],
                'asset_path': asset['path'],
                'audio': 'keep_original',
                'mode': 'replace',
                'reason': f"B-roll for keyword '{keyword}': {context[:80]}" if context else f"B-roll for keyword: {keyword}",
                'context': context  # Full context for AI generation
            })
        elif generate_images:
            # Generate AI B-roll for keyword match
            context = match.get('context', keyword)
            segment_id = f"keyword_{len(edits)}"
            ai_asset = generate_ai_broll(context, output_dir, segment_id)
            if ai_asset:
                edits.append({
                    'type': 'insert_broll',
                    'at': ts,
                    'duration': ai_asset.get('duration', 3.0),
                    'asset': ai_asset['id'],
                    'asset_path': ai_asset['path'],
                    'audio': 'keep_original',
                    'mode': 'replace',
                    'generated': True,
                    'reason': f"AI-generated B-roll for keyword: {keyword}"
                })

    return edits


def generate_cut_edits(analysis: dict) -> list:
    """Generate cut edits from analysis."""
    edits = []

    # From Gemini analysis
    suggested_cuts = analysis.get('suggested_cuts', [])
    for cut in suggested_cuts:
        if 'start' in cut and 'end' in cut:
            edits.append({
                'type': 'cut',
                'start': cut['start'],
                'end': cut['end'],
                'reason': cut.get('reason', 'Suggested cut')
            })

    return edits


def generate_overlay_edits(analysis: dict, instruction: str) -> list:
    """Generate overlay edits for key moments."""
    edits = []

    # Add lower-thirds for topic introductions
    topics = analysis.get('topics', [])

    for topic in topics:
        if isinstance(topic, dict) and 'timestamps' in topic:
            ts = topic['timestamps'][0] if topic['timestamps'] else None
            if ts:
                edits.append({
                    'type': 'overlay',
                    'start': ts,
                    'end': format_timestamp(parse_timestamp(ts) + 5),
                    'layer': 'lower_third',
                    'text': topic.get('topic', 'Key Point'),
                    'template': 'subtle_bar',
                    'reason': f"Topic introduction: {topic.get('topic')}"
                })

    return edits


def generate_edl(
    source_video: str,
    analysis: dict,
    instruction: str,
    output_path: Optional[str] = None,
    include_broll: bool = True,
    include_cuts: bool = True,
    include_overlays: bool = False,
    generate_images: bool = False,
    broll_output_dir: str = '/tmp/broll'
) -> dict:
    """Generate complete EDL from analysis.

    Args:
        generate_images: If True, generate AI images for B-roll when no asset matches
        broll_output_dir: Directory to store generated B-roll images/videos
    """

    manifest = load_asset_manifest()

    edits = []

    if include_broll:
        edits.extend(generate_broll_edits(
            analysis, instruction, manifest,
            generate_images=generate_images,
            output_dir=broll_output_dir
        ))

    if include_cuts:
        edits.extend(generate_cut_edits(analysis))

    if include_overlays:
        edits.extend(generate_overlay_edits(analysis, instruction))

    # Sort edits by timestamp
    def get_edit_time(edit):
        ts = edit.get('at') or edit.get('start') or '00:00:00'
        return parse_timestamp(ts)

    edits.sort(key=get_edit_time)

    # Build EDL
    duration = analysis.get('duration_seconds', 0)

    edl = {
        'version': '1.0',
        'source_video': source_video,
        'duration_seconds': duration,
        'instruction': instruction,
        'edits': edits,
        'output': {
            'path': output_path or source_video.replace('.mp4', '_edited.mp4'),
            'format': 'mp4',
            'resolution': 'source'
        },
        'metadata': {
            'edit_count': len(edits),
            'broll_count': len([e for e in edits if e['type'] == 'insert_broll']),
            'broll_generated': len([e for e in edits if e['type'] == 'insert_broll' and e.get('generated')]),
            'cut_count': len([e for e in edits if e['type'] == 'cut']),
            'overlay_count': len([e for e in edits if e['type'] == 'overlay'])
        }
    }

    return edl


def main():
    parser = argparse.ArgumentParser(
        description='Generate EDL from video analysis'
    )
    parser.add_argument('--analysis', '-a', help='Analysis JSON file from parse_transcript or analyze_video_gemini')
    parser.add_argument('--segments', '-s', help='Segments JSON file from parse_transcript')
    parser.add_argument('--video', '-v', help='Source video path')
    parser.add_argument('--instruction', '-i', default='Add relevant B-roll',
                        help='Edit instruction')
    parser.add_argument('--output', '-o', help='Output EDL JSON file')
    parser.add_argument('--no-broll', action='store_true', help='Skip B-roll edits')
    parser.add_argument('--no-cuts', action='store_true', help='Skip cut edits')
    parser.add_argument('--overlays', action='store_true', help='Include overlay edits')
    parser.add_argument('--generate-images', '-g', action='store_true',
                        help='Generate AI images for B-roll when no asset matches (uses Nano Banana)')
    parser.add_argument('--broll-dir', default='/tmp/broll',
                        help='Directory for generated B-roll files')

    args = parser.parse_args()

    # Load analysis
    if args.analysis:
        analysis = json.loads(Path(args.analysis).read_text())
    elif args.segments:
        analysis = json.loads(Path(args.segments).read_text())
    else:
        print("Error: Provide --analysis or --segments file", file=sys.stderr)
        sys.exit(1)

    # Determine source video
    source_video = args.video or analysis.get('source_video', 'video.mp4')

    # Generate EDL
    edl = generate_edl(
        source_video=source_video,
        analysis=analysis,
        instruction=args.instruction,
        output_path=args.output.replace('.json', '.mp4') if args.output else None,
        include_broll=not args.no_broll,
        include_cuts=not args.no_cuts,
        include_overlays=args.overlays,
        generate_images=args.generate_images,
        broll_output_dir=args.broll_dir
    )

    # Output
    edl_json = json.dumps(edl, indent=2)

    if args.output:
        Path(args.output).write_text(edl_json)
        print(f"EDL written to: {args.output}")
        print(f"  Total edits: {edl['metadata']['edit_count']}")
        print(f"  B-roll: {edl['metadata']['broll_count']} ({edl['metadata']['broll_generated']} AI-generated)")
        print(f"  Cuts: {edl['metadata']['cut_count']}")
        print(f"  Overlays: {edl['metadata']['overlay_count']}")
    else:
        print(edl_json)


if __name__ == '__main__':
    main()
