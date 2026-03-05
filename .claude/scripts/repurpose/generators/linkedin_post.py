"""
LinkedIn Post Generator.

Generates 1,200-1,800 character LinkedIn posts from insights.
"""

from pathlib import Path
from typing import Optional

from . import register_generator
from .base import (
    load_template,
    call_gemini,
    extract_text_from_response,
    save_content,
    build_generator_input,
    format_prompt_with_input,
    generate_slug,
    generate_title_images,
    LONG_FORM_TYPES,
)


@register_generator("linkedin_post")
def generate_linkedin_post(
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
    Generate a LinkedIn post from an insight.

    Args:
        insight: Insight dictionary
        tov_profile: LinkedIn TOV profile
        output_dir: Output directory
        insight_number: Insight number for filename
        user_feedback: Optional user feedback

    Returns:
        Path to generated file, or None on failure
    """
    print(f"Generating LinkedIn post for insight {insight_number}...")

    # Load template
    prompt_template = load_template("linkedin_post.md")
    if not prompt_template:
        print("Error: LinkedIn template not found")
        return None

    # Build input
    input_data = build_generator_input(
        insight=insight,
        tov_profile=tov_profile,
        platform="linkedin",
        user_feedback=user_feedback,
    )

    # Add LinkedIn-specific requirements
    input_data["target_length"] = "1200-1800 characters"
    input_data["content_requirements"] = {
        "include_hook": True,
        "include_cta": True,
        "use_formatting": True,
        "max_paragraphs": 12,
    }

    # Add podcast mode context
    if mode == "podcast" and guests:
        guest_names = [g["name"] for g in guests]
        input_data["podcast_mode"] = True
        input_data["guests"] = guests
        input_data["guest_attribution"] = f"This is from a podcast conversation with {', '.join(guest_names)}. Mention the guest(s) in the post."

    # Format prompt
    full_prompt = format_prompt_with_input(prompt_template, input_data)

    # Add specific instructions for output format
    full_prompt += """

IMPORTANT: Return ONLY the LinkedIn post text. No JSON, no code blocks, no explanations.
Just the raw post content that can be directly copied to LinkedIn.
Use plain text formatting (line breaks, bullet points with •, etc.)
Do NOT use markdown formatting.
"""

    # Call Gemini
    response = call_gemini(full_prompt)
    if not response:
        print("Failed to generate LinkedIn post")
        return None

    # Extract text
    content = extract_text_from_response(response)

    if not content:
        print("Empty response from generator")
        return None

    # Validate length
    char_count = len(content)
    if char_count < 500:
        print(f"Warning: Post too short ({char_count} chars)")
    elif char_count > 2500:
        print(f"Warning: Post too long ({char_count} chars)")

    # Create named subfolder
    core_insight = insight.get("core_insight", f"insight-{insight_number}")
    folder_name = generate_slug(core_insight, "linkedin_post")
    subfolder = output_dir / folder_name
    subfolder.mkdir(parents=True, exist_ok=True)

    # Save post content
    output_path = save_content(content, subfolder, "post.md")

    # Generate title images (long-form type)
    print(f"  Generating title images for LinkedIn post {insight_number}...")
    images = generate_title_images(core_insight, subfolder / "images")
    image_count = len(images)

    print(f"Generated LinkedIn post: {folder_name}/ ({char_count} chars, {image_count} title images)")
    return output_path
