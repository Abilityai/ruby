#!/usr/bin/env python3
"""
Generate voiceover audio using ElevenLabs.

Usage:
    # Single text
    python generate_voiceover.py "Text to speak" output.mp3

    # From JSON script file (for multi-scene videos)
    python generate_voiceover.py --script script.json output.mp3

    # List available voices
    python generate_voiceover.py --list-voices

Script JSON format:
{
    "scenes": [
        {"id": "scene_01", "text": "Narration text here", "pause_after": 0.5},
        {"id": "scene_02", "text": "Next scene text", "pause_after": 0.5}
    ]
}
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')

# the creator's cloned voice
DEFAULT_VOICE_ID = "${ELEVENLABS_VOICE_ID}"
DEFAULT_MODEL = "eleven_multilingual_v2"


def get_client():
    """Initialize ElevenLabs client."""
    from elevenlabs import ElevenLabs

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY not found in environment")
        sys.exit(1)

    return ElevenLabs(api_key=api_key)


def list_voices():
    """List available voices."""
    client = get_client()
    response = client.voices.get_all()

    print("\nAvailable Voices:")
    print("-" * 60)
    for voice in response.voices:
        category = voice.category or "unknown"
        print(f"  {voice.name}: {voice.voice_id} ({category})")


def generate_tts(text: str, output_path: str, voice_id: str = None, model: str = None):
    """Generate TTS audio using ElevenLabs.

    Args:
        text: Text to convert to speech
        output_path: Output audio file path
        voice_id: ElevenLabs voice ID (default: from env)
        model: Model ID (default: eleven_multilingual_v2)
    """
    client = get_client()

    voice_id = voice_id or DEFAULT_VOICE_ID
    model = model or DEFAULT_MODEL

    print(f"Generating voiceover...")
    print(f"  Voice: {voice_id}")
    print(f"  Model: {model}")
    print(f"  Text: {text[:80]}{'...' if len(text) > 80 else ''}")

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=model
    )

    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    print(f"  Output: {output_path}")
    return output_path


def generate_from_script(script_path: str, output_path: str, voice_id: str = None):
    """Generate voiceover from a JSON script file.

    Concatenates all scene narrations with optional pauses between.

    Args:
        script_path: Path to JSON script file
        output_path: Output audio file path
        voice_id: ElevenLabs voice ID (default: from env)
    """
    import subprocess
    import tempfile

    with open(script_path) as f:
        script = json.load(f)

    scenes = script.get('scenes', [])
    if not scenes:
        print("Error: No scenes found in script")
        sys.exit(1)

    print(f"Generating voiceover for {len(scenes)} scenes...")

    # Generate audio for each scene
    temp_files = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, scene in enumerate(scenes):
            scene_id = scene.get('id', f'scene_{i:02d}')
            text = scene.get('text', '')

            if not text:
                print(f"  Skipping {scene_id}: no text")
                continue

            temp_path = os.path.join(tmpdir, f'{scene_id}.mp3')
            print(f"\n  [{i+1}/{len(scenes)}] {scene_id}")
            generate_tts(text, temp_path, voice_id)
            temp_files.append(temp_path)

            # Add silence if pause_after specified
            pause = scene.get('pause_after', 0.3)
            if pause > 0:
                silence_path = os.path.join(tmpdir, f'{scene_id}_silence.mp3')
                subprocess.run([
                    'ffmpeg', '-y', '-f', 'lavfi',
                    '-i', f'anullsrc=r=44100:cl=stereo',
                    '-t', str(pause),
                    '-c:a', 'libmp3lame', '-q:a', '2',
                    silence_path
                ], capture_output=True)
                temp_files.append(silence_path)

        # Concatenate all files
        if temp_files:
            concat_list = os.path.join(tmpdir, 'concat.txt')
            with open(concat_list, 'w') as f:
                for temp_file in temp_files:
                    f.write(f"file '{temp_file}'\n")

            print(f"\nConcatenating {len(temp_files)} audio segments...")
            result = subprocess.run([
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', concat_list,
                '-c:a', 'libmp3lame', '-q:a', '2',
                output_path
            ], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"Error concatenating: {result.stderr}")
                sys.exit(1)

    print(f"\nVoiceover generated: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate voiceover using ElevenLabs")
    parser.add_argument("text", nargs="?", help="Text to convert to speech")
    parser.add_argument("output", nargs="?", help="Output audio file path")
    parser.add_argument("--script", "-s", help="JSON script file for multi-scene voiceover")
    parser.add_argument("--voice-id", "-v", default=DEFAULT_VOICE_ID,
                        help=f"Voice ID (default: default: {DEFAULT_VOICE_ID})")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL,
                        help=f"Model ID (default: {DEFAULT_MODEL})")
    parser.add_argument("--list-voices", "-l", action="store_true",
                        help="List available voices")

    args = parser.parse_args()

    if args.list_voices:
        list_voices()
        return

    if args.script:
        if not args.output:
            parser.error("Output path required with --script")
        generate_from_script(args.script, args.output, args.voice_id)
    elif args.text and args.output:
        generate_tts(args.text, args.output, args.voice_id, args.model)
    else:
        parser.error("Provide text and output path, or use --script")


if __name__ == "__main__":
    main()
