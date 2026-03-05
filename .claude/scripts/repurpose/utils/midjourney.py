"""
Midjourney Integration via LegNext API.

Generates carousel background images using Midjourney v7.
"""

import json
import subprocess
import tempfile
import os
import time
from pathlib import Path
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


def _curl_post(url: str, headers: dict, data: dict, timeout: int = 120) -> Optional[dict]:
    """Make a POST request using curl."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        data_file = f.name

    try:
        cmd = ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json"]
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
        cmd.extend(["-d", f"@{data_file}", url])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    except:
        return None
    finally:
        try:
            os.unlink(data_file)
        except:
            pass


def _curl_get(url: str, headers: dict, timeout: int = 60) -> Optional[dict]:
    """Make a GET request using curl."""
    cmd = ["curl", "-s"]
    for k, v in headers.items():
        cmd.extend(["-H", f"{k}: {v}"])
    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    except:
        return None


def _curl_download(url: str, output_path: Path, timeout: int = 60) -> bool:
    """Download a file using curl."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-o", str(output_path), url],
            capture_output=True,
            timeout=timeout,
        )
        return result.returncode == 0 and output_path.exists()
    except:
        return False


# LegNext API endpoint
LEGNEXT_API_URL = "https://api.legnext.ai/api/v1/diffusion"

# Required style suffix for all prompts
MIDJOURNEY_STYLE_SUFFIX = (
    "rendered in ASCII-style pixel blocks that glow like tiny silver lights, "
    "giving it a retro-digital, embroidery-like look --ar 16:9 --v 7.0"
)


def generate_background_image(
    prompt: str,
    output_path: Path,
    add_style_suffix: bool = True,
    timeout: int = 300,
) -> Optional[str]:
    """
    Generate a background image using Midjourney via LegNext.

    Args:
        prompt: The image generation prompt
        output_path: Path to save the output image
        add_style_suffix: Whether to add the standard style suffix
        timeout: Total timeout in seconds

    Returns:
        Path to generated image or None on failure
    """
    api_key = Config.get_legnext_api_key()
    if not api_key:
        print("Error: LEGNEXT_API_KEY not set")
        return None

    # Add style suffix if requested
    if add_style_suffix and MIDJOURNEY_STYLE_SUFFIX not in prompt:
        prompt = f"{prompt} {MIDJOURNEY_STYLE_SUFFIX}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "model": "midjourney",
        "version": "v7",
    }

    try:
        print(f"Generating image via Midjourney/LegNext...")
        print(f"Prompt: {prompt[:100]}...")

        # Submit the generation request
        result = _curl_post(LEGNEXT_API_URL, headers, payload, timeout=60)

        if not result:
            print("LegNext API request failed")
            return None

        # Check for task ID (async generation)
        task_id = result.get("task_id") or result.get("id")

        if task_id:
            # Poll for completion
            image_url = poll_for_completion(task_id, api_key, timeout)
        else:
            # Direct URL response
            image_url = (
                result.get("image_url") or
                result.get("url") or
                result.get("output", [{}])[0].get("url")
            )

        if not image_url:
            print("No image URL in response")
            print(json.dumps(result, indent=2)[:500])
            return None

        # Download the image
        print("Downloading generated image...")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not _curl_download(image_url, output_path):
            print("Failed to download image")
            return None

        print(f"Image saved: {output_path}")
        return str(output_path)

    except Exception as e:
        print(f"Error generating image: {e}")
        return None


def poll_for_completion(
    task_id: str,
    api_key: str,
    timeout: int = 300,
    poll_interval: int = 5,
) -> Optional[str]:
    """
    Poll for task completion.

    Args:
        task_id: The task ID to poll
        api_key: API key
        timeout: Total timeout
        poll_interval: Seconds between polls

    Returns:
        Image URL or None
    """
    status_url = f"{LEGNEXT_API_URL}/status/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            result = _curl_get(status_url, headers, timeout=30)

            if not result:
                time.sleep(poll_interval)
                continue

            status = result.get("status", "").lower()

            if status in ["completed", "finished", "success"]:
                return (
                    result.get("image_url") or
                    result.get("url") or
                    result.get("output", [{}])[0].get("url")
                )
            elif status in ["failed", "error"]:
                print(f"Generation failed: {result.get('message', 'Unknown error')}")
                return None

            print(f"Status: {status}...")
            time.sleep(poll_interval)

        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(poll_interval)

    print("Polling timed out")
    return None


def generate_carousel_background(
    insight_topic: str,
    output_path: Path,
) -> Optional[str]:
    """
    Generate a carousel background image based on the insight topic.

    Args:
        insight_topic: The topic/theme of the carousel
        output_path: Path to save the image

    Returns:
        Path to generated image or None
    """
    # Create a prompt from the topic
    prompt = (
        f"photorealistic shot of {insight_topic}, "
        "abstract visualization, professional business aesthetic, "
        "clean composition, cinematic lighting"
    )

    return generate_background_image(prompt, output_path)


if __name__ == "__main__":
    print("Midjourney/LegNext Integration")
    print("=" * 50)

    api_key = Config.get_legnext_api_key()
    print(f"API Key: {'present' if api_key else 'MISSING'}")

    if api_key:
        print(f"\nStyle suffix: {MIDJOURNEY_STYLE_SUFFIX[:50]}...")
