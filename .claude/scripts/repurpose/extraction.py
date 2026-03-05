"""
Content extraction module for CEO Content Engine.

Extracts actionable insights from video transcripts using Gemini AI.
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from config import Config


def load_transcript(folder_path: str) -> Optional[str]:
    """
    Load transcript.md from a folder.

    Args:
        folder_path: Path to the folder containing transcript.md

    Returns:
        Transcript content as string, or None if not found
    """
    transcript_path = Path(folder_path) / "transcript.md"

    if not transcript_path.exists():
        print(f"Error: transcript.md not found in {folder_path}")
        return None

    try:
        content = transcript_path.read_text()
        return content.strip()
    except IOError as e:
        print(f"Error reading transcript: {e}")
        return None


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def load_extraction_prompt() -> str:
    """Load the content extraction template."""
    templates_dir = Config.get_templates_dir()
    prompt_path = Path(templates_dir) / "content_extraction.md"

    if prompt_path.exists():
        return prompt_path.read_text()

    # Fallback prompt if file not found
    return """
    Extract 3-5 key insights from this transcript.
    Return as JSON with fields: insights (array with core_insight, scores, quotable_moments,
    thought_leadership_angle, supporting_context, potential_formats), transcript_summary, primary_topic.
    """


def call_gemini_api(prompt: str, model: str = None) -> Optional[str]:
    """
    Call Gemini API via the AI Studio MCP or direct API.

    Args:
        prompt: The prompt to send
        model: Model name (defaults to primary from config)

    Returns:
        Response text or None on error
    """
    if model is None:
        model = Config.GEMINI_MODELS["primary"]

    api_key = Config.get_gemini_api_key()
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        return None

    # Use direct Gemini API via curl
    import tempfile

    # Create the request body
    request_body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        }
    }

    # Write request to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(request_body, f)
        request_file = f.name

    try:
        # Call Gemini API
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST",
                "-H", "Content-Type: application/json",
                "-d", f"@{request_file}",
                api_url
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            print(f"Gemini API call failed: {result.stderr}")
            return None

        response = json.loads(result.stdout)

        # Check for errors
        if "error" in response:
            error_msg = response["error"].get("message", "Unknown error")
            print(f"Gemini API error: {error_msg}")

            # Try fallback model
            if model == Config.GEMINI_MODELS["primary"]:
                print(f"Trying fallback model: {Config.GEMINI_MODELS['fallback']}")
                return call_gemini_api(prompt, Config.GEMINI_MODELS["fallback"])
            return None

        # Extract text from response
        candidates = response.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return parts[0].get("text", "")

        print("No content in Gemini response")
        return None

    except json.JSONDecodeError as e:
        print(f"Error parsing Gemini response: {e}")
        return None
    except subprocess.TimeoutExpired:
        print("Gemini API call timed out")
        return None
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None
    finally:
        # Clean up temp file
        try:
            os.unlink(request_file)
        except:
            pass


def extract_json_from_response(response: str) -> Optional[dict]:
    """
    Extract JSON from Gemini response, handling code blocks.

    Args:
        response: Raw response text from Gemini

    Returns:
        Parsed JSON dict or None
    """
    if not response:
        return None

    # Try to find JSON in code blocks
    json_patterns = [
        r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
        r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
        r'\{[\s\S]*\}',                   # Raw JSON object
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, response)
        for match in matches:
            try:
                # Clean up the match
                json_str = match.strip()
                if json_str.startswith('{'):
                    return json.loads(json_str)
            except json.JSONDecodeError:
                continue

    # Last resort: try parsing the entire response
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass

    return None


def validate_insight(insight: dict) -> tuple[bool, list[str]]:
    """
    Validate an extracted insight.

    Args:
        insight: Insight dictionary

    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []

    # Required fields
    required_fields = [
        "core_insight",
        "scores",
        "quotable_moments",
        "thought_leadership_angle",
        "supporting_context",
    ]

    for field in required_fields:
        if field not in insight or not insight[field]:
            issues.append(f"Missing or empty field: {field}")

    # Validate scores
    scores = insight.get("scores", {})
    score_fields = ["impact", "clarity", "uniqueness", "actionability"]
    for score_field in score_fields:
        if score_field in scores:
            value = scores[score_field]
            if not isinstance(value, (int, float)) or value < 1 or value > 10:
                issues.append(f"Invalid score for {score_field}: {value}")

    # Validate quotable_moments is a list
    quotes = insight.get("quotable_moments", [])
    if not isinstance(quotes, list) or len(quotes) < 2:
        issues.append("quotable_moments must be a list with at least 2 items")

    # Validate potential_formats
    formats = insight.get("potential_formats", [])
    valid_formats = ["twitter_thread", "linkedin_post", "linkedin_carousel",
                     "text_post", "community_post", "newsletter", "framer_cms"]
    for fmt in formats:
        if fmt not in valid_formats:
            issues.append(f"Invalid format: {fmt}")

    return len(issues) == 0, issues


