#!/usr/bin/env python3
"""
Transcribe video/audio using Whisper with word-level timestamps.

Usage:
    python3 transcribe_video.py video.mp4 [options]

Options:
    -o, --output     Output file (default: stdout as JSON)
    -m, --model      Whisper model (tiny, base, small, medium, large)
    --language       Language code (en, es, etc.) - auto-detect if omitted
    --word-level     Include word-level timestamps (slower but more precise)
    --format         Output format: json (default), segments, transcript
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def check_whisper():
    """Verify whisper is installed."""
    result = subprocess.run(['which', 'whisper'], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error: whisper not found. Install with: pip install openai-whisper", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def transcribe(
    input_path: str,
    model: str = 'base',
    language: str = None,
    word_timestamps: bool = True
) -> dict:
    """
    Transcribe video/audio file using Whisper.

    Returns dict with segments, text, and metadata.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Create temp directory for whisper output
    with tempfile.TemporaryDirectory() as tmpdir:
        # Build whisper command
        cmd = [
            'whisper',
            str(input_path),
            '--model', model,
            '--output_dir', tmpdir,
            '--output_format', 'json',
            '--word_timestamps', 'True' if word_timestamps else 'False',
            '--verbose', 'False'
        ]

        if language:
            cmd.extend(['--language', language])

        # Run whisper
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Whisper error: {e.stderr}", file=sys.stderr)
            raise

        # Find and read JSON output
        json_file = Path(tmpdir) / f"{input_path.stem}.json"
        if not json_file.exists():
            # Try alternative naming
            json_files = list(Path(tmpdir).glob('*.json'))
            if json_files:
                json_file = json_files[0]
            else:
                raise FileNotFoundError("Whisper did not produce JSON output")

        with open(json_file) as f:
            whisper_output = json.load(f)

    return whisper_output


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS.mmm"""
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:06.3f}"


def format_timestamp_hhmmss(seconds: float) -> str:
    """Format seconds as HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def convert_to_segments(whisper_output: dict) -> dict:
    """
    Convert Whisper output to our segment format compatible with parse_transcript.py
    """
    segments = []
    all_text = []

    for seg in whisper_output.get('segments', []):
        segment = {
            'start': seg['start'],
            'end': seg['end'],
            'text': seg['text'].strip(),
            'start_formatted': format_timestamp(seg['start']),
            'end_formatted': format_timestamp(seg['end']),
        }

        # Include word-level timestamps if available
        if 'words' in seg:
            segment['words'] = [
                {
                    'word': w['word'].strip(),
                    'start': w['start'],
                    'end': w['end'],
                    'start_formatted': format_timestamp(w['start']),
                    'end_formatted': format_timestamp(w['end'])
                }
                for w in seg['words']
            ]

        segments.append(segment)
        all_text.append(seg['text'].strip())

    # Extract topics (simple: most common nouns/keywords)
    full_text = ' '.join(all_text)
    topics = extract_topics(full_text)

    # Calculate duration
    duration = whisper_output.get('segments', [{}])[-1].get('end', 0) if whisper_output.get('segments') else 0

    return {
        'segments': segments,
        'text': full_text,
        'topics': topics,
        'duration_seconds': duration,
        'duration_formatted': format_timestamp(duration),
        'segment_count': len(segments),
        'language': whisper_output.get('language', 'en')
    }


