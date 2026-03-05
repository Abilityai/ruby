"""
YouTube Thumbnail Generator.

Generates 15 YouTube thumbnail images from a video transcript using:
1. Gemini to generate 15 thumbnail prompts
2. Gemini Image API to generate images with reference photos
3. Google Drive upload to Thumbnails folder

Aspect ratio: 16:9 (YouTube standard)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directories to path
_parent = Path(__file__).parent.parent
sys.path.insert(0, str(_parent))
sys.path.insert(0, str(_parent / "utils"))

from config import Config

# Import base module (handle both relative and absolute imports)
try:
    from .base import load_template
except ImportError:
    from base import load_template

# Import Gemini Image utilities
from gemini_image import (
    download_reference_photos,
    generate_prompts,
    generate_image,
    save_image,
    upload_to_google_drive,
    create_google_drive_folder,
)

# Import guest utilities
try:
    from utils.guests import load_guests, find_guest_photos, format_guest_summary
except ImportError:
    from guests import load_guests, find_guest_photos, format_guest_summary


# Constants
TEMPLATE_FILES = {
    "solo": "youtube_thumbnail.md",
    "podcast": "youtube_thumbnail_podcast.md",
}
DEFAULT_MODE = "solo"
ASPECT_RATIO = "16:9"
NUM_THUMBNAILS = 15


def generate_thumbnails(
    transcript_path: Path,
    output_dir: Path,
    folder_id: Optional[str] = None,
    custom_title: Optional[str] = None,
    upload_to_drive: bool = True,
    rate_limit_delay: float = 2.0,
    mode: str = DEFAULT_MODE,
    guest_photos_path: Optional[Path] = None,
) -> dict:
    """
    Generate YouTube thumbnails from a video transcript.

    Args:
        transcript_path: Path to transcript.md
        output_dir: Local directory to save thumbnails
        folder_id: Google Drive folder ID to upload to (parent folder)
        custom_title: Optional custom title for thumbnails
        upload_to_drive: Whether to upload to Google Drive
        rate_limit_delay: Delay between image generations (seconds)
        mode: "solo" (single person) or "podcast" (two people talking)
        guest_photos_path: Path to guest reference photos (required for podcast mode)

    Returns:
        Result dictionary with status, paths, and statistics
    """
    result = {
        "success": False,
        "prompts_generated": 0,
        "images_generated": 0,
        "images_uploaded": 0,
        "local_paths": [],
        "drive_folder_id": None,
        "drive_folder_url": None,
        "errors": [],
    }

    # Validate transcript exists
    if not transcript_path.exists():
        result["errors"].append(f"Transcript not found: {transcript_path}")
        return result

    # Load transcript
    print(f"Loading transcript from {transcript_path}...")
    transcript = transcript_path.read_text()
    if not transcript.strip():
        result["errors"].append("Transcript is empty")
        return result

    # Load template based on mode
    template_file = TEMPLATE_FILES.get(mode, TEMPLATE_FILES[DEFAULT_MODE])
    print(f"Loading template: {template_file} (mode: {mode})")
    prompt_template = load_template(template_file)
    if not prompt_template:
        result["errors"].append(f"Could not load template: {template_file}")
        return result

    # Download host reference photos (creator)
    print("Downloading reference photos...")
    host_photos = download_reference_photos(max_photos=6)
    if not host_photos:
        result["errors"].append("No host reference photos available")
        return result
    print(f"  Using {len(host_photos)} host reference photos")

    # For podcast mode, also load guest reference photos
    guest_photos = []
    guests = []
    if mode == "podcast":
        # First, try to load from guests.md
        folder_path = transcript_path.parent
        guests_file = folder_path / "guests.md"

        if guests_file.exists() and not guest_photos_path:
            # Load guests from guests.md
            guests = load_guests(str(folder_path))
            if guests:
                print(f"  Found guests.md with {len(guests)} guest(s)")
                # Find photos for each guest
                for guest in guests:
                    if guest.get("photos"):
                        photos = find_guest_photos(str(folder_path), guest["photos"])
                        guest_photos.extend(photos)
                if not guest_photos:
                    # Fallback: look for any images in folder
                    for ext in ["*.jpg", "*.jpeg", "*.png"]:
                        guest_photos.extend(folder_path.glob(ext))
                    guest_photos = [p for p in guest_photos if "thumbnail" not in p.name.lower()]
                    guest_photos = sorted(guest_photos)[:6]

        # If no guests.md or no photos found, try --guest-photos argument
        if not guest_photos and guest_photos_path:
            guest_photos_path = Path(guest_photos_path)
            if guest_photos_path.is_dir():
                # Load all images from directory
                guest_photos = list(guest_photos_path.glob("*.png")) + \
                              list(guest_photos_path.glob("*.jpg")) + \
                              list(guest_photos_path.glob("*.jpeg"))
                guest_photos = sorted(guest_photos)[:6]  # Max 6 guest photos
            elif guest_photos_path.is_file():
                # Single image file
                guest_photos = [guest_photos_path]

        if not guest_photos:
            result["errors"].append("Podcast mode requires guests.md or --guest-photos argument")
            return result
        print(f"  Using {len(guest_photos)} guest reference photos")

    # Combine photos: host first, then guest
    # The prompt template will reference "first set" for host, "second set" for guest
    reference_photos = host_photos + guest_photos

    # Generate prompts
    print(f"Generating {NUM_THUMBNAILS} thumbnail prompts...")
    prompts = generate_prompts(
        transcript=transcript,
        prompt_template=prompt_template,
        custom_title=custom_title,
        num_prompts=NUM_THUMBNAILS,
    )

    if not prompts:
        result["errors"].append("Failed to generate prompts")
        return result

    result["prompts_generated"] = len(prompts)
    print(f"  Generated {len(prompts)} prompts")

    # Create local output directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M")
    thumbnails_dir = output_dir / f"Thumbnails_{timestamp}"
    thumbnails_dir.mkdir(parents=True, exist_ok=True)

    # Create Google Drive folder if uploading
    drive_folder_id = None
    if upload_to_drive and folder_id:
        print(f"Creating Google Drive folder...")
        drive_folder_id = create_google_drive_folder(f"Thumbnails_{timestamp}", folder_id)
        if drive_folder_id:
            result["drive_folder_id"] = drive_folder_id
            result["drive_folder_url"] = f"https://drive.google.com/drive/folders/{drive_folder_id}"
            print(f"  Created folder: {result['drive_folder_url']}")
        else:
            print("  Warning: Could not create Google Drive folder")

    # Generate images
    print(f"\nGenerating {len(prompts)} thumbnail images...")
    import time

    for i, prompt in enumerate(prompts, 1):
        print(f"\n  [{i}/{len(prompts)}] Generating thumbnail...")

        # Generate image
        image_data = generate_image(
            prompt=prompt,
            reference_photos=reference_photos,
            aspect_ratio=ASPECT_RATIO,
        )

        if not image_data:
            error_msg = f"Failed to generate thumbnail {i}"
            print(f"    Error: {error_msg}")
            result["errors"].append(error_msg)
            continue

        # Save locally
        local_path = thumbnails_dir / f"thumbnail_{i:02d}.png"
        if save_image(image_data, local_path):
            result["images_generated"] += 1
            result["local_paths"].append(str(local_path))
            print(f"    Saved: {local_path.name}")

            # Upload to Google Drive
            if upload_to_drive and drive_folder_id:
                file_id = upload_to_google_drive(local_path, drive_folder_id)
                if file_id:
                    result["images_uploaded"] += 1
                    print(f"    Uploaded to Drive")
                else:
                    print(f"    Warning: Upload failed")
        else:
            result["errors"].append(f"Failed to save thumbnail {i}")

        # Rate limiting between generations
        if i < len(prompts):
            time.sleep(rate_limit_delay)

    # Determine success
    result["success"] = result["images_generated"] > 0

    # Summary
    print(f"\n{'='*50}")
    print(f"Thumbnail Generation Complete")
    print(f"{'='*50}")
    print(f"  Prompts generated: {result['prompts_generated']}")
    print(f"  Images generated:  {result['images_generated']}/{len(prompts)}")
    if upload_to_drive:
        print(f"  Images uploaded:   {result['images_uploaded']}")
    print(f"  Local folder:      {thumbnails_dir}")
    if result["drive_folder_url"]:
        print(f"  Drive folder:      {result['drive_folder_url']}")
    if result["errors"]:
        print(f"  Errors: {len(result['errors'])}")

    # Save prompts for reference
    prompts_file = thumbnails_dir / "_prompts.json"
    with open(prompts_file, "w") as f:
        json.dump(prompts, f, indent=2)

    return result


def run_from_cli(args):
    """
    Run thumbnail generation from command line arguments.

    Args:
        args: Parsed argparse arguments
    """
    folder_path = Path(args.path)

    # Find transcript
    transcript_path = folder_path / "transcript.md"
    if not transcript_path.exists():
        print(f"Error: transcript.md not found in {folder_path}")
        sys.exit(1)

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    elif Config.is_test_mode():
        output_dir = Path(Config.get_test_output_dir())
    else:
        output_dir = folder_path

    # Get folder ID for Google Drive upload
    folder_id = args.folder_id if hasattr(args, 'folder_id') and args.folder_id else None

    # Check podcast mode requirements
    mode = args.mode if hasattr(args, 'mode') else DEFAULT_MODE
    guest_photos_path = Path(args.guest_photos) if hasattr(args, 'guest_photos') and args.guest_photos else None

    if mode == "podcast" and not guest_photos_path:
        print("Error: Podcast mode requires --guest-photos argument")
        print("Usage: --mode podcast --guest-photos /path/to/guest/photos")
        sys.exit(1)

    # Run generation
    result = generate_thumbnails(
        transcript_path=transcript_path,
        output_dir=output_dir,
        folder_id=folder_id,
        custom_title=args.title if hasattr(args, 'title') else None,
        upload_to_drive=not args.no_upload if hasattr(args, 'no_upload') else True,
        mode=mode,
        guest_photos_path=guest_photos_path,
    )

    if result["success"]:
        print("\nThumbnail generation completed successfully!")
        sys.exit(0)
    else:
        print("\nThumbnail generation failed.")
        for error in result["errors"]:
            print(f"  - {error}")
        sys.exit(1)


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate YouTube thumbnails from video transcript")
    parser.add_argument("path", type=str, help="Path to folder containing transcript.md")
    parser.add_argument("--mode", type=str, choices=["solo", "podcast"], default="solo",
                       help="Thumbnail mode: 'solo' (single person) or 'podcast' (two people)")
    parser.add_argument("--guest-photos", type=str,
                       help="Path to guest reference photos (required for podcast mode). Can be a directory or single image.")
    parser.add_argument("--title", type=str, help="Custom title for thumbnails")
    parser.add_argument("--output", type=str, help="Output directory (default: same as input)")
    parser.add_argument("--folder-id", type=str, help="Google Drive folder ID for upload")
    parser.add_argument("--no-upload", action="store_true", help="Skip Google Drive upload")

    args = parser.parse_args()
    run_from_cli(args)
