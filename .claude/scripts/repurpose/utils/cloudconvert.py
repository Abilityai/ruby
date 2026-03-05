"""
CloudConvert Integration.

Converts carousel PDFs to individual slide images.

Follows the N8N workflow pattern:
1. import/url - Import PDF from URL
2. convert - Convert PDF to JPG images
3. export/url - Export images to downloadable URLs
4. Poll status until finished
5. Download individual slide images
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


# CloudConvert API endpoints
CLOUDCONVERT_BASE_URL = "https://api.cloudconvert.com/v2"
IMPORT_URL_ENDPOINT = f"{CLOUDCONVERT_BASE_URL}/import/url"
CONVERT_ENDPOINT = f"{CLOUDCONVERT_BASE_URL}/convert"
EXPORT_URL_ENDPOINT = f"{CLOUDCONVERT_BASE_URL}/export/url"
TASK_STATUS_ENDPOINT = f"{CLOUDCONVERT_BASE_URL}/tasks"


def _curl_post(url: str, headers: dict, data: dict, timeout: int = 60) -> Optional[dict]:
    """Make a POST request using curl."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        data_file = f.name

    cmd = ["curl", "-s", "-X", "POST"]
    for k, v in headers.items():
        cmd.extend(["-H", f"{k}: {v}"])
    cmd.extend(["-d", f"@{data_file}", url])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        print(f"curl POST failed: {result.stderr[:200] if result.stderr else 'no output'}")
        return None
    except subprocess.TimeoutExpired:
        print(f"curl POST timed out after {timeout}s")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse response: {e}")
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
        return result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        print(f"curl download error: {e}")
        return False


