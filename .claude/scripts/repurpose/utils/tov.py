"""
Tone of Voice (TOV) profile management.

Handles loading TOV profiles from Google Drive with local caching.
Profiles are cached for 24 hours to minimize API calls.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


# Cache TTL in seconds (24 hours)
CACHE_TTL = 86400

# TOV file IDs from Google Drive
TOV_FILE_IDS = {
    "twitter": "YOUR_TWITTER_TOV_ID",
    "linkedin": "YOUR_LINKEDIN_TOV_ID",
    "heygen": "YOUR_HEYGEN_TOV_ID",
    "text_post": "YOUR_TEXT_POST_TOV_ID",
    "newsletter": "YOUR_NEWSLETTER_TOV_ID",
    "community_post": "YOUR_COMMUNITY_TOV_ID",
    "carousel": "YOUR_CAROUSEL_TOV_ID",
    "long_form": "YOUR_LONGFORM_TOV_ID",
}

# Platform aliases for flexibility
PLATFORM_ALIASES = {
    "x": "twitter",
    "tweet": "twitter",
    "li": "linkedin",
    "linked_in": "linkedin",
    "video": "heygen",
    "heygen_video": "heygen",
    "text": "text_post",
    "generic": "text_post",
    "community": "community_post",
    "youtube_community": "community_post",
    "carousels": "carousel",
    "linkedin_carousel": "carousel",
    "long": "long_form",
    "blog": "long_form",
}


def _get_cache_dir() -> Path:
    """Get the TOV cache directory, creating it if needed."""
    cache_dir = Path(Config.get_tov_cache_dir())
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_cache_file(platform: str) -> Path:
    """Get the cache file path for a platform."""
    return _get_cache_dir() / f"{platform}_tov.md"


def _is_cache_valid(cache_file: Path) -> bool:
    """Check if a cache file exists and is still valid."""
    if not cache_file.exists():
        return False

    mtime = cache_file.stat().st_mtime
    return (time.time() - mtime) < CACHE_TTL


def _normalize_platform(platform: str) -> str:
    """Normalize platform name, handling aliases."""
    platform = platform.lower().strip()
    return PLATFORM_ALIASES.get(platform, platform)


def _download_from_drive(file_id: str, output_path: Path) -> bool:
    """
    Download a file from Google Drive.

    Args:
        file_id: Google Drive file ID
        output_path: Local path to save the file

    Returns:
        True if successful, False otherwise
    """
    # First try the Google Drive script
    try:
        gdrive_script = Config.get_google_drive_script()

        result = subprocess.run(
            ["python3", gdrive_script, "download", file_id, str(output_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0 and output_path.exists():
            return True

        # Log but continue to fallback
        if "ModuleNotFoundError" in result.stderr:
            print("Google Drive API not available (missing google-api-python-client)")
        else:
            print(f"Google Drive script error: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        print("Google Drive download timed out")
    except Exception as e:
        print(f"Error with Google Drive script: {e}")

    # Fallback: Try direct curl download (works for shared files)
    try:
        # Google Drive direct download URL format
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        result = subprocess.run(
            ["curl", "-sL", "-o", str(output_path), download_url],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0 and output_path.exists():
            # Check if we got HTML (error page) instead of markdown
            content = output_path.read_text()
            if content.startswith("<!DOCTYPE") or content.startswith("<html") or content.startswith("<!doctype"):
                print("Google Drive returned HTML (file may not be publicly accessible)")
                output_path.unlink()
                return False
            # Also check for common Google error patterns
            if "accounts.google.com" in content or "sign in" in content.lower():
                print("Google Drive returned login page")
                output_path.unlink()
                return False
            return True

    except Exception as e:
        print(f"Curl fallback failed: {e}")

    return False


# Minimal fallback TOV profiles for test mode
_FALLBACK_TOV_PROFILES = {
    "twitter": """# the creator's Twitter Tone of Voice

## Core Voice
- Direct and punchy
- Contrarian when warranted
- Technical but accessible
- Use hyphens (-) not em-dashes

## Format
- 5-10 tweets per thread
- Each tweet under 280 characters
- Hook in first tweet
- CTA in last tweet

