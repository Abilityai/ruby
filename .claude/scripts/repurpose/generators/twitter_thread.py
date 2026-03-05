"""
Twitter Thread Generator.

Generates 5-10 tweet threads from insights.
"""

import json
from pathlib import Path
from typing import Optional

from . import register_generator
from .base import (
    load_template,
    call_gemini,
    extract_json_from_response,
    extract_text_from_response,
    save_content,
    build_generator_input,
    format_prompt_with_input,
    generate_slug,
)


def format_thread_as_markdown(thread_data: dict) -> str:
    """Format thread JSON as readable markdown."""
    lines = []

    tweets = thread_data.get("thread", [])
    if not tweets:
        return ""

    for i, tweet in enumerate(tweets, 1):
        lines.append(f"**Tweet {i}:**")
        lines.append(tweet)
        lines.append("")

    # Add metadata if available
    metadata = thread_data.get("thread_metadata", {})
    if metadata:
        lines.append("---")
        lines.append(f"Total tweets: {metadata.get('total_tweets', len(tweets))}")
        if "character_counts" in metadata:
            counts = metadata["character_counts"]
            lines.append(f"Character counts: {counts}")

    return "\n".join(lines)


@register_generator("twitter_thread")
def generate_twitter_thread(
    insight: dict,
    tov_profile: str,
    output_dir: Path,
    insight_number: int = 1,
    user_feedback: str = "NO_FEEDBACK",
    mode: str = "solo",
    guests: list = None,
    **kwargs,
) -> Optional[str]:
    """
    Generate a Twitter thread from an insight.

    Args:
        insight: Insight dictionary
        tov_profile: Twitter TOV profile
        output_dir: Output directory
        insight_number: Insight number for filename
        user_feedback: Optional user feedback
        mode: Content mode - "solo" or "podcast"
        guests: List of guest dictionaries (for podcast mode)

    Returns:
        Path to generated file, or None on failure
    """
    print(f"Generating Twitter thread for insight {insight_number}...")

    # Load template
    prompt_template = load_template("twitter_thread.md")
    if not prompt_template:
        print("Error: Twitter template not found")
        return None

    # Build input
    input_data = build_generator_input(
        insight=insight,
        tov_profile=tov_profile,
        platform="twitter_thread",
        user_feedback=user_feedback,
    )

    input_data["target_length"] = "280 chars per tweet, 5-10 tweets"
    input_data["content_requirements"] = {
        "include_hook": True,
        "include_cta": True,
        "use_formatting": True,
        "target_tweet_count": "5-10 tweets",
        "max_chars_per_tweet": 280,
        "use_thread_numbering": True,
    }

    # Add podcast mode context
    if mode == "podcast" and guests:
        handles = [g["twitter"] for g in guests if g.get("twitter")]
        input_data["podcast_mode"] = True
        input_data["guests"] = guests
        if handles:
            input_data["guest_attribution"] = f"Tag the guest(s) in the thread: {', '.join(handles)}"

    # Format prompt
    full_prompt = format_prompt_with_input(prompt_template, input_data)

    full_prompt += """

IMPORTANT: Return the thread as a JSON object with this structure:
{
  "thread": ["Tweet 1 text", "Tweet 2 text", ...],
  "thread_metadata": {
    "total_tweets": 5,
    "character_counts": [120, 180, 200, 150, 180],
    "primary_hook_type": "contrarian_statement",
    "cta_type": "engagement_question"
  }
}

Each tweet MUST be under 280 characters. Include the thread emoji in tweet 1.
"""

    # Call Gemini
    response = call_gemini(full_prompt)
    if not response:
        print("Failed to generate Twitter thread")
        return None

    # Try to parse as JSON first
    thread_data = extract_json_from_response(response)

    if thread_data and "thread" in thread_data:
        # Validate tweet lengths
        tweets = thread_data["thread"]
        for i, tweet in enumerate(tweets):
            if len(tweet) > 280:
                print(f"Warning: Tweet {i+1} exceeds 280 chars ({len(tweet)})")

        content = format_thread_as_markdown(thread_data)
    else:
        # Fallback: use raw text
        content = extract_text_from_response(response)

    if not content:
        print("Empty response from generator")
        return None

    # Create named subfolder
    core_insight = insight.get("core_insight", f"insight-{insight_number}")
    folder_name = generate_slug(core_insight, "twitter_thread")
    subfolder = output_dir / folder_name
    subfolder.mkdir(parents=True, exist_ok=True)

    # Save
    output_path = save_content(content, subfolder, "thread.md")

    tweet_count = len(thread_data.get("thread", [])) if thread_data else "unknown"
    print(f"Generated Twitter thread: {folder_name}/ ({tweet_count} tweets)")
    return output_path
