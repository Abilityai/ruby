"""
Base generator module with common functionality.
"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import sys
import unicodedata

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


def load_template(template_name: str) -> str:
    """
    Load a Gemini content generation template.

    Args:
        template_name: Name of the template file (without path)

    Returns:
        Template content
    """
    templates_dir = Config.get_templates_dir()
    template_path = Path(templates_dir) / template_name

    if template_path.exists():
        return template_path.read_text()

    print(f"Warning: Template file not found: {template_path}")
    return ""


def load_prompt(prompt_name: str) -> str:
    """Deprecated: Use load_template() instead."""
    return load_template(prompt_name)


def call_gemini(prompt: str, model: str = None) -> Optional[str]:
    """
    Call Gemini API.

    Args:
        prompt: The prompt to send
        model: Model to use (defaults to primary)

    Returns:
        Response text or None
    """
    if model is None:
        model = Config.GEMINI_MODELS["primary"]

    api_key = Config.get_gemini_api_key()
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        return None

    request_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 4096,
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(request_body, f)
        request_file = f.name

    try:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json",
             "-d", f"@{request_file}", api_url],
            capture_output=True, text=True, timeout=120,
        )

        if result.returncode != 0:
            print(f"Gemini API failed: {result.stderr}")
            return None

        response = json.loads(result.stdout)

        if "error" in response:
            error_msg = response["error"].get("message", "Unknown")
            print(f"Gemini error: {error_msg}")
            # Try fallback
            if model == Config.GEMINI_MODELS["primary"]:
                return call_gemini(prompt, Config.GEMINI_MODELS["fallback"])
            return None

        candidates = response.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")

        return None

    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return None
    finally:
        try:
            os.unlink(request_file)
        except:
            pass


def extract_json_from_response(response: str) -> Optional[dict]:
    """Extract JSON from Gemini response."""
    if not response:
        return None

    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'\{[\s\S]*\}',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, response)
        for match in matches:
            try:
                json_str = match.strip()
                if json_str.startswith('{'):
                    return json.loads(json_str)
            except json.JSONDecodeError:
                continue

    try:
        return json.loads(response.strip())
    except:
        pass

    return None


def extract_text_from_response(response: str) -> str:
    """
    Extract clean text from Gemini response.

    Removes code blocks, JSON markers, etc.
    """
    if not response:
        return ""

    text = response.strip()

    # Remove code block markers
    text = re.sub(r'^```\w*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)

    return text.strip()


def save_content(content: str, output_dir: Path, filename: str) -> str:
    """
    Save generated content to file.

    Args:
        content: Content to save
        output_dir: Output directory
        filename: Filename to use

    Returns:
        Full path to saved file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    with open(output_path, "w") as f:
        f.write(content)

    return str(output_path)


def build_generator_input(
    insight: dict,
    tov_profile: str,
    platform: str,
    user_feedback: str = "NO_FEEDBACK",
) -> dict:
    """
    Build the standard input structure for generators.

    Args:
        insight: Insight dictionary
        tov_profile: TOV profile content
        platform: Platform name
        user_feedback: User feedback string

    Returns:
        Input dictionary for generator prompt
    """
    return {
        "insight": {
            "core_insight": insight.get("core_insight", ""),
            "quotable_moments": insight.get("quotable_moments", []),
            "story_elements": insight.get("story_elements", "None"),
            "thought_leadership_angle": insight.get("thought_leadership_angle", ""),
            "supporting_context": insight.get("supporting_context", ""),
            "scores": insight.get("scores", {}),
        },
        "tone_of_voice_profile": tov_profile,
        "platform": platform,
        "user_feedback": user_feedback,
    }


def format_prompt_with_input(prompt_template: str, input_data: dict) -> str:
    """
    Format a prompt template with input data.

    Replaces N8N-style placeholders like {{ $('Node').json.field }}
    with the actual JSON input data.
    """
    # Remove N8N-specific placeholders
    prompt = re.sub(r'\{\{\s*\$\([^)]+\)[^}]*\}\}', '', prompt_template)

    # Add the input data as JSON at the end
    input_json = json.dumps(input_data, indent=2)

    formatted_prompt = f"""{prompt}

---

## INPUT DATA:

```json
{input_json}
```

Generate the content based on the input above.
"""

    return formatted_prompt


# Content types that get title images (long-form)
LONG_FORM_TYPES = {"linkedin_post", "blog_post", "newsletter"}

