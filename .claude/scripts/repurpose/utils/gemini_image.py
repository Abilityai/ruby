"""
Gemini Image API utility module.

Handles image generation using Google's Gemini Image API (gemini-3-pro-image-preview).
Used by both thumbnails and igcovers generators.
"""

import base64
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional
import sys

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


# Cache directory for reference photos
PHOTO_CACHE_DIR = Path.home() / ".cache" / "ruby" / "reference_photos"


def get_reference_photos_folder_id() -> str:
    """Get the Google Drive folder ID for the creator's reference photos."""
    return Config.GDRIVE_FOLDERS.get("reference_photos", "YOUR_FALLBACK_PHOTO_ID")


def download_reference_photos(max_photos: int = 6, force_refresh: bool = False) -> list[Path]:
    """
    Download reference photos from Google Drive and cache locally.

    Args:
        max_photos: Maximum number of photos to download (default 6, matching N8N)
        force_refresh: If True, re-download even if cached

    Returns:
        List of paths to downloaded photos
    """
    PHOTO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Check if we have cached photos
    cached_photos = list(PHOTO_CACHE_DIR.glob("*.png")) + list(PHOTO_CACHE_DIR.glob("*.jpg"))

    if len(cached_photos) >= max_photos and not force_refresh:
        print(f"Using {len(cached_photos)} cached reference photos from {PHOTO_CACHE_DIR}")
        return sorted(cached_photos)[:max_photos]

    print(f"Downloading reference photos from Google Drive...")

    # Get Google Drive script path
    gdrive_script = Config.get_google_drive_script()
    folder_id = get_reference_photos_folder_id()

    try:
        # List files in the Reference Photos folder
        result = subprocess.run(
            ["python3", gdrive_script, "list", folder_id],
            capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            print(f"Error listing photos folder: {result.stderr}")
            # Return any cached photos we have
            return sorted(cached_photos)[:max_photos] if cached_photos else []

        # Parse the output format:
        #   [F] filename.jpg
        #       ID: file_id
        files = []
        lines = result.stdout.strip().split("\n")
        current_name = None
        for line in lines:
            line = line.strip()
            # Match file lines: [F] filename.ext
            if line.startswith("[F]"):
                name = line[4:].strip()
                if name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    current_name = name
                else:
                    current_name = None
            # Match ID lines following a file
            elif line.startswith("ID:") and current_name:
                file_id = line[3:].strip()
                files.append((current_name, file_id))
                current_name = None

        if not files:
            print("No image files found in reference photos folder")
            return sorted(cached_photos)[:max_photos] if cached_photos else []

        # Download up to max_photos
        downloaded = []
        for name, file_id in files[:max_photos]:
            local_path = PHOTO_CACHE_DIR / name

            # Skip if already cached (unless force refresh)
            if local_path.exists() and not force_refresh:
                downloaded.append(local_path)
                continue

            print(f"  Downloading {name}...")
            dl_result = subprocess.run(
                ["python3", gdrive_script, "download", file_id, str(local_path)],
                capture_output=True, text=True, timeout=120
            )

            if dl_result.returncode == 0 and local_path.exists():
                downloaded.append(local_path)
            else:
                print(f"  Warning: Failed to download {name}")

        print(f"Downloaded {len(downloaded)} reference photos")
        return sorted(downloaded)

    except subprocess.TimeoutExpired:
        print("Timeout downloading reference photos")
        return sorted(cached_photos)[:max_photos] if cached_photos else []
    except Exception as e:
        print(f"Error downloading reference photos: {e}")
        return sorted(cached_photos)[:max_photos] if cached_photos else []


def encode_image_to_base64(image_path: Path) -> Optional[str]:
    """
    Encode an image file to base64.

    Args:
        image_path: Path to the image file

    Returns:
        Base64-encoded string, or None on error
    """
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None


def get_image_mime_type(image_path: Path) -> str:
    """Get the MIME type for an image file."""
    suffix = image_path.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mime_types.get(suffix, "image/png")


def generate_image(
    prompt: str,
    reference_photos: list[Path],
    aspect_ratio: str = "16:9",
    max_retries: int = 3,
    retry_delay: int = 5,
) -> Optional[bytes]:
    """
    Generate an image using Gemini Image API.

    Args:
        prompt: The image generation prompt
        reference_photos: List of paths to reference photos
        aspect_ratio: Aspect ratio ("16:9" for thumbnails, "9:16" for IGCovers)
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        Generated image as bytes, or None on failure
    """
    api_key = Config.get_gemini_api_key()
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        return None

    model = Config.GEMINI_MODELS.get("image", "gemini-3-pro-image-preview")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # Build the request parts
    parts = [{"text": prompt}]

    # Add reference photos as inline data
    for photo_path in reference_photos:
        base64_data = encode_image_to_base64(photo_path)
        if base64_data:
            mime_type = get_image_mime_type(photo_path)
            parts.append({
                "inlineData": {
                    "mimeType": mime_type,
                    "data": base64_data
                }
            })

    # Build request body
    request_body = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "imageConfig": {
                "aspectRatio": aspect_ratio
            }
        }
    }

    for attempt in range(max_retries):
        try:
            # Write request to temp file (for curl)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(request_body, f)
                request_file = f.name

            try:
                result = subprocess.run(
                    ["curl", "-s", "-X", "POST",
                     "-H", "Content-Type: application/json",
                     "-d", f"@{request_file}",
                     api_url],
                    capture_output=True, text=True, timeout=180  # 3 minute timeout
                )

                if result.returncode != 0:
                    print(f"Gemini Image API call failed: {result.stderr}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay}s... (attempt {attempt + 2}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    return None

                response = json.loads(result.stdout)

                # Check for API error
                if "error" in response:
                    error_msg = response["error"].get("message", "Unknown error")
                    print(f"Gemini Image API error: {error_msg}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay}s... (attempt {attempt + 2}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    return None

                # Extract the generated image
                image_data = extract_image_from_response(response)
                if image_data:
                    return image_data

                print("No image data found in response")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay}s... (attempt {attempt + 2}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                return None

            finally:
                try:
                    os.unlink(request_file)
                except:
                    pass

        except subprocess.TimeoutExpired:
            print(f"Timeout generating image (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None
        except Exception as e:
            print(f"Error generating image: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None

    return None


def extract_image_from_response(response: dict) -> Optional[bytes]:
    """
    Extract image data from Gemini API response.

    Args:
        response: The API response dictionary

    Returns:
        Image data as bytes, or None if not found
    """
    try:
        candidates = response.get("candidates", [])
        if not candidates:
            return None

        parts = candidates[0].get("content", {}).get("parts", [])

        # Find the part containing inline image data
        for part in parts:
            if "inlineData" in part:
                inline_data = part["inlineData"]
                if "data" in inline_data:
                    # Decode base64 to bytes
                    return base64.b64decode(inline_data["data"])

        return None

    except Exception as e:
        print(f"Error extracting image from response: {e}")
        return None


def generate_prompts(
    transcript: str,
    prompt_template: str,
    custom_title: Optional[str] = None,
    num_prompts: int = 15,
) -> list[str]:
    """
    Generate image prompts from a transcript using Gemini.

    Args:
        transcript: The video transcript text
        prompt_template: The prompt generator template
        custom_title: Optional custom title to use in prompts
        num_prompts: Number of prompts to generate (default 15)

    Returns:
        List of generated prompts
    """
    api_key = Config.get_gemini_api_key()
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        return []

    # Build user input as JSON object matching template's expected INPUT FORMAT
    user_input = {
        "transcript": transcript,
        "custom_title": custom_title if custom_title else "NONE",
        "user_feedback": "NO_FEEDBACK"
    }
    user_input_text = json.dumps(user_input, indent=2)

    # Build the request
    model = Config.GEMINI_MODELS.get("primary", "gemini-3-pro-preview")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    request_body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_input_text}]
            }
        ],
        "systemInstruction": {
            "parts": [{"text": prompt_template}]
        },
        "generationConfig": {
            "temperature": 0.8,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        }
    }

    max_retries = Config.get_max_retries()
    retry_delay = Config.get_retry_cooldown()

    for attempt in range(max_retries):
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(request_body, f)
                request_file = f.name

            try:
                result = subprocess.run(
                    ["curl", "-s", "-X", "POST",
                     "-H", "Content-Type: application/json",
                     "-d", f"@{request_file}",
                     api_url],
                    capture_output=True, text=True, timeout=120
                )

                if result.returncode != 0:
                    print(f"Prompt generation API call failed: {result.stderr}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    return []

                response = json.loads(result.stdout)

                if "error" in response:
                    error_msg = response["error"].get("message", "Unknown error")
                    print(f"Prompt generation error: {error_msg}")

                    # Try fallback model
                    if attempt == 0:
                        print("Trying fallback model...")
                        model = Config.GEMINI_MODELS.get("fallback", "gemini-2.5-pro")
                        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                        continue

                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return []

                # Extract text response
                candidates = response.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")
                        # Parse JSON array from response
                        prompts = parse_prompts_from_response(text)
                        if prompts:
                            return prompts[:num_prompts]

                print("No prompts found in response")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return []

            finally:
                try:
                    os.unlink(request_file)
                except:
                    pass

        except Exception as e:
            print(f"Error generating prompts: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return []

    return []


def parse_prompts_from_response(text: str) -> list[str]:
    """
    Parse prompts array from Gemini response text.

    Args:
        text: The response text (should be JSON array)

    Returns:
        List of prompt strings
    """
    import re

    # Try to find JSON array in response
    # First, try direct JSON parse
    try:
        result = json.loads(text.strip())
        if isinstance(result, list):
            return [str(p) for p in result if p]
    except json.JSONDecodeError:
        pass

    # Try to extract JSON array from markdown code block
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'\[[\s\S]*\]',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                # Clean up the match
                json_str = match.strip()
                if not json_str.startswith('['):
                    continue
                result = json.loads(json_str)
                if isinstance(result, list):
                    return [str(p) for p in result if p]
            except json.JSONDecodeError:
                continue

    return []


def save_image(image_data: bytes, output_path: Path) -> bool:
    """
    Save image data to a file.

    Args:
        image_data: Image bytes
        output_path: Path to save to

    Returns:
        True if successful
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(image_data)
        return True
    except Exception as e:
        print(f"Error saving image to {output_path}: {e}")
        return False


def upload_to_google_drive(local_path: Path, folder_id: str, name: Optional[str] = None) -> Optional[str]:
    """
    Upload a file to Google Drive.

    Args:
        local_path: Path to the local file
        folder_id: Google Drive folder ID
        name: Optional name for the file (defaults to local filename)

    Returns:
        Google Drive file ID, or None on failure
    """
    gdrive_script = Config.get_google_drive_script()
    file_name = name or local_path.name

    try:
        result = subprocess.run(
            ["python3", gdrive_script, "upload", str(local_path), file_name, folder_id],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            print(f"Error uploading to Google Drive: {result.stderr}")
            return None

        # Parse the file ID from output
        # Expected format: "Uploaded: filename (ID: abc123)"
        output = result.stdout.strip()
        if "ID:" in output:
            file_id = output.split("ID:")[-1].strip().rstrip(")")
            return file_id

        return None

    except Exception as e:
        print(f"Error uploading {local_path}: {e}")
        return None


def create_google_drive_folder(name: str, parent_id: str) -> Optional[str]:
    """
    Create a folder in Google Drive.

    Args:
        name: Folder name
        parent_id: Parent folder ID

    Returns:
        New folder ID, or None on failure
    """
    gdrive_script = Config.get_google_drive_script()

    try:
        result = subprocess.run(
            ["python3", gdrive_script, "mkdir", name, parent_id],
            capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            print(f"Error creating folder: {result.stderr}")
            return None

        # Parse folder ID from output
        output = result.stdout.strip()
        if "ID:" in output:
            folder_id = output.split("ID:")[-1].strip().rstrip(")")
            return folder_id

        # Try to parse as just the ID
        if output and len(output) < 50:
            return output

        return None

    except Exception as e:
        print(f"Error creating folder {name}: {e}")
        return None


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gemini Image API utilities")
    parser.add_argument("--download-photos", action="store_true", help="Download reference photos")
    parser.add_argument("--refresh", action="store_true", help="Force refresh cached photos")
    parser.add_argument("--test-generate", type=str, help="Test image generation with a prompt")
    parser.add_argument("--aspect", type=str, default="16:9", help="Aspect ratio (16:9 or 9:16)")

    args = parser.parse_args()

    if args.download_photos:
        photos = download_reference_photos(force_refresh=args.refresh)
        print(f"\nDownloaded photos:")
        for p in photos:
            print(f"  {p}")

    if args.test_generate:
        photos = download_reference_photos()
        if photos:
            print(f"\nGenerating image with prompt: {args.test_generate[:100]}...")
            image_data = generate_image(args.test_generate, photos, args.aspect)
            if image_data:
                output_path = Path("/tmp/test_generated_image.png")
                save_image(image_data, output_path)
                print(f"Saved test image to: {output_path}")
            else:
                print("Failed to generate image")
        else:
            print("No reference photos available")
