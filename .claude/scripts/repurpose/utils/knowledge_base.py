"""
the knowledge base agent Integration Module.

Provides optional integration with the knowledge base agent knowledge base agent
for enriching content with the creator's authentic perspective.
"""

import json
import subprocess
import os
from pathlib import Path
from typing import Optional
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


def is_knowledge_base_available() -> bool:
    """
    Check if the knowledge base agent is available for use.

    Returns:
        True if the knowledge base agent path exists
    """
    knowledge_base_path = Path(Config.knowledge_base_path())
    return knowledge_base_path.exists()


def query_knowledge_base(
    prompt: str,
    timeout: int = 120,
) -> Optional[dict]:
    """
    Query the knowledge base knowledge base agent.

    Args:
        prompt: The query prompt for the knowledge base agent
        timeout: Timeout in seconds

    Returns:
        the knowledge base agent response dict or None if unavailable/failed
    """
    knowledge_base_path = Path(Config.knowledge_base_path())

    if not knowledge_base_path.exists():
        print(f"Warning: the knowledge base agent path not found: {knowledge_base_path}")
        return None

    try:
        # Run claude command in the knowledge base agent directory
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(knowledge_base_path),
        )

        if result.returncode != 0:
            print(f"the knowledge base agent query failed: {result.stderr}")
            return None

        # Parse JSON response
        response = json.loads(result.stdout)
        return response

    except subprocess.TimeoutExpired:
        print("the knowledge base agent query timed out")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse the knowledge base agent response: {e}")
        return None
    except FileNotFoundError:
        print("Error: 'claude' command not found")
        return None
    except Exception as e:
        print(f"the knowledge base agent query error: {e}")
        return None


def get_perspective(topic: str) -> Optional[str]:
    """
    Get the creator's perspective on a topic via knowledge base agent.

    Args:
        topic: The topic to get perspective on

    Returns:
        Perspective text or None
    """
    prompt = f"""
    I need the creator's unique perspective on this topic for content creation.
    Return a 2-3 paragraph response with:
    1. the creator's contrarian or distinctive viewpoint
    2. Supporting examples or experiences
    3. Key quotable phrases in the creator's voice

    Topic: {topic}
    """

    response = query_knowledge_base(prompt)

    if response and "result" in response:
        return response["result"]

    return None


def enrich_insight(insight: dict) -> dict:
    """
    Enrich an insight with the knowledge base agent perspective.

    Args:
        insight: The insight dictionary to enrich

    Returns:
        Enriched insight dictionary
    """
    if not is_knowledge_base_available():
        insight["knowledge_base_enriched"] = False
        return insight

    core_insight = insight.get("core_insight", "")
    topic = insight.get("thought_leadership_angle", core_insight)

    print(f"Querying the knowledge base for perspective on: {topic[:50]}...")

    perspective = get_perspective(topic)

    if perspective:
        # Add the knowledge base agent perspective to supporting context
        existing_context = insight.get("supporting_context", "")
        insight["supporting_context"] = f"{existing_context}\n\n[the knowledge base agent]: {perspective}"
        insight["knowledge_base_enriched"] = True
        print("Insight enriched with the knowledge base agent perspective")
    else:
        insight["knowledge_base_enriched"] = False
        print("Could not get the knowledge base agent perspective")

    return insight


def get_related_content(topic: str, limit: int = 5) -> list[dict]:
    """
    Find related content from the knowledge base agent knowledge base.

    Args:
        topic: Topic to search for
        limit: Maximum number of results

    Returns:
        List of related content items
    """
    prompt = f"""
    Find up to {limit} pieces of related content from the knowledge base
    that relate to this topic. Return as JSON array with fields:
    title, summary, relevance_score (1-10).

    Topic: {topic}
    """

    response = query_knowledge_base(prompt)

    if response and "result" in response:
        try:
            # Try to parse as JSON
            result = response["result"]
            if isinstance(result, list):
                return result
            elif isinstance(result, str):
                return json.loads(result)
        except:
            pass

    return []


def print_knowledge_base_status() -> None:
    """Print the knowledge base agent integration status."""
    print("=" * 50)
    print("the knowledge base agent Integration Status")
    print("=" * 50)
    print(f"Path: {Config.knowledge_base_path()}")

    knowledge_base_path = Path(Config.knowledge_base_path())
    path_exists = knowledge_base_path.exists()
    print(f"Path exists: {path_exists}")
    print(f"Status: {'AVAILABLE' if path_exists else 'PATH NOT FOUND'}")

    print("=" * 50)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="the knowledge base agent Integration")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--query", type=str, help="Send a query")
    parser.add_argument("--perspective", type=str, help="Get perspective on topic")

    args = parser.parse_args()

    if args.status:
        print_knowledge_base_status()
    elif args.query:
        response = query_knowledge_base(args.query)
        if response:
            print(json.dumps(response, indent=2))
        else:
            print("Query failed")
    elif args.perspective:
        perspective = get_perspective(args.perspective)
        if perspective:
            print(perspective)
        else:
            print("Could not get perspective")
    else:
        print_knowledge_base_status()