def validate_extraction_result(result: dict) -> tuple[bool, list[str]]:
    """
    Validate the complete extraction result.

    Args:
        result: Extraction result dictionary

    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []

    # Check for error response
    if "error" in result:
        return False, [f"Extraction error: {result.get('reason', 'Unknown')}"]

    # Required top-level fields
    if "insights" not in result or not result["insights"]:
        issues.append("No insights extracted")
        return False, issues

    # Validate each insight
    insights = result.get("insights", [])
    if len(insights) < 2:
        issues.append(f"Too few insights: {len(insights)} (need at least 2)")
    elif len(insights) > 5:
        issues.append(f"Too many insights: {len(insights)} (max 5)")

    for i, insight in enumerate(insights):
        valid, insight_issues = validate_insight(insight)
        if not valid:
            for issue in insight_issues:
                issues.append(f"Insight {i+1}: {issue}")

    return len(issues) == 0, issues


def format_feedback_for_extraction(feedback: str) -> str:
    """
    Format user feedback as an extraction directive.

    Args:
        feedback: Processed feedback string

    Returns:
        Formatted feedback section for extraction prompt
    """
    if not feedback or feedback == "NO_FEEDBACK":
        return ""

    return f"""

---

## USER DIRECTION (IMPORTANT)

The user has provided specific direction for this content extraction. **Prioritize insights that align with this feedback:**

{feedback}

**Apply this direction to:**
1. Which insights to extract (prioritize topics mentioned in feedback)
2. How to score insights (boost scores for insights matching user direction)
3. Which quotable moments to highlight (favor quotes related to feedback themes)
4. Format recommendations (consider feedback when suggesting formats)

This feedback should influence your extraction priorities while still following the standard extraction framework.
"""


def extract_insights(transcript: str, verbose: bool = True, user_feedback: str = None) -> Optional[dict]:
    """
    Extract insights from a transcript using Gemini.

    Args:
        transcript: The transcript text
        verbose: Whether to print progress messages
        user_feedback: Optional user feedback to guide extraction priorities

    Returns:
        Extraction result dictionary or None on failure
    """
    if verbose:
        print("Loading extraction prompt...")

    extraction_prompt = load_extraction_prompt()

    # Add feedback section if provided
    feedback_section = ""
    if user_feedback and user_feedback != "NO_FEEDBACK":
        feedback_section = format_feedback_for_extraction(user_feedback)
        if verbose:
            print("Applying user feedback to extraction...")

    # Combine prompt with transcript and feedback
    full_prompt = f"""{extraction_prompt}
{feedback_section}
---

## TRANSCRIPT TO ANALYZE:

