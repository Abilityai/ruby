#!/usr/bin/env python3
"""
Generate AI background music using kie.ai Suno API.

This script analyzes video context/transcript and generates appropriate
background music using the Suno AI music generation service.

Usage:
    python generate_music.py "video context or transcript" -o /tmp/music.mp3
    python generate_music.py "context" --style "Ambient, Electronic" --duration 180

Environment:
    KIE_API_KEY: Your kie.ai API key (required)
"""

import argparse
import json
import os
import sys
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any


# API Configuration
API_BASE_URL = "https://api.kie.ai/api/v1"
DEFAULT_MODEL = "V5"  # Latest model with superior musicality
DEFAULT_POLL_INTERVAL = 15  # seconds
MAX_WAIT_TIME = 900  # 15 minutes max


def get_api_key() -> str:
    """Get API key from environment."""
    api_key = os.environ.get('KIE_API_KEY')
    if not api_key:
        # Try loading from .env file (project root)
        # Path: scripts -> edit-video -> skills -> .claude -> project_root
        env_path = Path(__file__).parent.parent.parent.parent.parent / '.env'
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.startswith('KIE_API_KEY='):
                        api_key = line.split('=', 1)[1].strip().strip('"\'')
                        break

    if not api_key:
        raise ValueError("KIE_API_KEY environment variable not set. Get your key at https://kie.ai/api-key")

    return api_key


def analyze_content_for_music(transcript: str, video_duration: float = 180.0) -> Dict[str, Any]:
    """Analyze transcript/context to determine appropriate music parameters.

    Args:
        transcript: Video transcript or context description
        video_duration: Video duration in seconds

    Returns:
        Dict with music generation parameters (mood, style, tempo, energy)
    """
    text_lower = transcript.lower()

    # Detect mood/tone
    mood = "professional"
    if any(word in text_lower for word in ['exciting', 'amazing', 'breakthrough', 'revolutionary']):
        mood = "inspiring"
    elif any(word in text_lower for word in ['problem', 'challenge', 'difficult', 'issue']):
        mood = "thoughtful"
    elif any(word in text_lower for word in ['future', 'vision', 'dream', 'possibility']):
        mood = "hopeful"
    elif any(word in text_lower for word in ['learn', 'tutorial', 'how to', 'step by step']):
        mood = "educational"

    # Detect content type
    is_tech = any(word in text_lower for word in ['ai', 'software', 'code', 'technology', 'system', 'agent', 'api'])
    is_business = any(word in text_lower for word in ['business', 'enterprise', 'company', 'startup', 'founder'])
    is_educational = any(word in text_lower for word in ['learn', 'explain', 'understand', 'concept', 'tutorial'])

    # Determine style based on content
    if is_tech:
        style_base = "Electronic, Ambient, Modern"
    elif is_business:
        style_base = "Corporate, Cinematic, Professional"
    elif is_educational:
        style_base = "Ambient, Soft, Minimal"
    else:
        style_base = "Cinematic, Documentary, Atmospheric"

    # Tempo based on video duration and mood
    if video_duration < 60:
        tempo = "medium-fast"
    elif video_duration < 180:
        tempo = "medium"
    else:
        tempo = "slow-medium"

    # Energy level
    energy = "moderate"
    if mood == "inspiring":
        energy = "building"
    elif mood == "thoughtful":
        energy = "subtle"
    elif mood == "educational":
        energy = "steady"

    return {
        "mood": mood,
        "style": style_base,
        "tempo": tempo,
        "energy": energy,
        "is_tech": is_tech,
        "is_business": is_business,
        "is_educational": is_educational
    }


