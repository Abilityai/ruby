"""
Community Post Generator.

Generates short community posts (200-400 chars) for Slack/Discord/YouTube.
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


@register_generator("community_post")
def generate_community_post(
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
    Generate a community post from an insight.
    """
    print(f"Generating community post for insight {insight_number}...")

    prompt_template = load_template("community_post.md")
    if not prompt_template:
        print("Error: Community post template not found")
        return None

    input_data = build_generator_input(
        insight=insight,
        tov_profile=tov_profile,
        platform="community_post",
        user_feedback=user_feedback,
    )

    input_data["target_length"] = "200-400 characters"
    input_data["content_requirements"] = {
        "include_question": True,
        "conversational_tone": True,
        "max_characters": 400,
    }

    full_prompt = format_prompt_with_input(prompt_template, input_data)

    full_prompt += """

IMPORTANT: Return ONLY the community post text. No JSON, no code blocks.
Keep it 200-400 characters. Use *bold* for emphasis where appropriate.
End with an engaging question to spark discussion.
"""

    response = call_gemini(full_prompt)
    if not response:
        print("Failed to generate community post")
        return None

    content = extract_text_from_response(response)

    if not content:
        print("Empty response from generator")
        return None

    char_count = len(content)
    if char_count < 100:
        print(f"Warning: Post too short ({char_count} chars)")
    elif char_count > 500:
        print(f"Warning: Post too long ({char_count} chars)")

    # Create named subfolder
    core_insight = insight.get("core_insight", f"insight-{insight_number}")
    folder_name = generate_slug(core_insight, "community_post")
    subfolder = output_dir / folder_name
    subfolder.mkdir(parents=True, exist_ok=True)

    output_path = save_content(content, subfolder, "post.md")

    print(f"Generated community post: {folder_name}/ ({char_count} chars)")
    return output_path
