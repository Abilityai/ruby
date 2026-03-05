"""
Text Post Generator.

Generates platform-agnostic short posts (300-500 chars).
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
)


@register_generator("text_post")
def generate_text_post(
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
    Generate a platform-agnostic text post from an insight.
    """
    print(f"Generating text post for insight {insight_number}...")

    prompt_template = load_template("text_post.md")
    if not prompt_template:
        print("Error: Text post template not found")
        return None

    input_data = build_generator_input(
        insight=insight,
        tov_profile=tov_profile,
        platform="text_post",
        user_feedback=user_feedback,
    )

    input_data["target_length"] = "300-500 characters"
    input_data["content_requirements"] = {
        "standalone_value": True,
        "no_external_links": True,
        "max_characters": 500,
    }

    full_prompt = format_prompt_with_input(prompt_template, input_data)

    full_prompt += """

IMPORTANT: Return ONLY the text post content. No JSON, no code blocks.
Keep it 300-500 characters. Should be punchy and standalone.
Can be used on any platform (Twitter, LinkedIn, Facebook, etc.)
"""

    response = call_gemini(full_prompt)
    if not response:
        print("Failed to generate text post")
        return None

    content = extract_text_from_response(response)

    if not content:
        print("Empty response from generator")
        return None

    char_count = len(content)
    if char_count < 150:
        print(f"Warning: Post too short ({char_count} chars)")
    elif char_count > 600:
        print(f"Warning: Post too long ({char_count} chars)")

    # Create named subfolder
    core_insight = insight.get("core_insight", f"insight-{insight_number}")
    folder_name = generate_slug(core_insight, "text_post")
    subfolder = output_dir / folder_name
    subfolder.mkdir(parents=True, exist_ok=True)

    output_path = save_content(content, subfolder, "post.md")

    print(f"Generated text post: {folder_name}/ ({char_count} chars)")
    return output_path