def generate_music_prompt(
    transcript: str,
    video_duration: float,
    style_override: Optional[str] = None,
    mood_override: Optional[str] = None
) -> Dict[str, str]:
    """Generate a music prompt based on video content analysis.

    Args:
        transcript: Video transcript or context
        video_duration: Video duration in seconds
        style_override: Optional style override from user
        mood_override: Optional mood override from user

    Returns:
        Dict with 'prompt', 'style', 'title' for Suno API
    """
    analysis = analyze_content_for_music(transcript, video_duration)

    style = style_override or analysis['style']
    mood = mood_override or analysis['mood']

    # Build descriptive prompt
    prompt_parts = [
        f"Background music for a {mood} video about technology and AI.",
        f"Style: {style}.",
        f"Tempo: {analysis['tempo']}.",
        f"Energy: {analysis['energy']}, suitable for narration.",
        "No vocals, purely instrumental.",
        "Clean and professional sound that doesn't distract from speech.",
        "Subtle progression with gentle dynamics.",
    ]

    if analysis['is_tech']:
        prompt_parts.append("Modern electronic elements with soft synth pads.")
    if analysis['is_business']:
        prompt_parts.append("Corporate feel with confident undertones.")
    if analysis['is_educational']:
        prompt_parts.append("Calm and focused, supporting learning and attention.")

    prompt = " ".join(prompt_parts)

    # Style for custom mode (more concise)
    style_desc = f"{style}, Instrumental, Background Music, {mood.capitalize()}"

    # Title
    title = f"Background Music - {mood.capitalize()}"

    return {
        "prompt": prompt,
        "style": style_desc,
        "title": title,
        "analysis": analysis
    }


def call_suno_api(
    prompt: str,
    style: str,
    title: str,
    model: str = DEFAULT_MODEL,
    instrumental: bool = True,
    negative_tags: Optional[str] = None,
    api_key: Optional[str] = None
) -> str:
    """Call kie.ai Suno API to generate music.

    Args:
        prompt: Music description
        style: Music style (custom mode)
        title: Track title
        model: Suno model (V3_5, V4, V4_5, V4_5PLUS, V4_5ALL, V5)
        instrumental: True for no vocals
        negative_tags: Things to avoid
        api_key: API key (uses env if not provided)

    Returns:
        Task ID for polling

    Raises:
        Exception on API error
    """
    if not api_key:
        api_key = get_api_key()

    url = f"{API_BASE_URL}/generate"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "prompt": prompt,
        "customMode": True,  # Use custom mode for better control
        "instrumental": instrumental,
        "model": model,
        "style": style,
        "title": title,
        "callBackUrl": "https://example.com/callback"  # Required by API, not used (we poll instead)
    }

    if negative_tags:
        payload["negativeTags"] = negative_tags

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    result = response.json()

    if response.status_code == 400:
        raise Exception(f"Content policy violation: {result.get('msg', 'Unknown error')}")
    elif response.status_code == 402:
        raise Exception("Insufficient credits. Please add credits at https://kie.ai")
    elif response.status_code == 429:
        raise Exception("Rate limit exceeded. Please wait and try again.")
    elif response.status_code != 200 or result.get('code') != 200:
        raise Exception(f"API error: {result.get('msg', 'Unknown error')}")

    return result['data']['taskId']


