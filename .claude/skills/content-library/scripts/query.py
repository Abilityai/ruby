#!/usr/bin/env python3
"""
Content Library Query Tool

Query and update the content library YAML file.

Usage:
    python3 query.py status              # Show content needing attention
    python3 query.py articles [status]   # List articles, optionally by status
    python3 query.py youtube             # List YouTube videos
    python3 query.py get <id>            # Get specific content by ID
    python3 query.py needs-review        # Articles waiting for review
    python3 query.py needs-repurposing   # Videos needing repurposing
"""

import sys
import yaml
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


def show_status():
    """Show content needing attention."""
    data = load_library()

    # Articles needing review
    review = [a for a in (data.get("articles") or []) if a.get("status") == "review"]
    approved = [a for a in (data.get("articles") or []) if a.get("status") == "approved"]
    drafts = [a for a in (data.get("articles") or []) if a.get("status") == "draft"]

    # Videos needing repurposing (less than 3 pieces)
    needs_repurpose = []
    for v in (data.get("youtube") or []):
        repurposed = v.get("repurposed", {})
        total = sum(repurposed.values()) if isinstance(repurposed, dict) else 0
        if total < 3:
            needs_repurpose.append((v, total))

    print("=" * 50)
    print("CONTENT LIBRARY STATUS")
    print("=" * 50)

    print(f"\n## Articles Needing Review: {len(review)}")
    for a in review:
        print(f"  - {a['title']} (created: {a.get('created', 'unknown')})")

    print(f"\n## Articles Ready to Publish: {len(approved)}")
    for a in approved:
        platforms = ", ".join(a.get("target_platforms", []))
        print(f"  - {a['title']} -> {platforms}")

    print(f"\n## Articles in Draft: {len(drafts)}")
    for a in drafts:
        print(f"  - {a['title']}")

    print(f"\n## Videos Needing Repurposing: {len(needs_repurpose)}")
    for v, count in needs_repurpose:
        print(f"  - {v['title']} ({count} pieces so far)")

    print()


def list_articles(status_filter=None):
    """List all articles, optionally filtered by status."""
    data = load_library()
    articles = data.get("articles") or []

    if status_filter:
        articles = [a for a in articles if a.get("status") == status_filter]

    if not articles:
        print(f"No articles found" + (f" with status '{status_filter}'" if status_filter else ""))
        return

    print(f"\n## Articles" + (f" (status: {status_filter})" if status_filter else "") + f": {len(articles)}")
    print("-" * 40)

    for a in articles:
        status = a.get("status", "unknown")
        title = a.get("title", "Untitled")
        created = a.get("created", "unknown")
        published = a.get("published", {})
        pub_count = len([p for p in published.values() if p])
        target_count = len(a.get("target_platforms", []))

        print(f"\nID: {a.get('id', 'no-id')}")
        print(f"Title: {title}")
        print(f"Status: {status}")
        print(f"Created: {created}")
        if target_count > 0:
            print(f"Published: {pub_count}/{target_count} platforms")
    print()


def list_youtube():
    """List all YouTube videos with repurposing stats."""
    data = load_library()
    videos = data.get("youtube") or []

    if not videos:
        print("No YouTube videos tracked")
        return

    print(f"\n## YouTube Videos: {len(videos)}")
    print("-" * 40)

    for v in videos:
        title = v.get("title", "Untitled")
        url = v.get("youtube_url", "no URL")
        published = v.get("published_date", "unknown")
        repurposed = v.get("repurposed", {})

        print(f"\nID: {v.get('id', 'no-id')}")
        print(f"Title: {title}")
        print(f"Published: {published}")
        print(f"URL: {url}")
        print("Repurposed:")
        for content_type, count in repurposed.items():
            print(f"  - {content_type}: {count}")
    print()


def get_content(content_id):
    """Get specific content by ID."""
    data = load_library()

    # Check articles
    for a in (data.get("articles") or []):
        if a.get("id") == content_id:
            print("\n## Article")
            print(yaml.dump(a, default_flow_style=False))
            return

    # Check youtube
    for v in (data.get("youtube") or []):
        if v.get("id") == content_id:
            print("\n## YouTube Video")
            print(yaml.dump(v, default_flow_style=False))
            return

    print(f"Content not found: {content_id}")


def needs_review():
    """Show articles needing review."""
    list_articles("review")


def needs_repurposing():
    """Show videos needing repurposing."""
    data = load_library()

    needs_repurpose = []
    for v in (data.get("youtube") or []):
        repurposed = v.get("repurposed", {})
        total = sum(repurposed.values()) if isinstance(repurposed, dict) else 0
        if total < 5:  # Threshold for "needs repurposing"
            needs_repurpose.append((v, total))

    if not needs_repurpose:
        print("All videos have been sufficiently repurposed!")
        return

    print(f"\n## Videos Needing Repurposing: {len(needs_repurpose)}")
    print("-" * 40)

    for v, count in sorted(needs_repurpose, key=lambda x: x[1]):
        print(f"\n{v['title']}")
        print(f"  URL: {v.get('youtube_url', 'no URL')}")
        print(f"  Repurposed pieces: {count}")
        repurposed = v.get("repurposed", {})
        for content_type, c in repurposed.items():
            if c == 0:
                print(f"  - {content_type}: NONE")
    print()


def main():
    if len(sys.argv) < 2:
        show_status()
        return

    command = sys.argv[1]

    if command == "status":
        show_status()
    elif command == "articles":
        status_filter = sys.argv[2] if len(sys.argv) > 2 else None
        list_articles(status_filter)
    elif command == "youtube":
        list_youtube()
    elif command == "get" and len(sys.argv) > 2:
        get_content(sys.argv[2])
    elif command == "needs-review":
        needs_review()
    elif command == "needs-repurposing":
        needs_repurposing()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