# Number of title images to generate per long-form post
TITLE_IMAGE_COUNT = 3


def generate_slug(text: str, content_type: str, max_words: int = 6) -> str:
    """
    Generate a meaningful kebab-case slug from insight text.

    Args:
        text: The core insight text to slugify
        content_type: Content type suffix (e.g., "linkedin_post" -> "linkedin-post")
        max_words: Maximum number of words in the slug (default 6)

    Returns:
        Slug like "why-agents-need-memory-linkedin-post"
    """
    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)

    # Remove non-ASCII
    text = text.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    text = text.lower()

    # Remove punctuation, keep alphanumeric and spaces
    text = re.sub(r"[^a-z0-9\s]", "", text)

    # Split into words and take first max_words meaningful ones
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "shall",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "about", "that", "this", "it", "its", "and",
        "but", "or", "not", "no", "so", "if", "than", "too", "very",
    }

    words = [w for w in text.split() if w and w not in stop_words]
    slug_words = words[:max_words]

    if not slug_words:
        # Fallback: use first few words without stop word filtering
        slug_words = text.split()[:max_words]

    # Convert content_type from snake_case to kebab-case
    type_suffix = content_type.replace("_", "-")

    topic_slug = "-".join(slug_words)

    return f"{topic_slug}-{type_suffix}"


def generate_title_images(
    insight_text: str,
    output_dir: Path,
    count: int = TITLE_IMAGE_COUNT,
) -> list[str]:
    """
    Generate cinematic-lifestyle title images for a long-form post.

    Uses Nano Banana (Gemini 2.5 Flash Image) with cinematic-lifestyle B-roll style.

    Args:
        insight_text: The core insight text (used to craft prompts)
        output_dir: Directory to save images (e.g., subfolder/images/)
        count: Number of images to generate (default 3)

    Returns:
        List of paths to generated images
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find the generate_image.py script
    # __file__ is .claude/scripts/repurpose/generators/base.py
    # .parent x4 = .claude/
    claude_dir = Path(__file__).parent.parent.parent.parent
    script_path = claude_dir / "skills" / "nano-banana-image-generator" / "scripts" / "generate_image.py"

    if not script_path.exists():
        print(f"Warning: Nano Banana script not found at {script_path}")
        return []

    # Variation parameters for each image
    variations = [
        {"subject": "a tech founder", "emotion": "curious and engaged", "environment": "modern office with soft window light", "lighting": "morning golden hour"},
        {"subject": "a focused developer", "emotion": "determined and contemplative", "environment": "cozy home workspace", "lighting": "warm afternoon light"},
        {"subject": "a team collaborating", "emotion": "energized and connected", "environment": "bright coworking space", "lighting": "natural diffused light"},
        {"subject": "a thoughtful leader", "emotion": "visionary and calm", "environment": "minimalist cafe setting", "lighting": "golden hour side light"},
        {"subject": "a creative professional", "emotion": "inspired and focused", "environment": "studio with plants", "lighting": "soft overhead natural light"},
    ]

    generated = []
    # Truncate insight for prompt context
    topic_brief = insight_text[:150].strip()

    for i in range(min(count, len(variations))):
        v = variations[i]
        output_path = output_dir / f"title_{i+1:02d}.png"

        prompt = (
            f"Cinematic lifestyle photograph related to the concept: \"{topic_brief}\". "
            f"Show {v['subject']}, looking {v['emotion']}, in {v['environment']}. "
            f"Shot on Kodak Portra 400, 85mm f/1.4. Warm pastel tones, "
            f"muted low saturation, lifted shadows. {v['lighting']}. "
            f"Shallow depth of field. Candid moment, genuine emotion. "
            f"Blurred background with warm pastel red and light grey tones. "
            f"Aspect ratio: 16:9 horizontal."
        )

        try:
            result = subprocess.run(
                [
                    sys.executable, str(script_path),
                    prompt,
                    str(output_path),
                    "--aspect-ratio", "16:9",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(script_path.parent),
            )

            if result.returncode == 0 and output_path.exists():
                generated.append(str(output_path))
                print(f"  Generated title image {i+1}/{count}")
            else:
                print(f"  Warning: Failed to generate title image {i+1}/{count}")
                if result.stderr:
                    print(f"    {result.stderr[:200]}")
        except Exception as e:
            print(f"  Warning: Title image {i+1}/{count} error: {e}")

    return generated
