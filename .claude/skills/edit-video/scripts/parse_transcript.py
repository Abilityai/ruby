#!/usr/bin/env python3
"""
Parse transcript files and extract word-level timestamps.

Supports formats:
- JSON: Output from transcribe_video.py (preferred)
- VTT-style: [00:00:05.123] text
- SRT-style: 00:00:05,123 --> 00:00:10,456
- Simple: [MM:SS] text or [HH:MM:SS] text
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional


def parse_timestamp(ts: str) -> float:
    """Convert timestamp string to seconds."""
    ts = ts.strip().replace(',', '.')

    # Handle HH:MM:SS.mmm or MM:SS.mmm or SS.mmm
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
    """Convert seconds to MM:SS.mmm format."""
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:06.3f}"


def parse_vtt_style(content: str) -> list:
    """Parse VTT-style timestamps: [00:00:05.123] text"""
    segments = []
    pattern = r'\[(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?)\]\s*(.+?)(?=\[|\Z)'

    for match in re.finditer(pattern, content, re.DOTALL):
        ts, text = match.groups()
        start = parse_timestamp(ts)
        text = text.strip()
        if text:
            segments.append({
                'start': start,
                'text': text
            })

    # Calculate end times (next segment's start or +5 seconds)
    for i, seg in enumerate(segments):
        if i + 1 < len(segments):
            seg['end'] = segments[i + 1]['start']
        else:
            seg['end'] = seg['start'] + 5.0

    return segments


def parse_srt_style(content: str) -> list:
    """Parse SRT-style timestamps: 00:00:05,123 --> 00:00:10,456"""
    segments = []
    pattern = r'(\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*\n(.+?)(?=\n\n|\Z)'

    for match in re.finditer(pattern, content, re.DOTALL):
        start_ts, end_ts, text = match.groups()
        segments.append({
            'start': parse_timestamp(start_ts),
            'end': parse_timestamp(end_ts),
            'text': text.strip().replace('\n', ' ')
        })

    return segments


def parse_simple_style(content: str) -> list:
    """Parse simple timestamps: [MM:SS] text"""
    segments = []
    pattern = r'\[(\d{1,2}:\d{2})\]\s*(.+?)(?=\[|\Z)'

    for match in re.finditer(pattern, content, re.DOTALL):
        ts, text = match.groups()
        start = parse_timestamp(ts + ':00')
        text = text.strip()
        if text:
            segments.append({
                'start': start,
                'text': text
            })

    # Calculate end times
    for i, seg in enumerate(segments):
        if i + 1 < len(segments):
            seg['end'] = segments[i + 1]['start']
        else:
            seg['end'] = seg['start'] + 10.0

    return segments


def extract_topics(segments: list, min_word_length: int = 4) -> list:
    """Extract likely topics from transcript text."""
    # Common filler words to ignore
    stopwords = {
        'the', 'and', 'that', 'this', 'with', 'from', 'have', 'been',
        'were', 'they', 'their', 'what', 'when', 'where', 'which',
        'would', 'could', 'should', 'about', 'into', 'just', 'like',
        'know', 'think', 'really', 'very', 'also', 'some', 'more',
        'going', 'being', 'because', 'through', 'before', 'after'
    }

    word_counts = {}
    for seg in segments:
        words = re.findall(r'\b[A-Za-z]+\b', seg['text'])
        for word in words:
            word_lower = word.lower()
            if len(word) >= min_word_length and word_lower not in stopwords:
                word_counts[word_lower] = word_counts.get(word_lower, 0) + 1

    # Return top 20 by frequency
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:20] if count >= 2]


def find_keyword_timestamps(segments: list, keywords: list) -> list:
    """Find timestamps where keywords appear."""
    matches = []
    keywords_lower = [k.lower() for k in keywords]

    for seg in segments:
        text_lower = seg['text'].lower()
        for kw in keywords_lower:
            if kw in text_lower:
                matches.append({
                    'keyword': kw,
                    'timestamp': format_timestamp(seg['start']),
                    'start_seconds': seg['start'],
                    'context': seg['text'][:100]
                })

    return matches


def parse_json_transcript(data: dict) -> dict:
    """Parse JSON transcript from transcribe_video.py output."""
    segments = data.get('segments', [])

    # Ensure all segments have formatted timestamps
    for seg in segments:
        if 'start_formatted' not in seg:
            seg['start_formatted'] = format_timestamp(seg.get('start', 0))
        if 'end_formatted' not in seg:
            seg['end_formatted'] = format_timestamp(seg.get('end', seg.get('start', 0)))

    # Return with all required fields
    return {
        'segments': segments,
        'topics': data.get('topics', extract_topics(segments)),
        'duration_seconds': data.get('duration_seconds', 0),
        'duration_formatted': data.get('duration_formatted', format_timestamp(data.get('duration_seconds', 0))),
        'segment_count': len(segments),
        'text': data.get('text', ''),
        'language': data.get('language', 'en')
    }


def parse_transcript(content: str) -> dict:
    """Auto-detect format and parse transcript."""
    # Try JSON first
    try:
        data = json.loads(content)
        if isinstance(data, dict) and 'segments' in data:
            return parse_json_transcript(data)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try each text format
    if '-->' in content:
        segments = parse_srt_style(content)
    elif re.search(r'\[\d{1,2}:\d{2}:\d{2}', content):
        segments = parse_vtt_style(content)
    elif re.search(r'\[\d{1,2}:\d{2}\]', content):
        segments = parse_simple_style(content)
    else:
        # No timestamps found, return entire content as one segment
        segments = [{
            'start': 0,
            'end': 0,
            'text': content.strip()
        }]

    # Calculate duration
    duration = max(seg.get('end', seg['start']) for seg in segments) if segments else 0

    # Format timestamps for output
    for seg in segments:
        seg['start_formatted'] = format_timestamp(seg['start'])
        seg['end_formatted'] = format_timestamp(seg.get('end', seg['start']))

    return {
        'segments': segments,
        'topics': extract_topics(segments),
        'duration_seconds': duration,
        'duration_formatted': format_timestamp(duration),
        'segment_count': len(segments)
    }


def main():
    parser = argparse.ArgumentParser(
        description='Parse transcript.md and extract timestamps'
    )
    parser.add_argument('transcript', help='Path to transcript file')
    parser.add_argument('-o', '--output', help='Output JSON file')
    parser.add_argument('-k', '--keywords', nargs='+', help='Keywords to find timestamps for')
    parser.add_argument('--format', choices=['json', 'text'], default='json', help='Output format')

    args = parser.parse_args()

    # Read transcript
    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"Error: File not found: {transcript_path}", file=sys.stderr)
        sys.exit(1)

    content = transcript_path.read_text()

    # Parse
    result = parse_transcript(content)

    # Find keyword timestamps if specified
    if args.keywords:
        result['keyword_matches'] = find_keyword_timestamps(result['segments'], args.keywords)

    # Output
    if args.format == 'json':
        output = json.dumps(result, indent=2)
    else:
        output = f"Duration: {result['duration_formatted']}\n"
        output += f"Segments: {result['segment_count']}\n"
        output += f"Topics: {', '.join(result['topics'][:10])}\n\n"
        for seg in result['segments']:
            output += f"[{seg['start_formatted']}] {seg['text'][:80]}...\n"

    if args.output:
        Path(args.output).write_text(output)
        print(f"Output written to: {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
