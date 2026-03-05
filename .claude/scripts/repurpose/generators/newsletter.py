"""
Newsletter Generator.

Generates newsletter sections (300-500 words) from insights.
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
    generate_title_images,
    LONG_FORM_TYPES,
)


def format_newsletter_as_markdown(data: dict) -> str:
    """Format newsletter JSON as markdown."""
    lines = []

    subject = data.get("subject_line", "")
    if subject:
        lines.append(f"**Subject:** {subject}")
        lines.append("")
        lines.append("---")
        lines.append("")

    body = data.get("email_body", "")
    if body:
        lines.append(body)

    return "\n".join(lines)


@register_generator("newsletter")
def generate_newsletter(
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
    Generate a newsletter section from an insight.
    """
    print(f"Generating newsletter for insight {insight_number}...")

    prompt_template = load_template("newsletter.md")
    if not prompt_template:
        print("Error: Newsletter template not found")
        return None

    input_data = build_generator_input(
        insight=insight,
        tov_profile=tov_profile,
        platform="newsletter",
        user_feedback=user_feedback,
    )

    input_data["target_length"] = "300-500 words"
    input_data["content_requirements"] = {
        "include_subject_line": True,
        "include_cta": True,
        "target_word_count": "300-500",
    }

    full_prompt = format_prompt_with_input(prompt_template, input_data)

    full_prompt += """

Return as JSON:
{
  "subject_line": "Compelling email subject line",
  "email_body": "Full email content...",
  "metadata": {
    "word_count": 400,
    "key_takeaways": ["takeaway 1", "takeaway 2"],
    "cta_type": "link_to_video"
  }
}
"""

    response = call_gemini(full_prompt)
    if not response:
        print("Failed to generate newsletter")
        return None

    data = extract_json_from_response(response)
    if data and "email_body" in data:
        content = format_newsletter_as_markdown(data)
    else:
        content = extract_text_from_response(response)

    if not content:
        print("Empty response from generator")
        return None

    # Create named subfolder
    core_insight = insight.get("core_insight", f"insight-{insight_number}")
    folder_name = generate_slug(core_insight, "newsletter")
    subfolder = output_dir / folder_name
    subfolder.mkdir(parents=True, exist_ok=True)

    # Save content
    output_path = save_content(content, subfolder, "post.md")

    # Generate title images (long-form type)
    print(f"  Generating title images for newsletter {insight_number}...")
    images = generate_title_images(core_insight, subfolder / "images")
    image_count = len(images)

    print(f"Generated newsletter: {folder_name}/ ({image_count} title images)")
    return output_path