def _get_headers() -> Optional[dict]:
    """Get CloudConvert API headers with authentication."""
    api_key = Config.get_cloudconvert_api_key()
    if not api_key:
        print("Error: CLOUDCONVERT_API_KEY not set")
        return None

    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def convert_pdf_url_to_images(
    pdf_url: str,
    output_dir: Path,
    total_slides: int,
    filename_prefix: str = "slide",
    image_format: str = "jpg",
    timeout: int = 300,
    poll_interval: int = 5,
) -> Optional[list[str]]:
    """
    Convert a PDF (from URL) to individual slide images using CloudConvert.

    This follows the N8N workflow pattern:
    1. import/url - Import PDF from the download URL
    2. convert - Convert PDF to JPG images (pages 1-N)
    3. export/url - Export images to downloadable URLs
    4. Poll status until finished
    5. Download individual slide images

    Args:
        pdf_url: URL to the PDF file (e.g., APITemplate download_url)
        output_dir: Directory to save output images
        total_slides: Number of slides/pages in the PDF
        filename_prefix: Prefix for output filenames (default: "slide")
        image_format: Output format (jpg, png)
        timeout: Total timeout in seconds for the conversion
        poll_interval: Seconds between status polls

    Returns:
        List of output image paths, or None on failure
    """
    headers = _get_headers()
    if not headers:
        return None

    print(f"Converting PDF to {image_format.upper()} images via CloudConvert...")
    print(f"  PDF URL: {pdf_url[:80]}...")
    print(f"  Total slides: {total_slides}")

    try:
        # Step 1: Import PDF from URL
        print("  [1/4] Importing PDF from URL...")
        import_payload = {
            "url": pdf_url,
            "filename": "carousel.pdf"
        }

        import_response = _curl_post(IMPORT_URL_ENDPOINT, headers, import_payload, timeout=60)

        if not import_response:
            print("  Failed to create import task")
            return None

        if "error" in import_response:
            print(f"  Import error: {import_response.get('error', {}).get('message', 'Unknown')}")
            return None

        import_task_id = import_response.get("data", {}).get("id")
        if not import_task_id:
            print("  No import task ID returned")
            print(f"  Response: {json.dumps(import_response, indent=2)[:500]}")
            return None

        print(f"  Import task ID: {import_task_id}")

        # Step 2: Create convert task
        print("  [2/4] Creating convert task...")
        convert_payload = {
            "input": import_task_id,
            "input_format": "pdf",
            "output_format": image_format,
            "pages": f"1-{total_slides}",
            "optimize_print": True
        }

        convert_response = _curl_post(CONVERT_ENDPOINT, headers, convert_payload, timeout=60)

        if not convert_response:
            print("  Failed to create convert task")
            return None

        if "error" in convert_response:
            print(f"  Convert error: {convert_response.get('error', {}).get('message', 'Unknown')}")
            return None

        convert_task_id = convert_response.get("data", {}).get("id")
        if not convert_task_id:
            print("  No convert task ID returned")
            return None

        print(f"  Convert task ID: {convert_task_id}")

        # Step 3: Create export task
        print("  [3/4] Creating export task...")
        export_payload = {
            "input": convert_task_id,
            "archive_multiple_files": False
        }

        export_response = _curl_post(EXPORT_URL_ENDPOINT, headers, export_payload, timeout=60)

        if not export_response:
            print("  Failed to create export task")
            return None

        if "error" in export_response:
            print(f"  Export error: {export_response.get('error', {}).get('message', 'Unknown')}")
            return None

        export_task_id = export_response.get("data", {}).get("id")
        if not export_task_id:
            print("  No export task ID returned")
            return None

        print(f"  Export task ID: {export_task_id}")

        # Step 4: Poll for completion
        print("  [4/4] Waiting for conversion to complete...")
        start_time = time.time()
        task_status_url = f"{TASK_STATUS_ENDPOINT}/{export_task_id}"

        while time.time() - start_time < timeout:
            time.sleep(poll_interval)

            status_response = _curl_get(task_status_url, headers, timeout=30)

            if not status_response:
                print("  Failed to get task status, retrying...")
                continue

            task_data = status_response.get("data", {})
            status = task_data.get("status", "").lower()

            if status == "finished":
                print("  Conversion finished!")

                # Extract file URLs from result
                result = task_data.get("result", {})
                files = result.get("files", [])

                if not files:
                    print("  No files in result")
                    return None

                # Download images
                output_dir.mkdir(parents=True, exist_ok=True)
                output_paths = []

                for idx, file_info in enumerate(files, 1):
                    file_url = file_info.get("url")
                    if not file_url:
                        print(f"  No URL for file {idx}")
                        continue

                    filename = f"{filename_prefix}_{idx:02d}.{image_format}"
                    output_path = output_dir / filename

                    if _curl_download(file_url, output_path):
                        output_paths.append(str(output_path))
                        print(f"  Downloaded: {filename}")
                    else:
                        print(f"  Failed to download: {filename}")

                print(f"  Downloaded {len(output_paths)} slides")
                return output_paths

            elif status in ["error", "failed"]:
                error_msg = task_data.get("message", "Unknown error")
                print(f"  Conversion failed: {error_msg}")
                return None

            else:
                elapsed = int(time.time() - start_time)
                print(f"  Status: {status} ({elapsed}s elapsed)")

        print(f"  Conversion timed out after {timeout}s")
        return None

    except Exception as e:
        print(f"  Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return None


def convert_pdf_to_images(
    pdf_path: Path,
    output_dir: Path,
    image_format: str = "jpg",
    dpi: int = 300,
    timeout: int = 300,
) -> Optional[list[str]]:
    """
    Convert a local PDF to individual images using CloudConvert.

    This version uploads the PDF first, then converts.
    For PDFs already available via URL, use convert_pdf_url_to_images() instead.

    Args:
        pdf_path: Path to the input PDF
        output_dir: Directory to save output images
        image_format: Output format (jpg, png)
        dpi: Resolution in DPI
        timeout: Total timeout in seconds

    Returns:
        List of output image paths, or None on failure
    """
    headers = _get_headers()
    if not headers:
        return None

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return None

    print(f"Converting local PDF to {image_format.upper()} images...")

    try:
        # Step 1: Create job with upload + convert + export tasks
        job_payload = {
            "tasks": {
                "upload-pdf": {
                    "operation": "import/upload"
                },
                "convert-pages": {
                    "operation": "convert",
                    "input": ["upload-pdf"],
                    "output_format": image_format,
                    "pages": "1-",  # All pages
                    "pixel_density": dpi,
                },
                "export-images": {
                    "operation": "export/url",
                    "input": ["convert-pages"],
                    "inline": False,
                    "archive_multiple_files": False,
                }
            }
        }

        # Create job
        job_response = _curl_post(f"{CLOUDCONVERT_BASE_URL}/jobs", headers, job_payload, timeout=60)

        if not job_response:
            print("Failed to create job")
            return None

        if "error" in job_response:
            print(f"Job creation error: {job_response.get('error', {}).get('message', 'Unknown')}")
            return None

        job_data = job_response.get("data", {})
        job_id = job_data.get("id")

        if not job_id:
            print("No job ID returned")
            return None

        # Find upload task
        upload_task = None
        for task in job_data.get("tasks", []):
            if task.get("name") == "upload-pdf":
                upload_task = task
                break

        if not upload_task or not upload_task.get("result", {}).get("form"):
            print("No upload task or form found")
            return None

        # Step 2: Upload the PDF using curl multipart
        form = upload_task["result"]["form"]
        upload_url = form["url"]
        params = form.get("parameters", {})

        # Build curl command for multipart upload
        cmd = ["curl", "-s", "-X", "POST"]
        for key, value in params.items():
            cmd.extend(["-F", f"{key}={value}"])
        cmd.extend(["-F", f"file=@{pdf_path}"])
        cmd.append(upload_url)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"Failed to upload PDF: {result.stderr[:200] if result.stderr else 'unknown error'}")
            return None

        print("PDF uploaded, waiting for conversion...")

        # Step 3: Wait for job completion
        start_time = time.time()
        job_status_url = f"{CLOUDCONVERT_BASE_URL}/jobs/{job_id}"

        while time.time() - start_time < timeout:
            time.sleep(3)

            status_response = _curl_get(job_status_url, headers, timeout=30)

            if not status_response:
                print("Failed to get job status, retrying...")
                continue

            job_status = status_response.get("data", {})
            status = job_status.get("status", "")

            if status == "finished":
                break
            elif status == "error":
                print("Conversion failed")
                for task in job_status.get("tasks", []):
                    if task.get("status") == "error":
                        print(f"  Error in {task.get('name')}: {task.get('message', 'Unknown')}")
                return None

            elapsed = int(time.time() - start_time)
            print(f"  Status: {status} ({elapsed}s elapsed)")

        # Step 4: Download the converted images
        output_dir.mkdir(parents=True, exist_ok=True)
        output_paths = []

        for task in job_status.get("tasks", []):
            if task.get("name") == "export-images" and task.get("result"):
                files = task["result"].get("files", [])
                for i, file_info in enumerate(files, 1):
                    file_url = file_info.get("url")
                    if not file_url:
                        continue

                    filename = f"slide_{i:02d}.{image_format}"
                    output_path = output_dir / filename

                    if _curl_download(file_url, output_path):
                        output_paths.append(str(output_path))
                        print(f"  Downloaded: {filename}")
                    else:
                        print(f"  Failed to download: {filename}")

        print(f"Converted {len(output_paths)} slides")
        return output_paths

    except Exception as e:
        print(f"Error converting PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_account_info() -> Optional[dict]:
    """Get CloudConvert account info (credits remaining, etc.)."""
    headers = _get_headers()
    if not headers:
        return None

    result = _curl_get(f"{CLOUDCONVERT_BASE_URL}/users/me", headers)
    if result:
        return result.get("data")
    return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CloudConvert Integration")
    parser.add_argument("--info", action="store_true", help="Show account info")
    parser.add_argument("--convert", type=str, help="Convert a local PDF to images")
    parser.add_argument("--url", type=str, help="Convert a PDF from URL to images")
    parser.add_argument("--slides", type=int, default=10, help="Number of slides (for URL conversion)")
    parser.add_argument("--output", type=str, default="/tmp/carousel_images", help="Output directory")

    args = parser.parse_args()

    print("CloudConvert Integration")
    print("=" * 50)

    api_key = Config.get_cloudconvert_api_key()
    print(f"API Key: {'present' if api_key else 'MISSING'}")

    if args.info or (not args.convert and not args.url):
        if api_key:
            info = get_account_info()
            if info:
                print(f"Account: {info.get('username', 'Unknown')}")
                print(f"Credits: {info.get('credits', 'Unknown')}")
            else:
                print("Could not fetch account info")

    if args.convert:
        pdf_path = Path(args.convert)
        output_dir = Path(args.output)
        result = convert_pdf_to_images(pdf_path, output_dir)
        if result:
            print(f"\nConverted {len(result)} images to {output_dir}")
        else:
            print("\nConversion failed")

    if args.url:
        output_dir = Path(args.output)
        result = convert_pdf_url_to_images(args.url, output_dir, args.slides)
        if result:
            print(f"\nConverted {len(result)} images to {output_dir}")
        else:
            print("\nConversion failed")
