#!/usr/bin/env python3
"""
Chain videos using Frame-to-Video technique with Veo 3.1

This script creates longer videos by:
1. Generating initial video
2. Extracting last frame
3. Using that frame as first_frame for next video
4. Repeating for seamless continuation

This approach:
- Doesn't require GCS bucket
- Gives more control over transitions
- Allows reference images at each step
- Works with any video (not just Veo-generated)

Usage:
  # Generate initial video
  python chain_video.py --generate "Initial prompt..." --output clip_01.mp4 --extract-last clip_01_last.png

  # Chain next video using last frame
  python chain_video.py --first-frame clip_01_last.png --prompt "Continue..." --output clip_02.mp4 --extract-last clip_02_last.png

  # Or extract from existing video
  python chain_video.py --extract-from video.mp4 --extract-last last_frame.png
"""

import sys
import os
import time
import subprocess
import argparse
from pathlib import Path
from typing import Optional

# Service account configuration
SCRIPT_DIR = Path(__file__).parent
SERVICE_ACCOUNT_PATH = SCRIPT_DIR / "trinity-vertex-ai-account.json"
PROJECT_ID = "mcp-server-project-455215"
LOCATION = "us-central1"

# Set credentials environment variable
if SERVICE_ACCOUNT_PATH.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(SERVICE_ACCOUNT_PATH)


def extract_last_frame(video_path: str, output_path: str) -> bool:
    """Extract the last frame from a video using ffmpeg."""
    try:
        # First, get the duration
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True
        )
        duration = float(result.stdout.strip())

        # Extract last frame (0.1s before end for cleaner frame)
        seek_time = max(0, duration - 0.1)

        subprocess.run([
            "ffmpeg", "-y", "-ss", str(seek_time), "-i", video_path,
            "-vframes", "1", "-q:v", "2", output_path
        ], check=True, capture_output=True)

        print(f"Extracted last frame to: {output_path}")
        return True
    except Exception as e:
        print(f"Error extracting frame: {e}")
        return False


def generate_video_with_first_frame(
    client,
    prompt: str,
    output_path: str,
    first_frame_path: str = None,
    last_frame_path: str = None,
    reference_images: Optional[list[str]] = None,
    model: str = "veo-3.1-generate-preview",
    aspect_ratio: str = "16:9"
) -> bool:
    """Generate video, optionally with first/last frame conditioning."""
    from google.genai import types

    print(f"Generating video with {model}...")
    print(f"Prompt: {prompt[:150]}...")

    # Build config
    config = types.GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
        number_of_videos=1,
    )

    # Prepare first frame image (passed as 'image' param to generate_videos)
    first_frame_image = None
    if first_frame_path and os.path.exists(first_frame_path):
        print(f"Using first frame: {first_frame_path}")
        with open(first_frame_path, "rb") as f:
            image_data = f.read()
        mime_type = "image/png" if first_frame_path.lower().endswith(".png") else "image/jpeg"
        first_frame_image = types.Image(image_bytes=image_data, mime_type=mime_type)

    # Add last frame if provided (for interpolation) - this goes in config
    if last_frame_path and os.path.exists(last_frame_path):
        print(f"Using last frame: {last_frame_path}")
        with open(last_frame_path, "rb") as f:
            image_data = f.read()
        mime_type = "image/png" if last_frame_path.lower().endswith(".png") else "image/jpeg"
        config.last_frame = types.Image(image_bytes=image_data, mime_type=mime_type)

    # Note: Can't use reference_images AND first/last frame together in Veo 3.1
    # If using first_frame, skip reference_images
    if not first_frame_path and not last_frame_path and reference_images:
        print(f"Reference images: {len(reference_images)}")
        ref_images_config = []
        for ref_path in reference_images:
            if not os.path.exists(ref_path):
                print(f"Warning: Reference image not found: {ref_path}")
                continue
            with open(ref_path, "rb") as f:
                image_data = f.read()
            mime_type = "image/png" if ref_path.lower().endswith(".png") else "image/jpeg"
            print(f"  Adding reference: {os.path.basename(ref_path)}")
            ref_images_config.append(
                types.VideoGenerationReferenceImage(
                    image=types.Image(image_bytes=image_data, mime_type=mime_type),
                    reference_type=types.VideoGenerationReferenceType.ASSET
                )
            )
        if ref_images_config:
            config.reference_images = ref_images_config

    # Generate - first frame passed as 'image' parameter
    print("Submitting generation request...")
    operation = client.models.generate_videos(
        model=model,
        prompt=prompt,
        image=first_frame_image,  # First frame goes here
        config=config
    )

    print(f"Operation started: {operation.name}")
    print("Waiting for video generation...")

    # Poll for completion
    start_time = time.time()
    while True:
        operation = client.operations.get(operation)
        if operation.done:
            print("Generation complete!")
            break
        elapsed = int(time.time() - start_time)
        print(f"  Still generating... ({elapsed}s elapsed)")
        time.sleep(15)
        if elapsed > 600:
            print("Timeout waiting for video generation")
            return False

    if operation.error:
        print(f"Generation failed: {operation.error}")
        return False

    # Get result
    result = operation.response if hasattr(operation, 'response') else operation.result
    if not result or not hasattr(result, 'generated_videos') or not result.generated_videos:
        print(f"No videos in response")
        return False

    # Save video
    video_obj = result.generated_videos[0]
    return save_video_to_file(video_obj, output_path)


