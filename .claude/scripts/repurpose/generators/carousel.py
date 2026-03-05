"""
LinkedIn Carousel Generator.

Full pipeline:
1. Generate image prompt from insight
2. Generate Midjourney image via LegNext
3. Generate carousel JSON with slides
4. Generate PDFs via APITemplate (light + dark themes)
5. Convert PDFs to images via CloudConvert (light + dark themes)
6. Save accompanying post text

If image generation fails, entire carousel is skipped.
If PDF-to-image conversion fails, the carousel continues (images are optional).
"""

import json
import time
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional

from . import register_generator
from .base import (
    load_template,
    call_gemini,
    extract_json_from_response,
    save_content,
    build_generator_input,
    format_prompt_with_input,
    generate_slug,
)

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


# APITemplate template IDs
TEMPLATE_LIGHT = "c8877b23e275116a"
TEMPLATE_DARK = "d1677b23e271267e"

# LegNext API
LEGNEXT_API_URL = "https://api.legnext.ai/api/v1/diffusion"

# Image selection index (0-based, hardcoded to pick second image)
IMAGE_INDEX = 1


def _get_retry_config():
    """Get retry configuration from Config."""
    return Config.get_max_retries(), Config.get_retry_cooldown()


def _get_timeouts():
    """Get timeout configuration from Config."""
    return {
        "midjourney": Config.get_timeout("midjourney_image"),
        "pdf": Config.get_timeout("apitemplate_pdf"),
    }


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
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"curl POST error: {e}")
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
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"curl GET error: {e}")
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


def generate_image_prompt(insight: dict, tov_profile: str) -> Optional[str]:
    """
    Generate a Midjourney image prompt from the insight.

    Returns the prompt string or None on failure.
    """
    prompt_template = load_template("carousel_image_prompt.md")
    if not prompt_template:
        print("Error: Carousel Image Prompt template not found")
        return None

    input_data = build_generator_input(
        insight=insight,
        tov_profile=tov_profile,
        platform="linkedin_carousel",
        user_feedback="NO_FEEDBACK",
    )

    full_prompt = format_prompt_with_input(prompt_template, input_data)

    response = call_gemini(full_prompt)
    if not response:
        print("Failed to generate image prompt")
        return None

    data = extract_json_from_response(response)
    if data and "carousel_image_prompt" in data:
        return data["carousel_image_prompt"]

    print("Failed to parse image prompt response")
    return None


def _generate_midjourney_image_single_attempt(prompt: str, headers: dict, timeout: int = 300) -> Optional[str]:
    """
    Single attempt to generate image via LegNext/Midjourney API.

    Returns the image URL at index 1 (second image) or None on failure.
    """
    payload = {
        "text": prompt,
    }

    # Submit generation request
    result = _curl_post(LEGNEXT_API_URL, headers, payload, timeout=60)

    if not result:
        print("LegNext API request failed")
        return None

    job_id = result.get("job_id")
    if not job_id:
        print("No job_id in LegNext response")
        print(json.dumps(result, indent=2)[:300])
        return None

    print(f"Job submitted: {job_id}")

    # Poll for completion
    status_url = f"https://api.legnext.ai/api/v1/job/{job_id}"
    start_time = time.time()
    poll_interval = 5

    while time.time() - start_time < timeout:
        time.sleep(poll_interval)

        status_result = _curl_get(status_url, headers, timeout=30)

        if not status_result:
            print("Failed to get job status, retrying...")
            continue

        status = status_result.get("status", "").lower()

        if status in ["completed", "finished", "success", "done"]:
            # Get image URLs
            output = status_result.get("output", {})
            image_urls = output.get("image_urls", [])

            if not image_urls:
                print("No image URLs in completed job")
                return None

            if len(image_urls) <= IMAGE_INDEX:
                print(f"Not enough images (got {len(image_urls)}, need index {IMAGE_INDEX})")
                # Fall back to first image if available
                if image_urls:
                    return image_urls[0]
                return None

            selected_url = image_urls[IMAGE_INDEX]
            print(f"Image generated successfully (selected index {IMAGE_INDEX})")
            return selected_url

        elif status in ["failed", "error"]:
            error_msg = status_result.get("message", "Unknown error")
            print(f"Image generation failed: {error_msg}")
            return None

        print(f"Status: {status}...")

    print("Image generation timed out")
    return None


