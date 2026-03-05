"""
APITemplate.io Integration.

Generates PDF carousels from slide data using APITemplate.io templates.
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


# Template IDs
TEMPLATES = {
    "carousel": "d1677b23e271267e",
    "carousel_alt": "c8877b23e275116a",
    "framer_cover": "6d577b235f5c06ca",
}


def generate_carousel_pdf(
    slides_data: dict,
    output_path: Path,
    template_id: str = None,
    timeout: int = 120,
) -> Optional[str]:
    """
    Generate a carousel PDF using APITemplate.io.

    Args:
        slides_data: Carousel slide data (from carousel generator)
        output_path: Path to save the PDF
        template_id: Template ID (defaults to carousel template)
        timeout: Request timeout in seconds

    Returns:
        Path to generated PDF or None on failure
    """
    api_key = Config.get_apitemplate_api_key()
    if not api_key:
        print("Error: APITEMPLATE_API_KEY not set")
        return None

    if template_id is None:
        template_id = TEMPLATES["carousel"]

    # Prepare the API request
    url = "https://api.apitemplate.io/v2/create-pdf"

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    # Transform slides data to APITemplate format
    payload = {
        "template_id": template_id,
        "export_type": "file",
        "expiration": 10,  # 10 minutes
        "output_file": str(output_path.name),
        "data": transform_to_apitemplate_format(slides_data),
    }

    try:
        print(f"Generating carousel PDF via APITemplate.io...")

        result = _curl_post(url, headers, payload, timeout)

        if not result:
            print("APITemplate request failed")
            return None

        # Check for download URL
        download_url = result.get("download_url") or result.get("file_url")

        if not download_url:
            print("No download URL in response")
            print(json.dumps(result, indent=2)[:500])
            return None

        # Download the PDF
        print(f"Downloading PDF...")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not _curl_download(download_url, output_path):
            print("Failed to download PDF")
            return None

        print(f"Carousel PDF saved: {output_path}")
        return str(output_path)

    except Exception as e:
        print(f"Error generating carousel PDF: {e}")
        return None


def transform_to_apitemplate_format(slides_data: dict) -> dict:
    """
    Transform our carousel JSON to APITemplate.io format.

    Args:
        slides_data: Our internal carousel format

    Returns:
        APITemplate-compatible data dict
    """
    # Extract profile info
    profile = slides_data.get("profile", {})

    # Build slide data
    template_data = {
        "profile_name": profile.get("name", "{{USER_NAME}}"),
        "profile_title": profile.get("title", "Your Title"),
        "profile_avatar": profile.get("avatar_url", ""),
    }

    # Add slides
    slides = slides_data.get("slides", [])

    for i, slide in enumerate(slides, 1):
        slide_type = slide.get("type", "content")
        prefix = f"slide_{i}_"

        if slide_type == "hook":
            template_data[f"{prefix}headline"] = slide.get("headline", "")

        elif slide_type == "content":
            template_data[f"{prefix}title"] = slide.get("title", "")
            template_data[f"{prefix}body"] = slide.get("body", "")

        elif slide_type == "list":
            template_data[f"{prefix}title"] = slide.get("title", "")
            list_items = slide.get("list_items", [])
            for j, item in enumerate(list_items, 1):
                template_data[f"{prefix}item_{j}"] = item.get("text", "")

        elif slide_type == "final":
            template_data[f"{prefix}greeting"] = slide.get("greeting", "")
            template_data[f"{prefix}message"] = slide.get("main_message", "")
            template_data[f"{prefix}cta_1"] = slide.get("cta_line1", "")
            template_data[f"{prefix}cta_2"] = slide.get("cta_line2", "")

    return template_data


def get_template_info(template_id: str) -> Optional[dict]:
    """
    Get information about a template.

    Args:
        template_id: Template ID

    Returns:
        Template info dict or None
    """
    api_key = Config.get_apitemplate_api_key()
    if not api_key:
        return None

    url = f"https://api.apitemplate.io/v2/list-templates/{template_id}"

    try:
        result = subprocess.run(
            ["curl", "-s", "-H", f"X-API-KEY: {api_key}", url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except:
        pass

    return None


if __name__ == "__main__":
    # Test APITemplate integration
    print("APITemplate.io Integration")
    print("=" * 50)

    api_key = Config.get_apitemplate_api_key()
    print(f"API Key: {'present' if api_key else 'MISSING'}")

    if api_key:
        print("\nAvailable templates:")
        for name, tid in TEMPLATES.items():
            print(f"  {name}: {tid}")