def save_video_to_file(video_obj, output_path: str) -> bool:
    """Save video object to file."""
    if hasattr(video_obj, 'video'):
        video_data = video_obj.video
        if hasattr(video_data, 'video_bytes') and video_data.video_bytes:
            with open(output_path, 'wb') as f:
                f.write(video_data.video_bytes)
            print(f"Saved to: {output_path}")
            return True
        elif hasattr(video_data, 'uri') and video_data.uri:
            import urllib.request
            import google.auth
            import google.auth.transport.requests

            print(f"Downloading from: {video_data.uri}")
            credentials, project = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)

            req = urllib.request.Request(video_data.uri)
            req.add_header('Authorization', f'Bearer {credentials.token}')

            with urllib.request.urlopen(req) as response:
                with open(output_path, 'wb') as f:
                    f.write(response.read())
            print(f"Saved to: {output_path}")
            return True

    print(f"Could not extract video data")
    return False


def main():
    parser = argparse.ArgumentParser(description="Chain videos using frame-to-video technique")
    parser.add_argument("--generate", type=str, help="Generate initial video with this prompt")
    parser.add_argument("--first-frame", type=str, help="First frame image for continuation")
    parser.add_argument("--last-frame", type=str, help="Last frame image (for interpolation)")
    parser.add_argument("--prompt", type=str, help="Prompt for continuation video")
    parser.add_argument("--output", type=str, help="Output video path")
    parser.add_argument("--extract-last", type=str, help="Extract last frame to this path")
    parser.add_argument("--extract-from", type=str, help="Extract last frame from this video (standalone)")
    parser.add_argument("--model", type=str, default="veo-3.1-generate-preview")
    parser.add_argument("--ref", nargs="+", help="Reference images (only for initial generation, not with first-frame)")
    parser.add_argument("--aspect", type=str, default="16:9", help="Aspect ratio (16:9, 9:16)")

    args = parser.parse_args()

    # Standalone frame extraction
    if args.extract_from:
        if not args.extract_last:
            print("Error: --extract-last required with --extract-from")
            sys.exit(1)
        Path(args.extract_last).parent.mkdir(parents=True, exist_ok=True)
        if extract_last_frame(args.extract_from, args.extract_last):
            print("Done!")
            sys.exit(0)
        sys.exit(1)

    # Need either --generate or --first-frame with --prompt
    if not args.generate and not (args.first_frame and args.prompt):
        print("Error: Must specify either --generate or (--first-frame and --prompt)")
        sys.exit(1)

    if not args.output:
        print("Error: --output required for video generation")
        sys.exit(1)

    if not SERVICE_ACCOUNT_PATH.exists():
        print(f"Error: Service account file not found: {SERVICE_ACCOUNT_PATH}")
        sys.exit(1)

    try:
        from google import genai
    except ImportError:
        print("Error: google-genai not installed")
        print("Run: pip install google-genai")
        sys.exit(1)

    # Initialize client
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=LOCATION
    )

    # Ensure output directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    # Determine prompt
    prompt = args.generate if args.generate else args.prompt

    # Generate video
    success = generate_video_with_first_frame(
        client,
        prompt,
        args.output,
        first_frame_path=args.first_frame,
        last_frame_path=args.last_frame,
        reference_images=args.ref if not args.first_frame else None,  # Can't use both
        model=args.model,
        aspect_ratio=args.aspect
    )

    if not success:
        sys.exit(1)

    # Extract last frame if requested
    if args.extract_last:
        Path(args.extract_last).parent.mkdir(parents=True, exist_ok=True)
        extract_last_frame(args.output, args.extract_last)

    print("\nDone!")
    print(f"Video: {args.output}")
    if args.extract_last:
        print(f"Last frame: {args.extract_last}")
        print("Use --first-frame with next generation for continuation")


if __name__ == "__main__":
    main()