## Style
- No hashtags in thread body
- Minimal emojis
- No corporate speak
- Challenge assumptions
""",
    "linkedin": """# the creator's LinkedIn Tone of Voice

## Core Voice
- Professional but not corporate
- Thought leadership focus
- Share real experiences
- Use hyphens (-) not em-dashes

## Format
- 1,200-1,800 characters
- 8-12 short paragraphs
- Single line breaks for readability
- Hook -> Content -> CTA structure

## Style
- No markdown formatting
- Plain text only
- Conversational tone
- Include personal stories
""",
    "newsletter": """# the creator's Newsletter Tone of Voice

## Core Voice
- Personal and insightful
- Like writing to a smart friend
- Share behind-the-scenes
- Use hyphens (-) not em-dashes

## Format
- 300-500 words
- Clear subject line
- Opening hook
- Value-driven content
- Clear CTA

## Style
- Conversational
- Include one key takeaway
- Link to longer content
""",
    "community_post": """# the creator's Community Post Tone of Voice

## Core Voice
- Casual and engaging
- Spark discussion
- Share quick insights
- Use hyphens (-) not em-dashes

## Format
- 200-400 characters
- Question or statement
- Encourage replies

## Style
- Use *bold* for emphasis
- Keep it conversational
- End with engaging question
""",
    "text_post": """# the creator's Text Post Tone of Voice

## Core Voice
- Punchy and standalone
- Single valuable insight
- Platform-agnostic
- Use hyphens (-) not em-dashes

## Format
- 300-500 characters
- Self-contained value
- No external links needed

## Style
- Conversational
- Clear point
- Memorable takeaway
""",
    "carousel": """# the creator's Carousel Tone of Voice

## Core Voice
- Visual storytelling
- Progressive revelation
- Clear takeaways
- Use hyphens (-) not em-dashes

## Format
- 6-10 slides
- Hook slide first
- One idea per slide
- CTA on final slide

## Style
- Bold headlines
- Minimal text per slide
- Visual hierarchy
""",
    "heygen": """# the creator's HeyGen Video Tone of Voice

## Core Voice
- Conversational speaking style
- As if talking to a friend
- Technical but accessible
- Use hyphens (-) not em-dashes

## Format
- 30 seconds max
- Clear hook in first 3 seconds
- One main point
- CTA at end

## Style
- Natural speech patterns
- Contractions OK
- Short sentences
- No jargon without explanation
""",
    "long_form": """# the creator's Long-Form Tone of Voice

## Core Voice
- Deep dive authority
- Well-researched
- Personal experiences
- Use hyphens (-) not em-dashes

## Format
- 1000-2000 words
- Clear structure
- Subheadings
- Examples and stories

