#!/usr/bin/env python3
"""
Generate videos using Google Veo 3.1 via Vertex AI

Usage:
  python generate_video.py "prompt" output_path.mp4 [OPTIONS]

Options:
  --model MODEL      Model to use (default: veo-3.1-generate-preview)
  --ref IMAGE [...]  Reference images for character consistency (up to 3)
  --aspect RATIO     Aspect ratio: 16:9, 9:16, 1:1 (default: 16:9)

Models available:
  veo-3.1-generate-preview (default) - highest quality
  veo-3.1-fast-generate-preview - faster, lower quality
  veo-3.0-generate-001 - older model
  veo-3.0-fast-generate-001 - older fast model

Examples:
  python generate_video.py "A woman making coffee" video.mp4
  python generate_video.py "A woman walking" video.mp4 --ref face.png body.png
  python generate_video.py "A woman talking" video.mp4 --ref ref.png --aspect 9:16
"""

import sys
import os
import time
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


def generate_video(
    prompt: str,
    output_path: str,
    model: str = "veo-3.1-generate-preview",
    reference_images: Optional[list[str]] = None,
    aspect_ratio: str = "16:9"
) -> bool:
    """Generate a video from a prompt using Veo via Vertex AI.

    Args:
        prompt: Text prompt describing the video
        output_path: Path to save the generated video
        model: Veo model to use
        reference_images: List of paths to reference images for character consistency
        aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1)

    Returns:
        True if successful, False otherwise
    """

    if not SERVICE_ACCOUNT_PATH.exists():
        print(f"Error: Service account file not found: {SERVICE_ACCOUNT_PATH}")
        return False

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Error: google-genai not installed")
        print("Run: pip install google-genai")
        return False

    print(f"Generating video with {model} via Vertex AI...")
    print(f"Project: {PROJECT_ID}, Location: {LOCATION}")
    print(f"Prompt: {prompt[:150]}...")
    print(f"Aspect ratio: {aspect_ratio}")

    # Build reference images list if provided
    ref_images_config = None
    if reference_images:
        print(f"Reference images: {len(reference_images)}")
        ref_images_config = []
        for ref_path in reference_images:
            if not os.path.exists(ref_path):
                print(f"Warning: Reference image not found: {ref_path}")
                continue

            # Read image data
            with open(ref_path, "rb") as f:
                image_data = f.read()

            # Determine mime type
            mime_type = "image/png"
            if ref_path.lower().endswith(".jpg") or ref_path.lower().endswith(".jpeg"):
                mime_type = "image/jpeg"

            print(f"  Adding reference: {os.path.basename(ref_path)}")
            ref_images_config.append(
                types.VideoGenerationReferenceImage(
                    image=types.Image(image_bytes=image_data, mime_type=mime_type),
                    reference_type=types.VideoGenerationReferenceType.ASSET
                )
            )

    try:
        # Initialize client with Vertex AI
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION
        )

        # Build config
        config = types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            number_of_videos=1,
        )

        # Add reference images if provided
        if ref_images_config:
            config.reference_images = ref_images_config

        # Start video generation
        print("Submitting generation request...")
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            config=config
        )

        print(f"Operation started: {operation.name}")
        print("Waiting for video generation (typically 2-5 minutes)...")

        # Poll for completion
        start_time = time.time()
        while True:
            # Refresh operation status
            operation = client.operations.get(operation)

            if operation.done:
                print("Generation complete!")
                break

            elapsed = int(time.time() - start_time)
            print(f"  Still generating... ({elapsed}s elapsed)")
            time.sleep(15)

            if elapsed > 600:  # 10 minute timeout
                print("Timeout waiting for video generation")
                return False

        # Check for errors
        if operation.error:
            print(f"Generation failed: {operation.error}")
            return False

        # Get the result - try different ways to access it
        result = None
        if hasattr(operation, 'response') and operation.response:
            result = operation.response
        elif hasattr(operation, 'result') and operation.result:
            result = operation.result
        if not result or not hasattr(result, 'generated_videos') or not result.generated_videos:
            print(f"No videos in response. Result: {result}")
            return False

        # Save the video
        video = result.generated_videos[0]
        if hasattr(video, 'video'):
            video_data = video.video
            if hasattr(video_data, 'video_bytes') and video_data.video_bytes:
                with open(output_path, 'wb') as f:
                    f.write(video_data.video_bytes)
                print(f"Saved to: {output_path}")
                return True
            elif hasattr(video_data, 'uri') and video_data.uri:
                # Download from URI with service account authentication
                import urllib.request
                import google.auth
                import google.auth.transport.requests

                print(f"Downloading from: {video_data.uri}")

                # Get credentials and create authorized request
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

        print(f"Could not extract video data. Video object: {video}")
        return False

    except Exception as e:
        print(f"Error generating video: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    prompt = sys.argv[1]
    output_path = sys.argv[2]
    model = "veo-3.1-generate-preview"
    reference_images = []
    aspect_ratio = "16:9"

    # Parse optional arguments
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--aspect" and i + 1 < len(sys.argv):
            aspect_ratio = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--ref":
            i += 1
            # Collect all following args until next flag or end
            while i < len(sys.argv) and not sys.argv[i].startswith("--"):
                reference_images.append(sys.argv[i])
                i += 1
        else:
            i += 1

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    success = generate_video(
        prompt,
        output_path,
        model,
        reference_images if reference_images else None,
        aspect_ratio
    )

    if not success:
        # Save prompt for manual use
        prompt_file = output_path.replace(".mp4", "_prompt.txt")
        with open(prompt_file, "w") as f:
            f.write(prompt)
        print(f"Prompt saved to: {prompt_file}")

    sys.exit(0 if success else 1)
