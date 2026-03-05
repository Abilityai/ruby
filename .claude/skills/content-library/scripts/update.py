#!/usr/bin/env python3
"""
Content Library Update Tool

Add and update content in the library.

Usage:
    python3 update.py add-article --id ID --title "Title" [--status STATUS] [--pillars P1,P2]
    python3 update.py add-youtube --id ID --title "Title" --url URL [--date DATE]
    python3 update.py set-status --id ID --status STATUS
    python3 update.py publish --id ID --platform PLATFORM --url URL
    python3 update.py increment-repurpose --id ID --type TYPE
"""

import sys
import yaml
import argparse
from pathlib import Path
from datetime import datetime

LIBRARY_PATH = Path.home() / "Dropbox/Agents/Ruby/.claude/memory/content_library.yaml"


def load_library():
    """Load the content library YAML file."""
    if not LIBRARY_PATH.exists():
        return {"articles": [], "youtube": [], "metadata": {}}
    with open(LIBRARY_PATH, "r") as f:
        return yaml.safe_load(f) or {"articles": [], "youtube": [], "metadata": {}}


def save_library(data):
    """Save the content library YAML file."""
    data["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    data["metadata"]["updated_by"] = "Ruby"
    with open(LIBRARY_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(f"Updated: {LIBRARY_PATH}")


def add_article(args):
    """Add a new article to the library."""
    data = load_library()

    if data.get("articles") is None:
        data["articles"] = []

    # Check for duplicate
    for a in data["articles"]:
        if a.get("id") == args.id:
            print(f"Error: Article with ID '{args.id}' already exists")
            return

    pillars = args.pillars.split(",") if args.pillars else []
    platforms = args.platforms.split(",") if args.platforms else []

    article = {
        "id": args.id,
        "title": args.title,
        "status": args.status or "draft",
        "drive_path": f"Articles/drafts/{args.id}",
        "created": datetime.now().strftime("%Y-%m-%d"),
        "pillars": pillars,
        "target_platforms": platforms,
        "published": {},
        "notes": args.notes or "",
    }

    data["articles"].append(article)
    save_library(data)
    print(f"Added article: {args.title}")


def add_youtube(args):
    """Add a new YouTube video to the library."""
    data = load_library()

    if data.get("youtube") is None:
        data["youtube"] = []

    # Check for duplicate
    for v in data["youtube"]:
        if v.get("id") == args.id:
            print(f"Error: Video with ID '{args.id}' already exists")
            return

    pillars = args.pillars.split(",") if args.pillars else []

    video = {
        "id": args.id,
        "title": args.title,
        "status": "published",
        "drive_path": args.drive_path or f"Content/{datetime.now().strftime('%m.%Y')}/{args.id}",
        "published_date": args.date or datetime.now().strftime("%Y-%m-%d"),
        "youtube_url": args.url,
        "pillars": pillars,
        "repurposed": {
            "twitter_threads": 0,
            "linkedin_posts": 0,
            "newsletters": 0,
            "shorts": 0,
        },
        "notes": args.notes or "",
    }

    data["youtube"].append(video)
    save_library(data)
    print(f"Added YouTube video: {args.title}")


def set_status(args):
    """Update the status of content."""
    data = load_library()

    valid_statuses = ["idea", "draft", "review", "approved", "published"]
    if args.status not in valid_statuses:
        print(f"Error: Invalid status '{args.status}'. Valid: {', '.join(valid_statuses)}")
        return

    # Check articles
    for a in data.get("articles", []):
        if a.get("id") == args.id:
            old_status = a.get("status")
            a["status"] = args.status

            # Update drive_path if moving to published
            if args.status == "published" and "drafts" in a.get("drive_path", ""):
                a["drive_path"] = a["drive_path"].replace("drafts", "published")

            save_library(data)
            print(f"Updated '{a['title']}': {old_status} -> {args.status}")
            return

    print(f"Content not found: {args.id}")


def publish(args):
    """Mark content as published to a platform."""
    data = load_library()

    for a in data.get("articles", []):
        if a.get("id") == args.id:
            if "published" not in a:
                a["published"] = {}

            a["published"][args.platform] = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "url": args.url,
            }

            # Check if all target platforms are done
            target = set(a.get("target_platforms", []))
            published = set(a.get("published", {}).keys())
            if target and target.issubset(published):
                a["status"] = "published"
                if "drafts" in a.get("drive_path", ""):
                    a["drive_path"] = a["drive_path"].replace("drafts", "published")
                print(f"All platforms published! Status updated to 'published'")

            save_library(data)
            print(f"Marked '{a['title']}' as published to {args.platform}")
            return

    print(f"Article not found: {args.id}")


def increment_repurpose(args):
    """Increment repurposing counter for a YouTube video."""
    data = load_library()

    valid_types = ["twitter_threads", "linkedin_posts", "newsletters", "shorts"]
    if args.type not in valid_types:
        print(f"Error: Invalid type '{args.type}'. Valid: {', '.join(valid_types)}")
        return

    for v in data.get("youtube", []):
        if v.get("id") == args.id:
            if "repurposed" not in v:
                v["repurposed"] = {t: 0 for t in valid_types}

            v["repurposed"][args.type] = v["repurposed"].get(args.type, 0) + 1

            save_library(data)
            print(f"Incremented {args.type} for '{v['title']}': now {v['repurposed'][args.type]}")
            return

    print(f"Video not found: {args.id}")


def main():
    parser = argparse.ArgumentParser(description="Content Library Update Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add-article
    p_add_article = subparsers.add_parser("add-article")
    p_add_article.add_argument("--id", required=True)
    p_add_article.add_argument("--title", required=True)
    p_add_article.add_argument("--status", default="draft")
    p_add_article.add_argument("--pillars", help="Comma-separated pillars")
    p_add_article.add_argument("--platforms", help="Comma-separated target platforms")
    p_add_article.add_argument("--notes", default="")

    # add-youtube
    p_add_youtube = subparsers.add_parser("add-youtube")
    p_add_youtube.add_argument("--id", required=True)
    p_add_youtube.add_argument("--title", required=True)
    p_add_youtube.add_argument("--url", required=True)
    p_add_youtube.add_argument("--date")
    p_add_youtube.add_argument("--drive-path")
    p_add_youtube.add_argument("--pillars", help="Comma-separated pillars")
    p_add_youtube.add_argument("--notes", default="")

    # set-status
    p_status = subparsers.add_parser("set-status")
    p_status.add_argument("--id", required=True)
    p_status.add_argument("--status", required=True)

    # publish
    p_publish = subparsers.add_parser("publish")
    p_publish.add_argument("--id", required=True)
    p_publish.add_argument("--platform", required=True)
    p_publish.add_argument("--url", required=True)

    # increment-repurpose
    p_repurpose = subparsers.add_parser("increment-repurpose")
    p_repurpose.add_argument("--id", required=True)
    p_repurpose.add_argument("--type", required=True)

    args = parser.parse_args()

    if args.command == "add-article":
        add_article(args)
    elif args.command == "add-youtube":
        add_youtube(args)
    elif args.command == "set-status":
        set_status(args)
    elif args.command == "publish":
        publish(args)
    elif args.command == "increment-repurpose":
        increment_repurpose(args)


if __name__ == "__main__":
    main()