{transcript}
"""

    if verbose:
        word_count = count_words(transcript)
        print(f"Transcript: {word_count} words")
        print("Calling Gemini API for insight extraction...")

    # Call Gemini
    response = call_gemini_api(full_prompt)

    if not response:
        print("Failed to get response from Gemini")
        return None

    if verbose:
        print("Parsing extraction response...")

    # Parse JSON from response
    result = extract_json_from_response(response)

    if not result:
        print("Failed to parse JSON from Gemini response")
        print("Raw response (first 500 chars):")
        print(response[:500])
        return None

    # Validate result
    is_valid, issues = validate_extraction_result(result)

    if not is_valid:
        print("Extraction result validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        # Return result anyway for debugging, but mark it
        result["_validation_issues"] = issues

    # ENFORCE cap at 5 insights - keep highest scored
    MAX_INSIGHTS = 5
    insights = result.get("insights", [])
    if len(insights) > MAX_INSIGHTS:
        print(f"Capping insights from {len(insights)} to {MAX_INSIGHTS} (keeping highest scored)")
        # Sort by overall_score descending, keep top 5
        insights.sort(
            key=lambda x: x.get("scores", {}).get("overall_score", 0),
            reverse=True
        )
        result["insights"] = insights[:MAX_INSIGHTS]
        # Re-number the insights
        for i, insight in enumerate(result["insights"], 1):
            insight["id"] = i

    if verbose:
        insight_count = len(result.get("insights", []))
        print(f"Extracted {insight_count} insights")

    return result


def extract_from_folder(folder_path: str, verbose: bool = True, user_feedback: str = None) -> Optional[dict]:
    """
    Extract insights from a folder's transcript.md.

    Args:
        folder_path: Path to folder containing transcript.md
        verbose: Whether to print progress
        user_feedback: Optional user feedback to guide extraction priorities

    Returns:
        Extraction result or None
    """
    if verbose:
        print(f"Extracting insights from: {folder_path}")

    # Load transcript
    transcript = load_transcript(folder_path)
    if not transcript:
        return None

    # Extract insights
    return extract_insights(transcript, verbose, user_feedback)


def format_insights_summary(result: dict) -> str:
    """
    Format extraction result as a readable summary.

    Args:
        result: Extraction result dictionary

    Returns:
        Formatted string summary
    """
    lines = []
    lines.append("=" * 60)
    lines.append("EXTRACTION SUMMARY")
    lines.append("=" * 60)

    if "transcript_summary" in result:
        lines.append(f"\nSummary: {result['transcript_summary']}")

    if "primary_topic" in result:
        lines.append(f"Topic: {result['primary_topic']}")

    insights = result.get("insights", [])
    lines.append(f"\nInsights: {len(insights)}")
    lines.append("-" * 60)

    for insight in insights:
        insight_num = insight.get("insight_number", "?")
        core = insight.get("core_insight", "N/A")
        scores = insight.get("scores", {})
        overall = scores.get("overall_score", 0)

        lines.append(f"\n[Insight {insight_num}] Score: {overall}")
        lines.append(f"  {core[:100]}...")

        quotes = insight.get("quotable_moments", [])
        if quotes:
            lines.append(f"  Quotes: {len(quotes)}")

        formats = insight.get("potential_formats", [])
        if formats:
            lines.append(f"  Formats: {', '.join(formats)}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Content Extraction")
    parser.add_argument("folder", nargs="?", help="Folder containing transcript.md")
    parser.add_argument("--test", action="store_true", help="Run with test transcript")
    parser.add_argument("--output", "-o", help="Output file for JSON result")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")

    args = parser.parse_args()

    if args.test:
        # Use test transcript from resources
        test_folder = str(Config.get_project_root() / "resources" / "temp" / "Test")
        result = extract_from_folder(test_folder, verbose=not args.quiet)
    elif args.folder:
        result = extract_from_folder(args.folder, verbose=not args.quiet)
    else:
        parser.print_help()
        sys.exit(1)

    if result:
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Result saved to: {args.output}")
        else:
            print(format_insights_summary(result))
    else:
        print("Extraction failed")
        sys.exit(1)
