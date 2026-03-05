#!/usr/bin/env python3
"""
Add a new post to schedule.json.

Usage:
    python add_post.py --platform twitter --text "Content" --time "2026-01-26T10:00:00-08:00"
    python add_post.py --platform linkedin --text "Content" --pillar "Deep Agent Architecture" --hook strange
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCHEDULE_FILE = Path.home() / "Dropbox/Agents/Ruby/.claude/memory/schedule.json"

PLATFORMS = ["twitter", "linkedin", "instagram", "tiktok", "youtube", "threads", "bluesky", "facebook"]
CONTENT_TYPES = ["text", "image", "video", "carousel", "thread"]
PILLARS = [
    "Deep Agent Architecture",
    "AI Adoption Psychology",
    "Shallow vs Deep",
    "Production Patterns",
    "Founder Lessons"
]
HOOKS = ["scary", "strange", "sexy", "free_value", "familiar"]


def load_schedule() -> dict:
    """Load the schedule.json file."""
    if not SCHEDULE_FILE.exists():
        return {"scheduled_posts": [], "content_inventory": {}, "posting_stats": {}, "metadata": {}}

    with open(SCHEDULE_FILE) as f:
        return json.load(f)


def save_schedule(data: dict):
    """Save the schedule.json file."""
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def generate_id(text: str, platforms: list, date: str) -> str:
    """Generate a unique post ID."""
    # Extract date part
    date_part = date[:10] if date else datetime.now().strftime("%Y-%m-%d")

    # Create slug from text
    words = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower()).split()[:3]
    slug = "-".join(words) if words else "post"

    # Add platform
    platform = platforms[0] if platforms else "multi"

    return f"{slug}-{platform}-{date_part}"


def main():
    parser = argparse.ArgumentParser(description="Add a post to schedule.json")

    parser.add_argument("--platform", "-p", required=True,
                        help="Platform(s) - comma-separated for multiple")
    parser.add_argument("--text", "-t", required=True,
                        help="Post content")
    parser.add_argument("--time", required=True,
                        help="Scheduled time (ISO 8601)")
    parser.add_argument("--type",
                        choices=CONTENT_TYPES,
                        default="text",
                        help="Content type")
    parser.add_argument("--pillar",
                        help="Content pillar (REQUIRED for tracking)")
    parser.add_argument("--hook",
                        choices=HOOKS,
                        help="Hook type (REQUIRED for tracking)")
    parser.add_argument("--media",
                        help="Media URL")
    parser.add_argument("--media-urls", nargs="+",
                        help="Multiple media URLs")
    parser.add_argument("--youtube-cta",
                        help="YouTube video URL for CTA")
    parser.add_argument("--notes",
                        help="Additional notes")
    parser.add_argument("--id",
                        help="Custom post ID (auto-generated if not provided)")

    args = parser.parse_args()

    # Warn if missing pillar/hook
    if not args.pillar:
        print("WARNING: No content pillar specified. Consider adding --pillar")
    if not args.hook:
        print("WARNING: No hook type specified. Consider adding --hook")

    # Parse platforms
    platforms = [p.strip().lower() for p in args.platform.split(",")]
    for p in platforms:
        if p not in PLATFORMS:
            print(f"Warning: Unknown platform '{p}'")

    # Generate ID
    post_id = args.id or generate_id(args.text, platforms, args.time)

    # Build post entry
    now = datetime.utcnow().isoformat() + "Z"

    post = {
        "id": post_id,
        "created_at": now,
        "scheduled_time": args.time,
        "platforms": platforms,
        "content_type": args.type,
        "content_text": args.text,
        "status": "scheduled",
        "updated_at": now
    }

    if args.pillar:
        post["content_pillar"] = args.pillar
    if args.hook:
        post["hook_type"] = args.hook
    if args.media:
        post["media_url"] = args.media
    if args.media_urls:
        post["media_urls"] = args.media_urls
    if args.youtube_cta:
        post["youtube_cta"] = args.youtube_cta
    if args.notes:
        post["notes"] = args.notes

    # Load, add, save
    data = load_schedule()

    # Check for duplicate ID
    existing_ids = [p.get("id") for p in data.get("scheduled_posts", [])]
    if post_id in existing_ids:
        print(f"Error: Post ID '{post_id}' already exists")
        sys.exit(1)

    data["scheduled_posts"].append(post)

    # Update metadata
    data["metadata"] = data.get("metadata", {})
    data["metadata"]["last_updated"] = now

    save_schedule(data)

    print(f"Post added successfully!")
    print(f"  ID: {post_id}")
    print(f"  Platforms: {', '.join(platforms)}")
    print(f"  Scheduled: {args.time}")
    print(f"  Status: scheduled")


if __name__ == "__main__":
    main()
