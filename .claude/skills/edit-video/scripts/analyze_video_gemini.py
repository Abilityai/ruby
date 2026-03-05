#!/usr/bin/env python3
"""
Analyze video content using Gemini 1.5 Pro for semantic understanding.

Capabilities:
- Scene detection with timestamps
- Find moments matching semantic queries
- Identify natural cut points
- Extract topics discussed
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai package not installed", file=sys.stderr)
    print("Install with: pip install google-generativeai", file=sys.stderr)
    sys.exit(1)


def setup_gemini():
    """Configure Gemini API."""
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        # Try reading from .env file (Ruby agent root)
        # Skill is at .claude/skills/edit-video, so .env is at ../../..
        skill_dir = Path(__file__).parent.parent
        env_path = skill_dir.parent.parent.parent / '.env'
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith('GEMINI_API_KEY=') or line.startswith('GOOGLE_API_KEY='):
                    api_key = line.split('=', 1)[1].strip().strip('"\'')
                    break

    if not api_key:
        print("Error: GEMINI_API_KEY or GOOGLE_API_KEY not found", file=sys.stderr)
        sys.exit(1)

    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-pro')


def upload_video(video_path: str) -> 'genai.File':
    """Upload video to Gemini."""
    print(f"Uploading video: {video_path}")

    video_file = genai.upload_file(path=video_path)

    # Wait for processing
    while video_file.state.name == "PROCESSING":
        print("Processing video...")
        time.sleep(5)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError(f"Video processing failed: {video_file.state.name}")

    print(f"Video ready: {video_file.uri}")
    return video_file


def analyze_video(model, video_file, instruction: str) -> dict:
    """Analyze video with Gemini."""

    prompt = f"""Analyze this video for video editing purposes.

User instruction: {instruction}

Please provide a JSON response with:

1. "scenes" - Array of scene changes with:
   - "start": timestamp (MM:SS format)
   - "end": timestamp (MM:SS format)
   - "description": what's happening in this scene

2. "moments" - Array of specific moments matching the instruction:
   - "at": timestamp (MM:SS format)
   - "description": what's happening
   - "confidence": 0.0-1.0 how well it matches the instruction

3. "cut_points" - Array of natural cut point timestamps (MM:SS format) where transitions would work well

4. "topics" - Array of main topics discussed with timestamps:
   - "topic": the topic name
   - "timestamps": array of MM:SS timestamps where it's discussed

5. "summary" - Brief summary of the video content

Return ONLY valid JSON, no markdown formatting."""

    response = model.generate_content(
        [video_file, prompt],
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=4096
        )
    )

    # Parse JSON from response
    text = response.text.strip()

    # Remove markdown code blocks if present
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
        if text.endswith('```'):
            text = text.rsplit('```', 1)[0]
        elif '```' in text:
            text = text.rsplit('```', 1)[0]

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {
                'raw_response': text,
                'error': 'Could not parse JSON response'
            }

    return result


def analyze_with_transcript(model, transcript_path: str, instruction: str) -> dict:
    """Analyze using transcript only (faster, no video upload)."""

    transcript = Path(transcript_path).read_text()

    prompt = f"""Analyze this video transcript for editing purposes.

Transcript:
{transcript}

User instruction: {instruction}

Please provide a JSON response with:

1. "moments" - Array of specific moments matching the instruction:
   - "at": estimated timestamp based on position in transcript
   - "text": the relevant text
   - "confidence": 0.0-1.0 how well it matches the instruction

2. "topics" - Array of main topics discussed:
   - "topic": the topic name
   - "mentions": array of relevant quotes

3. "suggested_cuts" - Array of sections that could be cut (filler, repetition)
   - "reason": why this could be cut
   - "text": the text to cut

4. "summary" - Brief summary of the content

Return ONLY valid JSON, no markdown formatting."""

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=4096
        )
    )

    text = response.text.strip()

    # Remove markdown code blocks if present
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
        if '```' in text:
            text = text.rsplit('```', 1)[0]

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {
                'raw_response': text,
                'error': 'Could not parse JSON response'
            }

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Analyze video with Gemini for semantic editing'
    )
    parser.add_argument('video', help='Path to video file')
    parser.add_argument('instruction', nargs='?', default='Identify key moments and natural cut points',
                        help='What to look for in the video')
    parser.add_argument('-o', '--output', help='Output JSON file')
    parser.add_argument('-t', '--transcript', help='Use transcript instead of video upload (faster)')
    parser.add_argument('--keep-file', action='store_true', help='Keep uploaded file on Gemini')

    args = parser.parse_args()

    # Validate video exists
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: Video not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    # Setup Gemini
    model = setup_gemini()

    # Analyze
    if args.transcript:
        print("Analyzing transcript (no video upload)...")
        result = analyze_with_transcript(model, args.transcript, args.instruction)
    else:
        # Upload and analyze video
        video_file = upload_video(str(video_path))

        try:
            print(f"Analyzing video with instruction: {args.instruction}")
            result = analyze_video(model, video_file, args.instruction)
        finally:
            # Clean up uploaded file unless --keep-file
            if not args.keep_file:
                try:
                    genai.delete_file(video_file.name)
                    print("Cleaned up uploaded video")
                except Exception as e:
                    print(f"Warning: Could not delete uploaded file: {e}")

    # Add metadata
    result['source_video'] = str(video_path)
    result['instruction'] = args.instruction
    result['analysis_type'] = 'transcript' if args.transcript else 'video'

    # Output
    output_json = json.dumps(result, indent=2)

    if args.output:
        Path(args.output).write_text(output_json)
        print(f"Analysis written to: {args.output}")
    else:
        print(output_json)


if __name__ == '__main__':
    main()
