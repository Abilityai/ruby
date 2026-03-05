#!/usr/bin/env python3
"""
Update the status of a post in schedule.json.

Usage:
    python update_status.py --id "post-id" --status posted
    python update_status.py --id "post-id" --status posted --blotato-id "123"
    python update_status.py --id "post-id" --status failed --notes "API error"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCHEDULE_FILE = Path.home() / "Dropbox/Agents/Ruby/.claude/memory/schedule.json"

STATUSES = ["scheduled", "posted", "failed", "canceled", "unverified"]


def load_schedule() -> dict:
    if not SCHEDULE_FILE.exists():
        print(f"Error: Schedule file not found: {SCHEDULE_FILE}")
        sys.exit(1)

    with open(SCHEDULE_FILE) as f:
        return json.load(f)


def save_schedule(data: dict):
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Update post status in schedule.json")

    parser.add_argument("--id", required=True,
                        help="Post ID to update")
    parser.add_argument("--status", "-s",
                        choices=STATUSES,
                        help="New status")
    parser.add_argument("--blotato-id",
                        help="Blotato post ID (for tracking)")
    parser.add_argument("--metricool-id",
                        help="Metricool post ID")
    parser.add_argument("--posted-time",
                        help="Actual posted time (ISO 8601)")
    parser.add_argument("--notes",
                        help="Add notes to the post")
    parser.add_argument("--url",
                        help="URL of the published post")

    args = parser.parse_args()

    data = load_schedule()
    posts = data.get("scheduled_posts", [])

    # Find post
    post_index = None
    for i, post in enumerate(posts):
        if post.get("id") == args.id:
            post_index = i
            break

    if post_index is None:
        print(f"Error: Post not found: {args.id}")
        sys.exit(1)

    post = posts[post_index]
    now = datetime.utcnow().isoformat() + "Z"

    # Update fields
    if args.status:
        old_status = post.get("status")
        post["status"] = args.status
        print(f"Status: {old_status} -> {args.status}")

        # If marking as posted, set posted_time
        if args.status == "posted" and not post.get("posted_time"):
            post["posted_time"] = args.posted_time or now

    if args.posted_time:
        post["posted_time"] = args.posted_time

    if args.blotato_id:
        post["blotato_ids"] = post.get("blotato_ids", {})
        # Add to all platforms
        for platform in post.get("platforms", []):
            post["blotato_ids"][platform] = args.blotato_id

    if args.metricool_id:
        post["metricool_ids"] = post.get("metricool_ids", {})
        for platform in post.get("platforms", []):
            post["metricool_ids"][platform] = args.metricool_id

    if args.notes:
        existing_notes = post.get("notes", "")
        if existing_notes:
            post["notes"] = f"{existing_notes}; {args.notes}"
        else:
            post["notes"] = args.notes

    if args.url:
        # Determine URL field based on platform
        platforms = post.get("platforms", [])
        if "youtube" in platforms:
            post["youtube_url"] = args.url
        elif "twitter" in platforms:
            post["twitter_url"] = args.url
        elif "linkedin" in platforms:
            post["linkedin_url"] = args.url
        elif "tiktok" in platforms:
            post["tiktok_url"] = args.url
        else:
            post["url"] = args.url

    post["updated_at"] = now

    # Save
    data["scheduled_posts"][post_index] = post
    data["metadata"] = data.get("metadata", {})
    data["metadata"]["last_updated"] = now

    save_schedule(data)

    print(f"Updated post: {args.id}")
    print(f"Updated at: {now}")


if __name__ == "__main__":
    main()