def poll_task_status(task_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Poll task status until completion or failure.

    Args:
        task_id: Task ID from generation call
        api_key: API key

    Returns:
        Task result with audio URLs

    Raises:
        Exception on failure or timeout
    """
    if not api_key:
        api_key = get_api_key()

    url = f"{API_BASE_URL}/generate/record-info"
    headers = {"Authorization": f"Bearer {api_key}"}

    start_time = time.time()
    consecutive_errors = 0
    max_consecutive_errors = 5
    last_status = None

    while time.time() - start_time < MAX_WAIT_TIME:
        try:
            response = requests.get(url, params={"taskId": task_id}, headers=headers, timeout=30)
            result = response.json()

            # Handle non-200 responses with retries
            if response.status_code != 200 or result.get('code') != 200:
                consecutive_errors += 1
                error_msg = result.get('msg', f'HTTP {response.status_code}')
                print(f"  API error (attempt {consecutive_errors}/{max_consecutive_errors}): {error_msg}")
                if consecutive_errors >= max_consecutive_errors:
                    raise Exception(f"Status check failed after {max_consecutive_errors} attempts: {error_msg}")
                time.sleep(DEFAULT_POLL_INTERVAL)
                continue

            # Reset error counter on successful response
            consecutive_errors = 0

            task_data = result['data']
            status = task_data['status']

            # Log status changes
            if status != last_status:
                elapsed = int(time.time() - start_time)
                print(f"  Status: {status} ({elapsed}s elapsed)")
                last_status = status

            if status == 'SUCCESS':
                print("  Music generation complete!")
                return task_data['response']
            elif status == 'FIRST_SUCCESS':
                # First track ready - but audio URL might not be ready yet
                suno_data = task_data.get('response', {}).get('sunoData', [])
                if suno_data and suno_data[0].get('audioUrl'):
                    print("  First track generated with audio!")
                    return task_data['response']
                else:
                    # Audio URL not ready yet, keep polling
                    print("  First track processing, waiting for audio URL...")
            elif status in ['PENDING', 'TEXT_SUCCESS']:
                # PENDING = task submitted
                # TEXT_SUCCESS = lyrics/text generated, audio still processing
                pass  # Continue polling
            elif status in ['CREATE_TASK_FAILED', 'GENERATE_AUDIO_FAILED']:
                error_msg = task_data.get('errorMessage', 'Generation failed')
                raise Exception(f"Music generation failed: {error_msg}")
            elif status == 'SENSITIVE_WORD_ERROR':
                raise Exception("Content filtered due to policy violation")
            elif status == 'CALLBACK_EXCEPTION':
                # Callback failed but generation might be OK - check for data
                suno_data = task_data.get('response', {}).get('sunoData', [])
                if suno_data and suno_data[0].get('audioUrl'):
                    print("  Callback failed but audio available!")
                    return task_data['response']
                # Don't fail immediately - API might still be processing
                print(f"  Callback exception, continuing to poll...")
            else:
                # Unknown status - log it but keep polling
                elapsed = int(time.time() - start_time)
                print(f"  Unknown status '{status}' ({elapsed}s elapsed), continuing...")

        except requests.exceptions.RequestException as e:
            # Network errors - retry with backoff
            consecutive_errors += 1
            print(f"  Network error (attempt {consecutive_errors}/{max_consecutive_errors}): {e}")
            if consecutive_errors >= max_consecutive_errors:
                raise Exception(f"Network error after {max_consecutive_errors} attempts: {e}")
            time.sleep(DEFAULT_POLL_INTERVAL * 2)  # Longer wait on network errors
            continue
        except json.JSONDecodeError as e:
            # Malformed response - retry
            consecutive_errors += 1
            print(f"  Invalid JSON response (attempt {consecutive_errors}/{max_consecutive_errors})")
            if consecutive_errors >= max_consecutive_errors:
                raise Exception(f"Invalid JSON after {max_consecutive_errors} attempts")
            time.sleep(DEFAULT_POLL_INTERVAL)
            continue

        time.sleep(DEFAULT_POLL_INTERVAL)

    raise Exception(f"Music generation timed out after {MAX_WAIT_TIME}s")


def download_audio(audio_url: str, output_path: str) -> str:
    """Download audio file from URL.

    Args:
        audio_url: URL to audio file
        output_path: Local path to save file

    Returns:
        Path to downloaded file
    """
    print(f"  Downloading audio to: {output_path}")

    response = requests.get(audio_url, stream=True, timeout=60)
    response.raise_for_status()

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    file_size = os.path.getsize(output_path)
    print(f"  Downloaded: {file_size / 1024 / 1024:.1f} MB")

    return output_path


def generate_background_music(
    transcript: str,
    output_path: str,
    video_duration: float = 180.0,
    style: Optional[str] = None,
    mood: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Main function to generate background music for a video.

    Args:
        transcript: Video transcript or context
        output_path: Where to save the generated music
        video_duration: Video duration in seconds
        style: Optional style override
        mood: Optional mood override
        model: Suno model to use
        api_key: API key (uses env if not provided)

    Returns:
        Dict with success status, path, and metadata
    """
    print(f"\n{'='*50}")
    print("Generating AI Background Music")
    print(f"{'='*50}")

    # Generate prompt
    print("\nAnalyzing content for music generation...")
    prompt_data = generate_music_prompt(transcript, video_duration, style, mood)

    print(f"  Mood: {prompt_data['analysis']['mood']}")
    print(f"  Style: {prompt_data['style']}")
    print(f"  Model: {model}")

    # Call API
    print("\nSubmitting to Suno API...")
    try:
        task_id = call_suno_api(
            prompt=prompt_data['prompt'],
            style=prompt_data['style'],
            title=prompt_data['title'],
            model=model,
            instrumental=True,
            negative_tags="vocals, singing, lyrics, voice",
            api_key=api_key
        )
        print(f"  Task ID: {task_id}")
    except Exception as e:
        return {"success": False, "error": str(e)}

    # Poll for completion
    print("\nWaiting for music generation...")
    try:
        result = poll_task_status(task_id, api_key)
    except Exception as e:
        return {"success": False, "error": str(e), "task_id": task_id}

    # Download first track
    if not result.get('sunoData') or len(result['sunoData']) == 0:
        return {"success": False, "error": "No audio tracks generated", "task_id": task_id}

    track = result['sunoData'][0]
    audio_url = track.get('audioUrl')

    if not audio_url:
        return {"success": False, "error": "No audio URL in response", "task_id": task_id}

    print(f"\nGenerated track: {track.get('title', 'Untitled')}")
    print(f"  Duration: {track.get('duration', 'Unknown')}s")
    print(f"  Tags: {track.get('tags', 'None')}")

    # Download
    try:
        download_audio(audio_url, output_path)
    except Exception as e:
        return {
            "success": False,
            "error": f"Download failed: {e}",
            "audio_url": audio_url,
            "task_id": task_id
        }

    print(f"\n{'='*50}")
    print(f"Success! Music saved to: {output_path}")
    print(f"{'='*50}")

    return {
        "success": True,
        "music_path": output_path,
        "audio_url": audio_url,
        "task_id": task_id,
        "duration": track.get('duration'),
        "title": track.get('title'),
        "tags": track.get('tags'),
        "prompt": prompt_data['prompt'],
        "style": prompt_data['style'],
        "analysis": prompt_data['analysis']
    }


def main():
    parser = argparse.ArgumentParser(
        description='Generate AI background music using kie.ai Suno API'
    )
    parser.add_argument('context', help='Video transcript or context description')
    parser.add_argument('-o', '--output', default='/tmp/background_music.mp3',
                       help='Output path for generated music')
    parser.add_argument('-d', '--duration', type=float, default=180.0,
                       help='Video duration in seconds (for music matching)')
    parser.add_argument('--style', help='Music style override (e.g., "Ambient, Electronic")')
    parser.add_argument('--mood', help='Mood override (e.g., "inspiring", "thoughtful")')
    parser.add_argument('--model', default=DEFAULT_MODEL,
                       choices=['V3_5', 'V4', 'V4_5', 'V4_5PLUS', 'V4_5ALL', 'V5'],
                       help=f'Suno model (default: {DEFAULT_MODEL})')
    parser.add_argument('--json', action='store_true',
                       help='Output result as JSON (progress goes to stderr)')

    args = parser.parse_args()

    # When --json is used, redirect stdout to stderr during generation
    # so only the final JSON goes to stdout
    original_stdout = sys.stdout
    if args.json:
        sys.stdout = sys.stderr

    try:
        result = generate_background_music(
            transcript=args.context,
            output_path=args.output,
            video_duration=args.duration,
            style=args.style,
            mood=args.mood,
            model=args.model
        )

        # Restore stdout for JSON output
        if args.json:
            sys.stdout = original_stdout
            print(json.dumps(result, indent=2))

        sys.exit(0 if result['success'] else 1)

    except Exception as e:
        # Restore stdout before error handling
        if args.json:
            sys.stdout = original_stdout
        error_result = {"success": False, "error": str(e)}
        if args.json:
            print(json.dumps(error_result))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