def extract_topics(text: str, max_topics: int = 10) -> list:
    """Extract likely topics from text (simple keyword extraction)."""
    import re

    # Common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'dare', 'ought', 'used', 'this', 'that', 'these', 'those', 'i', 'you',
        'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'whom',
        'whose', 'where', 'when', 'why', 'how', 'all', 'each', 'every',
        'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
        'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
        'also', 'now', 'here', 'there', 'then', 'once', 'if', 'because',
        'as', 'until', 'while', 'about', 'against', 'between', 'into',
        'through', 'during', 'before', 'after', 'above', 'below', 'up',
        'down', 'out', 'off', 'over', 'under', 'again', 'further', 'then',
        'once', 'really', 'actually', 'basically', 'gonna', 'going', 'like',
        'know', 'think', 'want', 'get', 'got', 'make', 'made', 'let', 'say',
        'said', 'see', 'look', 'come', 'came', 'go', 'went', 'take', 'took',
        'give', 'gave', 'find', 'found', 'tell', 'told', 'ask', 'asked',
        'seem', 'seemed', 'feel', 'felt', 'try', 'tried', 'leave', 'left',
        'call', 'called', 'keep', 'kept', 'put', 'run', 'ran', 'move',
        'live', 'believe', 'hold', 'bring', 'happen', 'write', 'provide',
        'sit', 'stand', 'lose', 'pay', 'meet', 'include', 'continue',
        'set', 'learn', 'change', 'lead', 'understand', 'watch', 'follow',
        'stop', 'create', 'speak', 'read', 'allow', 'add', 'spend', 'grow',
        'open', 'walk', 'win', 'offer', 'remember', 'love', 'consider',
        'appear', 'buy', 'wait', 'serve', 'die', 'send', 'expect', 'build',
        'stay', 'fall', 'cut', 'reach', 'kill', 'remain', 'right', 'well',
        'way', 'thing', 'things', 'something', 'anything', 'everything',
        'nothing', 'someone', 'anyone', 'everyone', 'one', 'two', 'three',
        'first', 'second', 'new', 'old', 'good', 'bad', 'great', 'little',
        'big', 'small', 'long', 'short', 'high', 'low', 'much', 'many',
        'lot', 'kind', 'sort', 'part', 'place', 'case', 'fact', 'point',
        'time', 'year', 'day', 'week', 'month', 'people', 'person', 'man',
        'woman', 'child', 'world', 'life', 'hand', 'work', 'still', 'even',
        'back', 'any', 'around', 'show', 'always', 'never', 'through'
    }

    # Extract words (3+ characters)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

    # Count non-stop words
    word_counts = {}
    for word in words:
        if word not in stop_words:
            word_counts[word] = word_counts.get(word, 0) + 1

    # Sort by frequency and return top topics
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:max_topics] if count >= 2]


def format_as_transcript(result: dict) -> str:
    """Format as human-readable transcript with timestamps."""
    lines = []
    for seg in result['segments']:
        timestamp = format_timestamp_hhmmss(seg['start'])
        lines.append(f"[{timestamp}] {seg['text']}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Transcribe video/audio using Whisper with timestamps'
    )
    parser.add_argument('input', help='Video or audio file to transcribe')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    parser.add_argument('-m', '--model', default='base',
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model size (default: base)')
    parser.add_argument('--language', help='Language code (auto-detect if omitted)')
    parser.add_argument('--word-level', action='store_true', default=True,
                       help='Include word-level timestamps (default: True)')
    parser.add_argument('--no-word-level', dest='word_level', action='store_false',
                       help='Disable word-level timestamps (faster)')
    parser.add_argument('--format', default='json',
                       choices=['json', 'segments', 'transcript'],
                       help='Output format (default: json)')

    args = parser.parse_args()

    # Check whisper is available
    check_whisper()

    # Transcribe
    try:
        whisper_output = transcribe(
            args.input,
            model=args.model,
            language=args.language,
            word_timestamps=args.word_level
        )
    except Exception as e:
        print(f"Error transcribing: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert to our format
    result = convert_to_segments(whisper_output)

    # Format output
    if args.format == 'json':
        output = json.dumps(result, indent=2)
    elif args.format == 'segments':
        output = json.dumps(result['segments'], indent=2)
    elif args.format == 'transcript':
        output = format_as_transcript(result)
    else:
        output = json.dumps(result, indent=2)

    # Write output
    if args.output:
        Path(args.output).write_text(output)
        print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