## Style
- Professional but personable
- Include data when relevant
- Connect concepts
- Actionable takeaways
""",
}


def get_tov_profile(platform: str, force_refresh: bool = False, use_fallback: bool = True) -> Optional[str]:
    """
    Load a TOV profile from Google Drive with caching.

    Args:
        platform: Platform name (e.g., "twitter", "linkedin", "newsletter")
        force_refresh: If True, ignore cache and download fresh copy
        use_fallback: If True, use minimal fallback profiles when download fails

    Returns:
        TOV profile content as string, or None if not found
    """
    # Normalize platform name
    platform = _normalize_platform(platform)

    # Check if platform is supported
    if platform not in TOV_FILE_IDS:
        print(f"Warning: Unknown platform '{platform}'. Available: {list(TOV_FILE_IDS.keys())}")
        return None

    cache_file = _get_cache_file(platform)

    # Check cache first (unless force_refresh)
    if not force_refresh and _is_cache_valid(cache_file):
        try:
            return cache_file.read_text()
        except IOError as e:
            print(f"Error reading cache: {e}")

    # Download from Google Drive
    file_id = TOV_FILE_IDS[platform]
    print(f"Downloading TOV profile for {platform}...")

    if _download_from_drive(file_id, cache_file):
        try:
            return cache_file.read_text()
        except IOError as e:
            print(f"Error reading downloaded file: {e}")

    # If download failed but cache exists (even if expired), use it
    if cache_file.exists():
        print(f"Warning: Using expired cache for {platform}")
        try:
            return cache_file.read_text()
        except IOError:
            pass

    # Use fallback profile if enabled
    if use_fallback and platform in _FALLBACK_TOV_PROFILES:
        print(f"Using fallback TOV profile for {platform} (development mode)")
        fallback_content = _FALLBACK_TOV_PROFILES[platform]
        # Cache the fallback for consistency
        try:
            cache_file.write_text(fallback_content)
        except IOError:
            pass
        return fallback_content

    return None


def get_tov_profiles(platforms: list[str]) -> dict[str, Optional[str]]:
    """
    Load multiple TOV profiles at once.

    Args:
        platforms: List of platform names

    Returns:
        Dict of platform -> profile content
    """
    return {platform: get_tov_profile(platform) for platform in platforms}


def clear_tov_cache(platform: Optional[str] = None) -> int:
    """
    Clear TOV cache.

    Args:
        platform: Specific platform to clear, or None for all

    Returns:
        Number of cache files deleted
    """
    cache_dir = _get_cache_dir()
    deleted = 0

    if platform:
        platform = _normalize_platform(platform)
        cache_file = _get_cache_file(platform)
        if cache_file.exists():
            cache_file.unlink()
            deleted = 1
    else:
        for cache_file in cache_dir.glob("*_tov.md"):
            cache_file.unlink()
            deleted += 1

    return deleted


def list_cached_profiles() -> list[dict]:
    """
    List all cached TOV profiles with their status.

    Returns:
        List of dicts with platform, cached, valid, and age_hours
    """
    cache_dir = _get_cache_dir()
    results = []

    for platform in TOV_FILE_IDS.keys():
        cache_file = _get_cache_file(platform)
        entry = {
            "platform": platform,
            "cached": cache_file.exists(),
            "valid": False,
            "age_hours": None,
        }

        if cache_file.exists():
            mtime = cache_file.stat().st_mtime
            age_seconds = time.time() - mtime
            entry["age_hours"] = round(age_seconds / 3600, 1)
            entry["valid"] = age_seconds < CACHE_TTL

        results.append(entry)

    return results


def preload_all_profiles() -> dict[str, bool]:
    """
    Preload all TOV profiles into cache.

    Useful for ensuring all profiles are available before processing.

    Returns:
        Dict of platform -> success status
    """
    results = {}
    for platform in TOV_FILE_IDS.keys():
        profile = get_tov_profile(platform)
        results[platform] = profile is not None
    return results


def get_available_platforms() -> list[str]:
    """Get list of available platform names."""
    return list(TOV_FILE_IDS.keys())


def print_cache_status() -> None:
    """Print the status of the TOV cache."""
    print("=" * 50)
    print("TOV Profile Cache Status")
    print("=" * 50)
    print(f"Cache directory: {_get_cache_dir()}")
    print(f"Cache TTL: {CACHE_TTL // 3600} hours")
    print("-" * 50)

    profiles = list_cached_profiles()
    for p in profiles:
        status = "VALID" if p["valid"] else ("EXPIRED" if p["cached"] else "NOT CACHED")
        age = f"({p['age_hours']}h)" if p["age_hours"] is not None else ""
        print(f"  {p['platform']:15} {status:12} {age}")

    print("=" * 50)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TOV Profile Management")
    parser.add_argument("--status", action="store_true", help="Show cache status")
    parser.add_argument("--clear", action="store_true", help="Clear all cache")
    parser.add_argument("--preload", action="store_true", help="Preload all profiles")
    parser.add_argument("--get", type=str, help="Get a specific profile")

    args = parser.parse_args()

    if args.status:
        print_cache_status()
    elif args.clear:
        deleted = clear_tov_cache()
        print(f"Cleared {deleted} cached profiles")
    elif args.preload:
        print("Preloading all TOV profiles...")
        results = preload_all_profiles()
        for platform, success in results.items():
            status = "OK" if success else "FAILED"
            print(f"  {platform}: {status}")
    elif args.get:
        profile = get_tov_profile(args.get)
        if profile:
            print(f"Profile for {args.get}:")
            print("-" * 40)
            print(profile[:500] + "..." if len(profile) > 500 else profile)
        else:
            print(f"Failed to load profile for {args.get}")
    else:
        print_cache_status()
