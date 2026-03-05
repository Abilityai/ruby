#!/usr/bin/env python3
"""
Post content to social media via Blotato API.

Usage:
    python post.py --platform twitter --text "Your post content"
    python post.py --platform tiktok --text "Caption" --media "https://..."
    python post.py --platform linkedin --text "Content" --schedule "2026-01-26T08:00:00-08:00"
"""

import argparse
import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path


# Load environment
def load_env():
    env_paths = [
        Path(".env"),
        Path.home() / "Dropbox/Agents/Ruby/.env"
    ]

    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key, value)
            break


load_env()

# Configuration
API_BASE = "https://api.blotato.com/v1"
API_KEY = os.environ.get("BLOTATO_API_KEY")

ACCOUNT_IDS = {
    "youtube": "${BLOTATO_YOUTUBE_ID}",
    "instagram": "${BLOTATO_INSTAGRAM_ID}",
    "linkedin": "${BLOTATO_LINKEDIN_ID}",
    "twitter": "${BLOTATO_TWITTER_ID}",
    "threads": "${BLOTATO_THREADS_ID}",
    "tiktok": "${BLOTATO_TIKTOK_ID}",
    "facebook": "${BLOTATO_INSTAGRAM_ID}",  # Same as Instagram for Meta
}


def post_content(
    platform: str,
    text: str,
    media_url: str = None,
    media_urls: list = None,
    schedule_time: str = None,
    post_type: str = None
) -> dict:
    """Post content to a platform via Blotato."""

    if not API_KEY:
        print("Error: BLOTATO_API_KEY not found in environment")
        sys.exit(1)

    account_id = ACCOUNT_IDS.get(platform.lower())
    if not account_id:
        print(f"Error: Unknown platform: {platform}")
        print(f"Available: {', '.join(ACCOUNT_IDS.keys())}")
        sys.exit(1)

    # Determine post type
    if not post_type:
        if media_urls and len(media_urls) > 1:
            post_type = "carousel"
        elif media_url or media_urls:
            # Check if video or image based on extension
            url = media_url or media_urls[0]
            if any(ext in url.lower() for ext in ['.mp4', '.mov', '.avi', '.webm']):
                post_type = "video"
            else:
                post_type = "image"
        else:
            post_type = "text"

    # Build payload
    payload = {
        "account_id": account_id,
        "content": text,
        "post_type": post_type
    }

    if media_url:
        payload["media_urls"] = [media_url]
    elif media_urls:
        payload["media_urls"] = media_urls

    if schedule_time:
        payload["scheduled_at"] = schedule_time

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    print(f"Posting to {platform}...")
    print(f"Account ID: {account_id}")
    print(f"Post type: {post_type}")
    if schedule_time:
        print(f"Scheduled for: {schedule_time}")

    response = requests.post(
        f"{API_BASE}/posts",
        headers=headers,
        json=payload
    )

    if response.status_code == 200 or response.status_code == 201:
        result = response.json()
        print(f"Success!")
        print(f"Post ID: {result.get('id', 'N/A')}")
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return {"error": response.text, "status_code": response.status_code}


def post_thread(platform: str, tweets: list, schedule_time: str = None) -> dict:
    """Post a thread to Twitter."""

    if platform.lower() != "twitter":
        print("Error: Threads are only supported on Twitter")
        sys.exit(1)

    account_id = ACCOUNT_IDS["twitter"]

    payload = {
        "account_id": account_id,
        "content": tweets,
        "post_type": "thread"
    }

    if schedule_time:
        payload["scheduled_at"] = schedule_time

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    print(f"Posting thread ({len(tweets)} tweets)...")

    response = requests.post(
        f"{API_BASE}/posts",
        headers=headers,
        json=payload
    )

    if response.status_code in [200, 201]:
        result = response.json()
        print(f"Thread posted successfully!")
        print(f"Post ID: {result.get('id', 'N/A')}")
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return {"error": response.text}


def main():
    parser = argparse.ArgumentParser(description="Post to social media via Blotato")

    parser.add_argument("--platform", "-p", required=True,
                        choices=list(ACCOUNT_IDS.keys()),
                        help="Target platform")
    parser.add_argument("--text", "-t", required=True,
                        help="Post content (or comma-separated for threads)")
    parser.add_argument("--media", "-m",
                        help="Media URL (image or video)")
    parser.add_argument("--media-urls", nargs="+",
                        help="Multiple media URLs (for carousels)")
    parser.add_argument("--schedule", "-s",
                        help="Schedule time (ISO 8601 format)")
    parser.add_argument("--type",
                        choices=["text", "image", "video", "carousel", "thread"],
                        help="Post type (auto-detected if not specified)")
    parser.add_argument("--thread", action="store_true",
                        help="Post as a thread (use | to separate tweets)")

    args = parser.parse_args()

    # Handle thread posting
    if args.thread or args.type == "thread":
        tweets = [t.strip() for t in args.text.split("|")]
        result = post_thread(args.platform, tweets, args.schedule)
    else:
        result = post_content(
            platform=args.platform,
            text=args.text,
            media_url=args.media,
            media_urls=args.media_urls,
            schedule_time=args.schedule,
            post_type=args.type
        )

    # Output JSON for scripting
    print("\n--- Response ---")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
