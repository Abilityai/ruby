"""
Feedback processing utilities for CEO Content Engine.

Processes user feedback for both extraction and generation stages.
"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


def load_feedback_template() -> str:
    """Load the feedback processing template."""
    templates_dir = Config.get_templates_dir()
    template_path = Path(templates_dir) / "feedback_processing.md"

    if template_path.exists():
        return template_path.read_text()

    return ""


def call_gemini_for_feedback(prompt: str, model: str = None) -> Optional[str]:
    """
    Call Gemini API for feedback processing.

    Args:
        prompt: The prompt to send
        model: Model name (defaults to primary from config)

    Returns:
        Response text or None on error
    """
    if model is None:
        model = Config.GEMINI_MODELS.get("primary", "gemini-2.5-flash")

    api_key = Config.get_gemini_api_key()
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        return None

    request_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,  # Lower temperature for consistent processing
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024,
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
            capture_output=True, text=True, timeout=60,
        )

        if result.returncode != 0:
            return None

        response = json.loads(result.stdout)

        if "error" in response:
            return None

        candidates = response.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()

        return None

    except Exception as e:
        print(f"Error processing feedback: {e}")
        return None
    finally:
        try:
            os.unlink(request_file)
        except:
            pass


def is_no_feedback(feedback: str) -> bool:
    """
    Check if feedback string indicates no feedback.

    Args:
        feedback: Raw feedback string

    Returns:
        True if no feedback, False otherwise
    """
    if not feedback:
        return True

    feedback_lower = feedback.strip().lower()

    # Common "no feedback" patterns
    no_feedback_patterns = [
        "no", "nope", "no feedback", "no ideas", "nothing",
        "all good", "looks good", "looks great", "fine", "ok", "okay",
        "proceed", "go ahead", "continue",
        "n/a", "na", "skip", "pass", "-", "none",
        "no_feedback"
    ]

    return feedback_lower in no_feedback_patterns


def process_feedback(raw_feedback: str, verbose: bool = False) -> str:
    """
    Process raw user feedback into structured instructions.

    Uses the feedback_processing.md template via Gemini to transform
    raw feedback into actionable instructions for generators.

    Args:
        raw_feedback: Raw user feedback string
        verbose: Whether to print processing messages

    Returns:
        Processed feedback string, or "NO_FEEDBACK" if no feedback
    """
    # Quick check for obvious "no feedback" cases
    if is_no_feedback(raw_feedback):
        return "NO_FEEDBACK"

    # Load the feedback processing template
    template = load_feedback_template()

    if not template:
        # If template not found, return feedback as-is (cleaned up)
        if verbose:
            print("Warning: Feedback template not found, using raw feedback")
        return raw_feedback.strip()

    # Build the prompt
    input_data = {"message": raw_feedback}

    full_prompt = f"""{template}

---

## INPUT:

```json
{json.dumps(input_data, indent=2)}
```

Process the message above and return either plain text instructions or "NO_FEEDBACK".
"""

    if verbose:
        print("Processing feedback...")

    # Call Gemini to process the feedback
    result = call_gemini_for_feedback(full_prompt)

    if not result:
        # If Gemini fails, return feedback as-is
        if verbose:
            print("Warning: Feedback processing failed, using raw feedback")
        return raw_feedback.strip()

    # Clean up the result
    result = result.strip()

    # Check if result is NO_FEEDBACK
    if result.upper() == "NO_FEEDBACK":
        return "NO_FEEDBACK"

    return result


def format_feedback_for_extraction(processed_feedback: str) -> str:
    """
    Format processed feedback specifically for the extraction stage.

    This creates a section that can be appended to the extraction prompt
    to guide what insights to prioritize.

    Args:
        processed_feedback: Processed feedback string

    Returns:
        Formatted feedback section for extraction prompt
    """
    if processed_feedback == "NO_FEEDBACK" or not processed_feedback:
        return ""

    return f"""

---

## USER DIRECTION (IMPORTANT)

The user has provided specific direction for this content extraction. **Prioritize insights that align with this feedback:**

{processed_feedback}

**Apply this direction to:**
1. Which insights to extract (prioritize topics mentioned in feedback)
2. How to score insights (boost scores for insights matching user direction)
3. Which quotable moments to highlight (favor quotes related to feedback themes)
4. Format recommendations (consider feedback when suggesting formats)

This feedback should influence your extraction priorities while still following the standard extraction framework.
"""


def format_feedback_for_generation(processed_feedback: str) -> str:
    """
    Format processed feedback for the generation stage.

    Args:
        processed_feedback: Processed feedback string

    Returns:
        Feedback string ready for generators (or "NO_FEEDBACK")
    """
    if processed_feedback == "NO_FEEDBACK" or not processed_feedback:
        return "NO_FEEDBACK"

    return processed_feedback
