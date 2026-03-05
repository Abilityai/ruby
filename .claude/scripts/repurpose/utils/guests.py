"""
Guest profile utilities for podcast mode.

Handles loading and parsing guests.md files.
"""

import re
from pathlib import Path
from typing import Optional


def load_guests(folder_path: str) -> list[dict]:
    """
    Load guest profiles from guests.md in the folder.

    Args:
        folder_path: Path to folder containing guests.md

    Returns:
        List of guest dictionaries with keys:
        - name: Guest name
        - slug: URL-safe identifier
        - twitter: Twitter handle (with @)
        - linkedin: LinkedIn URL or username
        - company: Company name
        - role: Job title/role
        - photos: Glob pattern for reference photos
    """
    folder = Path(folder_path)
    guests_file = folder / "guests.md"

    if not guests_file.exists():
        return []

    content = guests_file.read_text()
    guests = []

    # Split by ## headers (guest sections)
    sections = re.split(r'\n## ', content)

    for section in sections[1:]:  # Skip first section (before first ##)
        lines = section.strip().split('\n')
        if not lines:
            continue

        # First line is the guest name
        name = lines[0].strip()

        guest = {
            "name": name,
            "slug": "",
            "twitter": "",
            "linkedin": "",
            "company": "",
            "role": "",
            "photos": "",
        }

        # Parse key-value pairs
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('- '):
                line = line[2:]
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if key in guest:
                        guest[key] = value

        # Generate slug if not provided
        if not guest["slug"]:
            guest["slug"] = name.lower().replace(' ', '_').replace('-', '_')

        guests.append(guest)

    return guests


def find_guest_photos(folder_path: str, photo_pattern: str) -> list[Path]:
    """
    Find guest reference photos matching a pattern.

    Args:
        folder_path: Base folder path
        photo_pattern: Glob pattern like "guest_photos/mrinal_*.jpg"

    Returns:
        List of photo paths found
    """
    folder = Path(folder_path)

    if not photo_pattern:
        return []

    # Handle relative patterns
    if photo_pattern.startswith('/'):
        pattern_path = Path(photo_pattern)
    else:
        pattern_path = folder / photo_pattern

    # Get parent directory and pattern
    if '*' in photo_pattern:
        parent = pattern_path.parent
        pattern = pattern_path.name
        if parent.exists():
            return sorted(parent.glob(pattern))
    elif pattern_path.exists():
        return [pattern_path]

    # Also check for common photo locations if pattern doesn't match
    common_locations = [
        folder / "guest_photos",
        folder,
    ]

    photos = []
    for loc in common_locations:
        if loc.exists():
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                photos.extend(loc.glob(ext))

    return sorted(set(photos))[:6]  # Max 6 photos


def format_guest_summary(guests: list[dict], folder_path: str = None) -> str:
    """
    Format guest information for display/approval.

    Args:
        guests: List of guest dictionaries
        folder_path: Optional path to check for photos

    Returns:
        Formatted string for display
    """
    if not guests:
        return "No guests found in guests.md"

    lines = ["## Guest Profiles Loaded\n"]

    for i, guest in enumerate(guests, 1):
        lines.append(f"### Guest {i}: {guest['name']}")

        if guest.get('twitter'):
            lines.append(f"- Twitter: {guest['twitter']}")
        if guest.get('linkedin'):
            lines.append(f"- LinkedIn: {guest['linkedin']}")
        if guest.get('company'):
            lines.append(f"- Company: {guest['company']}")
        if guest.get('role'):
            lines.append(f"- Role: {guest['role']}")

        # Count photos if folder provided
        if folder_path and guest.get('photos'):
            photos = find_guest_photos(folder_path, guest['photos'])
            lines.append(f"- Photos: {len(photos)} found")

        lines.append("")

    return "\n".join(lines)


def create_guests_template(folder_path: str, guest_names: list[str] = None) -> str:
    """
    Create a guests.md template file.

    Args:
        folder_path: Path to create the file in
        guest_names: Optional list of guest names to pre-populate

    Returns:
        Path to created file
    """
    folder = Path(folder_path)
    guests_file = folder / "guests.md"

    if guest_names is None:
        guest_names = ["[Guest Name]"]

    sections = ["# Podcast Guests\n"]

    for name in guest_names:
        slug = name.lower().replace(' ', '_').replace('[', '').replace(']', '')
        sections.append(f"""## {name}
- slug: {slug}
- twitter:
- linkedin:
- company:
- role:
- photos: guest_photos/{slug}_*.jpg
""")

    content = "\n".join(sections)
    guests_file.write_text(content)

    return str(guests_file)


def get_guest_attribution(guests: list[dict], platform: str = "generic") -> str:
    """
    Generate attribution text for guests based on platform.

    Args:
        guests: List of guest dictionaries
        platform: Target platform (twitter, linkedin, generic)

    Returns:
        Attribution string
    """
    if not guests:
        return ""

    if platform == "twitter":
        handles = [g['twitter'] for g in guests if g.get('twitter')]
        if handles:
            return " with " + ", ".join(handles)

    elif platform == "linkedin":
        # For LinkedIn, use full names
        names = [g['name'] for g in guests]
        if names:
            return " with " + ", ".join(names)

    else:
        # Generic: prefer names
        names = [g['name'] for g in guests]
        if names:
            return " with " + ", ".join(names)

    return ""
