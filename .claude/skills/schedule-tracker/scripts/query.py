#!/usr/bin/env python3
"""
Query the schedule.json database.

Usage:
    python query.py --status scheduled
    python query.py --platform twitter
    python query.py --pillar "Deep Agent Architecture"
    python query.py --after 2026-01-01 --before 2026-01-31
    python query.py --id "post-id-here"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCHEDULE_FILE = Path.home() / "Dropbox/Agents/Ruby/.claude/memory/schedule.json"


def load_schedule() -> dict:
    """Load the schedule.json file."""
    if not SCHEDULE_FILE.exists():
        print(f"Error: Schedule file not found: {SCHEDULE_FILE}")
        sys.exit(1)

    with open(SCHEDULE_FILE) as f:
        return json.load(f)


def parse_date(date_str: str) -> datetime:
    """Parse various date formats."""
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: {date_str}")


def filter_posts(
    posts: list,
    status: str = None,
    platform: str = None,
    pillar: str = None,
    hook_type: str = None,
    after: str = None,
    before: str = None,
    post_id: str = None
) -> list:
    """Filter posts by various criteria."""

    results = posts

    if post_id:
        results = [p for p in results if p.get("id") == post_id]
        return results

    if status:
        results = [p for p in results if p.get("status") == status]

    if platform:
        results = [p for p in results
                   if platform.lower() in [pl.lower() for pl in p.get("platforms", [])]]

    if pillar:
        results = [p for p in results
                   if pillar.lower() in p.get("content_pillar", "").lower()]

    if hook_type:
        results = [p for p in results if p.get("hook_type") == hook_type]

    if after:
        after_date = parse_date(after)
        filtered = []
        for p in results:
            time_field = p.get("scheduled_time") or p.get("posted_time") or p.get("created_at")
            if time_field:
                try:
                    post_date = parse_date(time_field[:19])  # Truncate timezone
                    if post_date >= after_date.replace(tzinfo=None):
                        filtered.append(p)
                except:
                    filtered.append(p)  # Include if can't parse
        results = filtered

    if before:
        before_date = parse_date(before)
        filtered = []
        for p in results:
            time_field = p.get("scheduled_time") or p.get("posted_time") or p.get("created_at")
            if time_field:
                try:
                    post_date = parse_date(time_field[:19])
                    if post_date <= before_date.replace(tzinfo=None):
                        filtered.append(p)
                except:
                    filtered.append(p)
        results = filtered

    return results


def format_post(post: dict, verbose: bool = False) -> str:
    """Format a post for display."""
    lines = []

    # Header
    status_emoji = {
        "scheduled": "📅",
        "posted": "✅",
        "failed": "❌",
        "canceled": "🚫",
        "unverified": "❓"
    }.get(post.get("status", ""), "❓")

    lines.append(f"{status_emoji} [{post.get('id', 'no-id')}]")
    lines.append(f"   Status: {post.get('status', 'unknown')}")
    lines.append(f"   Platforms: {', '.join(post.get('platforms', []))}")

    time_field = post.get("scheduled_time") or post.get("posted_time")
    if time_field:
        lines.append(f"   Time: {time_field}")

    if post.get("content_pillar"):
        lines.append(f"   Pillar: {post.get('content_pillar')}")

    if post.get("hook_type"):
        lines.append(f"   Hook: {post.get('hook_type')}")

    if verbose:
        content = post.get("content_text", "")[:100]
        if len(post.get("content_text", "")) > 100:
            content += "..."
        lines.append(f"   Content: {content}")

        if post.get("media_url"):
            lines.append(f"   Media: {post.get('media_url')}")

        if post.get("notes"):
            lines.append(f"   Notes: {post.get('notes')}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Query schedule.json")

    parser.add_argument("--status", "-s",
                        choices=["scheduled", "posted", "failed", "canceled", "unverified"],
                        help="Filter by status")
    parser.add_argument("--platform", "-p",
                        help="Filter by platform")
    parser.add_argument("--pillar",
                        help="Filter by content pillar")
    parser.add_argument("--hook",
                        choices=["scary", "strange", "sexy", "free_value", "familiar"],
                        help="Filter by hook type")
    parser.add_argument("--after",
                        help="Posts after date (YYYY-MM-DD)")
    parser.add_argument("--before",
                        help="Posts before date (YYYY-MM-DD)")
    parser.add_argument("--id",
                        help="Get specific post by ID")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show full post details")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--stats", action="store_true",
                        help="Show posting statistics")

    args = parser.parse_args()

    data = load_schedule()
    posts = data.get("scheduled_posts", [])

    # Show stats if requested
    if args.stats:
        print("=== Posting Stats ===")
        stats = data.get("posting_stats", {})
        print(f"Period: {stats.get('period', 'N/A')}")
        print("\nVerified posts:")
        for platform, count in stats.get("verified_posts", {}).items():
            print(f"  {platform}: {count}")
        print("\nTargets per week:")
        for platform, target in stats.get("targets_per_week", {}).items():
            print(f"  {platform}: {target}")
        return

    # Filter posts
    results = filter_posts(
        posts,
        status=args.status,
        platform=args.platform,
        pillar=args.pillar,
        hook_type=args.hook,
        after=args.after,
        before=args.before,
        post_id=args.id
    )

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"Found {len(results)} post(s)\n")
        for post in results:
            print(format_post(post, verbose=args.verbose))
            print()


if __name__ == "__main__":
    main()
