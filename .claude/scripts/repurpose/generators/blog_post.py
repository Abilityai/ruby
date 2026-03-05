"""
Blog Post Generator.

Generates blog articles from insights with SEO metadata.
AI decides which insights are blog-worthy and content depth.
"""

import json
from pathlib import Path
from typing import Optional

from . import register_generator
from .base import (
    load_template,
    call_gemini,
    extract_json_from_response,
    build_generator_input,
    format_prompt_with_input,
    generate_slug,
    generate_title_images,
    LONG_FORM_TYPES,
)


# Valid blog post categories
BLOG_CATEGORIES = [
    "AI Strategy",
    "AI Implementation",
    "Case Study",
    "How-To",
    "Industry Insights",
    "AI Governance",
    "Automation",
    "E-commerce",
    "HR & Recruiting",
    "Customer Support",
    "Marketing",
    "Company News",
]


def validate_blog_post(data: dict) -> tuple[bool, list[str]]:
    """
    Validate blog post JSON structure.

    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []

    # Check if AI decided to skip this insight
    if data.get("skip") or data.get("skipReason"):
        return True, []  # Valid skip response

    # Required fields
    required_fields = ["slug", "title", "category", "introduction", "fullContent"]
    for field in required_fields:
        if field not in data or not data[field]:
            issues.append(f"Missing or empty required field: {field}")

    # Validate slug format (3-5 words, lowercase, hyphenated)
    slug = data.get("slug", "")
    if slug:
        words = slug.split("-")
        if len(words) < 2 or len(words) > 6:
            issues.append(f"Slug should be 3-5 words, got {len(words)}: {slug}")
        if slug != slug.lower():
            issues.append("Slug should be lowercase")

    # Validate title length (max 60 chars)
    title = data.get("title", "")
    if title and len(title) > 70:  # Allow some flexibility
        issues.append(f"Title too long: {len(title)} chars (max 60)")

    # Validate category
    category = data.get("category", "")
    if category and category not in BLOG_CATEGORIES:
        issues.append(f"Invalid category: {category}. Must be one of: {BLOG_CATEGORIES}")

    # Validate introduction length (150-160 chars for meta description)
    intro = data.get("introduction", "")
    if intro and (len(intro) < 100 or len(intro) > 200):
        issues.append(f"Introduction should be 150-160 chars, got {len(intro)}")

    # Validate content length (800+ words)
    content = data.get("fullContent", "")
    if content:
        word_count = len(content.split())
        if word_count < 600:  # Allow some flexibility below 800
            issues.append(f"Content too short: {word_count} words (min 800)")

    return len(issues) == 0, issues


def format_blog_post_output(data: dict) -> dict:
    """
    Format and normalize the blog post JSON output.

    - Auto-generates pageTitle from title
    - Ensures featuredImage structure
    - Cleans up any extra fields
    """
    title = data.get("title", "Untitled")

    # Build the normalized output
    output = {
        "slug": data.get("slug", ""),
        "title": title,
        "pageTitle": f"{title} | Ability AI",
        "category": data.get("category", "AI Strategy"),
        "introduction": data.get("introduction", ""),
    }

    # Add fullContent if present
    if data.get("fullContent"):
        output["fullContent"] = data["fullContent"]

    # Build featuredImage structure
    featured_image = data.get("featuredImage", {})
    if isinstance(featured_image, dict):
        output["featuredImage"] = {
            "description": featured_image.get("description", ""),
        }
        if featured_image.get("visualTheme"):
            output["featuredImage"]["visualTheme"] = featured_image["visualTheme"]
    elif data.get("thumbnailTitle") or data.get("imageDescription"):
        # Handle alternative field names from AI
        output["featuredImage"] = {
            "description": data.get("thumbnailTitle") or data.get("imageDescription", ""),
        }
    else:
        # Default empty featured image
        output["featuredImage"] = {
            "description": "",
        }

    return output


@register_generator("blog_post")
def generate_blog_post(
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
    Generate a blog post from an insight.

    The AI decides:
    - Whether this insight is worth a blog post (may skip)
    - Content depth (800+ words standard, 1200+ for pillar content)

    Returns:
        Path to generated JSON file, or None if skipped/failed
    """
    print(f"Evaluating insight {insight_number} for blog post...")

    prompt_template = load_template("blog_post.md")
    if not prompt_template:
        print("Error: Blog post template not found")
        return None

    input_data = build_generator_input(
        insight=insight,
        tov_profile=tov_profile,
        platform="blog_post",
        user_feedback=user_feedback,
    )

    # Add insight scores to help AI decide blog-worthiness
    input_data["insight_scores"] = insight.get("scores", {})
    input_data["categories"] = BLOG_CATEGORIES

    full_prompt = format_prompt_with_input(prompt_template, input_data)

    response = call_gemini(full_prompt)
    if not response:
        print("Failed to generate blog post content")
        return None

    data = extract_json_from_response(response)
    if not data:
        print("Failed to parse blog post JSON")
        return None

    # Check if AI decided to skip this insight
    if data.get("skip") is True or data.get("skipReason"):
        skip_reason = data.get("skipReason", "Not suitable for blog format")
        print(f"Skipping insight {insight_number} for blog post: {skip_reason}")
        return None

    # Validate the response
    is_valid, issues = validate_blog_post(data)
    if not is_valid:
        print(f"Blog post validation issues for insight {insight_number}:")
        for issue in issues:
            print(f"  - {issue}")
        # Continue anyway but log the issues

    # Format and normalize the output
    formatted_data = format_blog_post_output(data)

    # Create named subfolder
    core_insight = insight.get("core_insight", f"insight-{insight_number}")
    folder_name = generate_slug(core_insight, "blog_post")
    subfolder = output_dir / folder_name
    subfolder.mkdir(parents=True, exist_ok=True)

    # Save JSON file
    json_path = subfolder / "post.json"
    with open(json_path, "w") as f:
        json.dump(formatted_data, f, indent=2)

    # Generate title images (long-form type)
    word_count = len(formatted_data.get("fullContent", "").split())
    print(f"  Generating title images for blog post {insight_number}...")
    images = generate_title_images(core_insight, subfolder / "images")
    image_count = len(images)

    content_type = "pillar" if word_count >= 1200 else "standard"
    print(f"Generated blog post: {folder_name}/ ({word_count} words, {content_type}, {image_count} title images)")

    return str(json_path)
