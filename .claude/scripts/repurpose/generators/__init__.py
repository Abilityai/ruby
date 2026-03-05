"""
Content generators for CEO Content Engine.

Each generator takes an insight and produces platform-specific content.
"""

from typing import Optional, Callable
from pathlib import Path

# Generator registry
_GENERATORS: dict[str, Callable] = {}


def register_generator(content_type: str):
    """Decorator to register a generator function."""
    def decorator(func: Callable):
        _GENERATORS[content_type] = func
        return func
    return decorator


def get_generator(content_type: str) -> Optional[Callable]:
    """Get a generator function by content type."""
    return _GENERATORS.get(content_type)


def get_available_generators() -> list[str]:
    """Get list of available content types."""
    return list(_GENERATORS.keys())


def generate_content(
    content_type: str,
    insight: dict,
    tov_profile: str,
    output_dir: Path,
    insight_number: int = 1,
    user_feedback: str = "NO_FEEDBACK",
    mode: str = "solo",
    guests: list = None,
) -> Optional[str]:
    """
    Generate content for a specific platform.

    Args:
        content_type: Type of content (e.g., "linkedin_post")
        insight: Insight dictionary from extraction
        tov_profile: Tone of voice profile content
        output_dir: Directory to save generated content
        insight_number: Insight number for filename
        user_feedback: Optional user feedback/direction
        mode: Content mode - "solo" or "podcast"
        guests: List of guest dictionaries (for podcast mode)

    Returns:
        Path to generated file, or None on failure
    """
    generator = get_generator(content_type)
    if not generator:
        print(f"No generator found for content type: {content_type}")
        return None

    return generator(
        insight=insight,
        tov_profile=tov_profile,
        output_dir=output_dir,
        insight_number=insight_number,
        user_feedback=user_feedback,
        mode=mode,
        guests=guests,
    )


def generate_all_for_insight(
    insight: dict,
    tov_profiles: dict[str, str],
    output_dir: Path,
    insight_number: int = 1,
    content_types: list[str] = None,
    user_feedback: str = "NO_FEEDBACK",
    mode: str = "solo",
    guests: list = None,
) -> dict[str, Optional[str]]:
    """
    Generate all content types for a single insight.

    Args:
        insight: Insight dictionary
        tov_profiles: Dict of platform -> TOV profile content
        output_dir: Output directory
        insight_number: Insight number
        content_types: List of content types to generate (None = all)
        user_feedback: Optional user feedback
        mode: Content mode - "solo" or "podcast"
        guests: List of guest dictionaries (for podcast mode)

    Returns:
        Dict of content_type -> generated file path (or None if failed)
    """
    if content_types is None:
        content_types = get_available_generators()

    results = {}

    # Map content types to TOV profile keys
    tov_mapping = {
        "linkedin_post": "linkedin",
        "twitter_thread": "twitter",
        "newsletter": "newsletter",
        "community_post": "community_post",
        "text_post": "text_post",
        "linkedin_carousel": "carousel",
        "blog_post": "long_form",
        "instagram_post": "text_post",
        "quote_card": "text_post",
        "guest_promo": "text_post",
    }

    for content_type in content_types:
        tov_key = tov_mapping.get(content_type, "text_post")
        tov_profile = tov_profiles.get(tov_key, "")

        result = generate_content(
            content_type=content_type,
            insight=insight,
            tov_profile=tov_profile,
            output_dir=output_dir,
            insight_number=insight_number,
            user_feedback=user_feedback,
            mode=mode,
            guests=guests,
        )
        results[content_type] = result

    return results


# Import all generators to register them
from . import (
    linkedin_post,
    twitter_thread,
    newsletter,
    community_post,
    text_post,
    carousel,
    blog_post,
)

__all__ = [
    "register_generator",
    "get_generator",
    "get_available_generators",
    "generate_content",
    "generate_all_for_insight",
]