def generate_midjourney_image(prompt: str, timeout: int = None) -> Optional[str]:
    """
    Generate image via LegNext/Midjourney API with retry logic.

    Returns the image URL at index 1 (second image) or None on failure.
    Retries up to max_retries times with cooldown seconds between attempts.
    """
    api_key = Config.get_legnext_api_key()
    if not api_key:
        print("Error: LEGNEXT_API_KEY not set")
        return None

    max_retries, retry_cooldown = _get_retry_config()
    timeouts = _get_timeouts()
    if timeout is None:
        timeout = timeouts["midjourney"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print(f"Generating Midjourney image...")
    print(f"Prompt: {prompt[:80]}...")

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            print(f"Retry {attempt}/{max_retries} after {retry_cooldown}s cooldown...")
            time.sleep(retry_cooldown)

        result = _generate_midjourney_image_single_attempt(prompt, headers, timeout)
        if result:
            return result

        if attempt < max_retries:
            print(f"Attempt {attempt} failed, will retry...")

    print(f"All {max_retries} attempts failed for Midjourney image generation")
    return None


def generate_carousel_json(
    insight: dict,
    tov_profile: str,
    carousel_image_url: str,
) -> Optional[dict]:
    """
    Generate carousel JSON with slides.

    Returns the carousel data dict or None on failure.
    """
    prompt_template = load_template("linkedin_carousel.md")
    if not prompt_template:
        print("Error: LinkedIn Carousel template not found")
        return None

    input_data = build_generator_input(
        insight=insight,
        tov_profile=tov_profile,
        platform="linkedin_carousel",
        user_feedback="NO_FEEDBACK",
    )

    input_data["target_slides"] = "6-10 slides"
    input_data["content_requirements"] = {
        "hook_slide": True,
        "content_slides": True,
        "cta_slide": True,
        "max_slides": 10,
    }

    full_prompt = format_prompt_with_input(prompt_template, input_data)

    # Pass the image URL to the LLM so it can include it in the correct location
    # Using string concatenation to avoid f-string issues with JSON braces
    full_prompt += """

---

Carousel Image URL: """ + carousel_image_url + """

Use this exact URL for the carousel_image_url field in the hook slide.

---

Return as JSON with this structure:
{
  "profile": {
    "name": "{{USER_NAME}}",
    "title": "Your Title",
    "avatar_url": ""
  },
  "slides": [
    {"type": "hook", "headline": "Bold hook text", "carousel_image_url": "THE_IMAGE_URL_PROVIDED_ABOVE"},
    {"type": "content", "title": "Slide title", "body": "Slide content"},
    {"type": "list", "title": "List title", "list_items": [{"icon": "check", "text": "Item"}]},
    {"type": "final", "greeting": "Thanks!", "main_message": "Key takeaway", "cta_line1": "Follow for more", "cta_line2": "@eugen{{YOUTUBE_HANDLE}}"}
  ],
  "linkedin_post_text": "Accompanying post text for the carousel...",
  "metadata": {
    "total_slides": 8,
    "theme": "ai_agents"
  }
}

IMPORTANT: The carousel_image_url in the hook slide MUST be the exact URL provided above.
"""

    response = call_gemini(full_prompt)
    if not response:
        print("Failed to generate carousel JSON")
        return None

    data = extract_json_from_response(response)
    if not data or "slides" not in data:
        print("Failed to parse carousel JSON")
        return None

    # Verify the image URL was included correctly in hook slide
    if data.get("slides") and len(data["slides"]) > 0:
        hook_slide = data["slides"][0]
        if hook_slide.get("type") == "hook" and not hook_slide.get("carousel_image_url"):
            # Fallback: inject if LLM didn't include it
            hook_slide["carousel_image_url"] = carousel_image_url

    return data


def transform_to_apitemplate_format(slides_data: dict) -> dict:
    """
    Transform carousel JSON to APITemplate.io format.
    """
    profile = slides_data.get("profile", {})

    template_data = {
        "profile_name": profile.get("name", "{{USER_NAME}}"),
        "profile_title": profile.get("title", "Your Title"),
        "profile_avatar": profile.get("avatar_url", ""),
        "carousel_image_url": slides_data.get("carousel_image_url", ""),
    }

    slides = slides_data.get("slides", [])

    for i, slide in enumerate(slides, 1):
        slide_type = slide.get("type", "content")
        prefix = f"slide_{i}_"

        template_data[f"{prefix}type"] = slide_type

        if slide_type == "hook":
            template_data[f"{prefix}headline"] = slide.get("headline", "")

        elif slide_type == "content":
            template_data[f"{prefix}title"] = slide.get("title", "")
            template_data[f"{prefix}body"] = slide.get("body", "")

        elif slide_type == "list":
            template_data[f"{prefix}title"] = slide.get("title", "")
            list_items = slide.get("list_items", [])
            for j, item in enumerate(list_items, 1):
                template_data[f"{prefix}item_{j}_icon"] = item.get("icon", "bullet")
                template_data[f"{prefix}item_{j}_text"] = item.get("text", "")

        elif slide_type == "final":
            template_data[f"{prefix}greeting"] = slide.get("greeting", "")
            template_data[f"{prefix}message"] = slide.get("main_message", "")
            template_data[f"{prefix}cta_1"] = slide.get("cta_line1", "")
            template_data[f"{prefix}cta_2"] = slide.get("cta_line2", "")

    return template_data


def _generate_pdf_single_attempt(
    slides_data: dict,
    output_path: Path,
    template_id: str,
    api_key: str,
) -> Optional[tuple[str, str]]:
    """
    Single attempt to generate a PDF via APITemplate.io.

    Returns tuple of (local_path, download_url) or None on failure.
    """
    timeouts = _get_timeouts()
    # Correct URL format: template_id in query string
    url = f"https://rest.apitemplate.io/v2/create-pdf?template_id={template_id}"

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    # Send raw carousel JSON directly (APITemplate template expects this format)
    # This matches N8N behavior: $('Slides Parser').item.json.toJsonString()
    payload = slides_data

    result = _curl_post(url, headers, payload, timeout=timeouts["pdf"])

    if not result:
        print(f"APITemplate request failed for {template_id}")
        return None

    download_url = result.get("download_url") or result.get("file_url")

    if not download_url:
        print("No download URL in APITemplate response")
        print(json.dumps(result, indent=2)[:500])
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not _curl_download(download_url, output_path):
        print(f"Failed to download PDF: {output_path}")
        return None

    return (str(output_path), download_url)


def generate_pdf(
    slides_data: dict,
    output_path: Path,
    template_id: str,
) -> Optional[tuple[str, str]]:
    """
    Generate a PDF via APITemplate.io with retry logic.

    Returns tuple of (local_path, download_url) or None on failure.
    Retries up to max_retries times with cooldown seconds between attempts.
    """
    api_key = Config.get_apitemplate_api_key()
    if not api_key:
        print("Error: APITEMPLATE_API_KEY not set")
        return None

    max_retries, retry_cooldown = _get_retry_config()

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            print(f"Retry {attempt}/{max_retries} after {retry_cooldown}s cooldown...")
            time.sleep(retry_cooldown)

        result = _generate_pdf_single_attempt(slides_data, output_path, template_id, api_key)
        if result:
            return result

        if attempt < max_retries:
            print(f"Attempt {attempt} failed, will retry...")

    print(f"All {max_retries} attempts failed for PDF generation")
    return None


def convert_pdf_to_slide_images(
    pdf_download_url: str,
    output_dir: Path,
    total_slides: int,
    folder_name: str,
) -> Optional[list[str]]:
    """
    Convert a carousel PDF to individual slide images.

    Creates a subfolder with the carousel images.

    Args:
        pdf_download_url: URL to the PDF from APITemplate
        output_dir: Base output directory (Generated Content folder)
        total_slides: Number of slides in the carousel
        folder_name: Name for the images subfolder (e.g., "linkedin_carousel_images_001")

    Returns:
        List of output image paths, or None on failure
    """
    from utils.cloudconvert import convert_pdf_url_to_images

    images_dir = output_dir / folder_name

    print(f"  Converting PDF to images -> {folder_name}/")

    result = convert_pdf_url_to_images(
        pdf_url=pdf_download_url,
        output_dir=images_dir,
        total_slides=total_slides,
        filename_prefix="slide",
        image_format="jpg",
        timeout=300,
    )

    return result


@register_generator("linkedin_carousel")
def generate_carousel(
    insight: dict,
    tov_profile: str,
    output_dir: Path,
    insight_number: int = 1,
    user_feedback: str = "NO_FEEDBACK",
    mode: str = "solo",
    guests: list = None,
    **kwargs,
) -> Optional[str]:
    """
    Generate LinkedIn carousel PDFs from an insight.

    Full pipeline:
    1. Generate image prompt
    2. Generate Midjourney image via LegNext
    3. Generate carousel JSON
    4. Generate light theme PDF
    5. Generate dark theme PDF
    6. Convert light PDF to images
    7. Convert dark PDF to images
    8. Save accompanying post text

    If PDF generation fails, entire carousel is skipped.
    If PDF-to-image conversion fails, the carousel continues (images are optional).

    Returns path to the text file (primary output for manifest tracking).
    """
    print(f"Generating carousel for insight {insight_number}...")

    # Step 1: Generate image prompt
    print("  [1/8] Generating image prompt...")
    image_prompt = generate_image_prompt(insight, tov_profile)
    if not image_prompt:
        print("  SKIP: Failed to generate image prompt")
        return None

    # Step 2: Generate Midjourney image
    print("  [2/8] Generating Midjourney image via LegNext...")
    image_url = generate_midjourney_image(image_prompt)
    if not image_url:
        print("  SKIP: Failed to generate Midjourney image")
        return None

    # Step 3: Generate carousel JSON
    print("  [3/8] Generating carousel content...")
    carousel_data = generate_carousel_json(insight, tov_profile, image_url)
    if not carousel_data:
        print("  SKIP: Failed to generate carousel JSON")
        return None

    slide_count = len(carousel_data.get("slides", []))
    print(f"  Generated {slide_count} slides")

    # Create named subfolder
    core_insight = insight.get("core_insight", f"insight-{insight_number}")
    folder_name = generate_slug(core_insight, "linkedin-carousel")
    subfolder = output_dir / folder_name
    subfolder.mkdir(parents=True, exist_ok=True)

    # Step 4: Generate light theme PDF
    print("  [4/8] Generating light theme PDF...")
    light_pdf_path = subfolder / "carousel.pdf"
    light_result = generate_pdf(carousel_data, light_pdf_path, TEMPLATE_LIGHT)
    if not light_result:
        print("  SKIP: Failed to generate light theme PDF")
        return None
    light_local_path, light_download_url = light_result
    print(f"  Saved: {light_pdf_path.name}")

    # Step 5: Generate dark theme PDF
    print("  [5/8] Generating dark theme PDF...")
    dark_pdf_path = subfolder / "carousel_dark.pdf"
    dark_result = generate_pdf(carousel_data, dark_pdf_path, TEMPLATE_DARK)
    if not dark_result:
        print("  SKIP: Failed to generate dark theme PDF")
        return None
    dark_local_path, dark_download_url = dark_result
    print(f"  Saved: {dark_pdf_path.name}")

    # Step 6: Convert light PDF to images
    print("  [6/8] Converting light PDF to images...")
    light_images_folder = "carousel_images"
    light_images = convert_pdf_to_slide_images(
        pdf_download_url=light_download_url,
        output_dir=subfolder,
        total_slides=slide_count,
        folder_name=light_images_folder,
    )
    if light_images:
        print(f"  Created {len(light_images)} images in {light_images_folder}/")
    else:
        print(f"  Warning: Failed to convert light PDF to images (continuing anyway)")

    # Step 7: Convert dark PDF to images
    print("  [7/8] Converting dark PDF to images...")
    dark_images_folder = "carousel_images_dark"
    dark_images = convert_pdf_to_slide_images(
        pdf_download_url=dark_download_url,
        output_dir=subfolder,
        total_slides=slide_count,
        folder_name=dark_images_folder,
    )
    if dark_images:
        print(f"  Created {len(dark_images)} images in {dark_images_folder}/")
    else:
        print(f"  Warning: Failed to convert dark PDF to images (continuing anyway)")

    # Step 8: Save accompanying post text
    print("  [8/8] Saving accompanying post text...")
    post_text = carousel_data.get("linkedin_post_text", "")
    if not post_text:
        print("  Warning: No accompanying post text in carousel data")
        post_text = ""

    text_path = subfolder / "post.md"
    with open(text_path, "w") as f:
        f.write(post_text)
    print(f"  Saved: post.md")

    # Summary
    images_summary = []
    if light_images:
        images_summary.append(f"{len(light_images)} light")
    if dark_images:
        images_summary.append(f"{len(dark_images)} dark")
    images_str = f", {' + '.join(images_summary)} images" if images_summary else ""

    print(f"Carousel complete: {folder_name}/ ({slide_count} slides, 2 PDFs{images_str})")
    return str(text_path)
