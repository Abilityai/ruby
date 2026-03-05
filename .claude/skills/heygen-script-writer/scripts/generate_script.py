#!/usr/bin/env python3
"""
Generate HeyGen video scripts following the creator's voice profile.

Usage:
    python generate_script.py "Topic or prompt"
    python generate_script.py "Topic" --pillar "Deep Agent Architecture" --hook scary
    python generate_script.py "Topic" --output /path/to/script.md
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Script constraints
MAX_WORDS = 85
MIN_WORDS = 65
MAX_DURATION = 30  # seconds
WORDS_PER_SECOND = 2.8  # Average speaking rate

# HeyGen configuration
AVATAR_ID = "${HEYGEN_AVATAR_ID}"
VOICE_ID = "${HEYGEN_VOICE_ID}"

CONTENT_PILLARS = [
    "Deep Agent Architecture",
    "AI Adoption Psychology",
    "Shallow vs Deep",
    "Production Patterns",
    "Founder Lessons"
]

HOOK_TYPES = ["scary", "strange", "sexy", "free_value", "familiar"]

SCRIPT_TEMPLATE = """---
topic: {topic}
pillar: {pillar}
hook_type: {hook_type}
word_count: {word_count}
estimated_duration: {duration} seconds
avatar_id: {avatar_id}
voice_id: {voice_id}
generated_at: {timestamp}
---

{script}
"""

EXAMPLE_STRUCTURES = {
    "scary": [
        "Your {topic} is broken. Here's why.",
        "Most people get {topic} completely wrong.",
        "The hidden cost of ignoring {topic}."
    ],
    "strange": [
        "I stopped doing {topic} the normal way.",
        "Here's the counterintuitive truth about {topic}.",
        "Everyone says do X. I do the opposite."
    ],
    "sexy": [
        "This one pattern changed everything about {topic}.",
        "How I 10x'd my results with {topic}.",
        "The secret to mastering {topic}."
    ],
    "free_value": [
        "The 4 components of {topic} you need to know.",
        "My complete checklist for {topic}.",
        "How to actually implement {topic}."
    ],
    "familiar": [
        "Remember when we thought {topic} was simple?",
        "Every developer makes this {topic} mistake.",
        "I used to think {topic} didn't matter."
    ]
}


def count_words(text: str) -> int:
    """Count words in text, excluding metadata."""
    # Remove any YAML frontmatter if present
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    return len(text.split())


def estimate_duration(word_count: int) -> float:
    """Estimate speaking duration in seconds."""
    return round(word_count / WORDS_PER_SECOND, 1)


def generate_script_outline(topic: str, hook_type: str) -> str:
    """Generate a script outline based on topic and hook type."""

    outline = f"""# Script Outline for: {topic}

## Structure (30 seconds, ~80 words)

### HOOK (5 sec, ~15 words)
{EXAMPLE_STRUCTURES.get(hook_type, EXAMPLE_STRUCTURES['strange'])[0].format(topic=topic)}

### CONTEXT (8 sec, ~25 words)
Set up the problem or misconception about {topic}.

### INSIGHT (12 sec, ~35 words)
Deliver the key insight or contrarian take on {topic}.

### CURIOSITY HOOK (5 sec, ~10 words)
End with intrigue about {topic}, not a hard CTA.

---

## Writing Guidelines

DO:
- Start mid-thought ("Here's the thing about...")
- Use conversational contractions
- Include one specific example or number
- End with curiosity

DON'T:
- Start with greetings ("Hey everyone")
- Use corporate speak
- Include calls-to-action
- Exceed 85 words

---

## Draft Your Script Below:

[Write your ~80 word script here following the structure above]
"""
    return outline


def validate_script(script: str) -> dict:
    """Validate a script meets requirements."""
    word_count = count_words(script)
    duration = estimate_duration(word_count)

    issues = []

    if word_count > MAX_WORDS:
        issues.append(f"Too long: {word_count} words (max {MAX_WORDS})")
    if word_count < MIN_WORDS:
        issues.append(f"Too short: {word_count} words (min {MIN_WORDS})")
    if duration > MAX_DURATION:
        issues.append(f"Duration ~{duration}s exceeds {MAX_DURATION}s")

    # Check for common issues
    lower_script = script.lower()
    if lower_script.startswith("hey ") or lower_script.startswith("hi "):
        issues.append("Avoid starting with greetings")
    if "subscribe" in lower_script or "follow me" in lower_script:
        issues.append("Avoid direct CTAs")

    return {
        "valid": len(issues) == 0,
        "word_count": word_count,
        "duration": duration,
        "issues": issues
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate HeyGen video scripts",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("topic", help="Topic or prompt for the script")
    parser.add_argument("--pillar", choices=CONTENT_PILLARS,
                        default="Deep Agent Architecture",
                        help="Content pillar")
    parser.add_argument("--hook", choices=HOOK_TYPES,
                        default="strange",
                        help="Hook type (3S+2F framework)")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--validate", "-v", help="Validate an existing script file")

    args = parser.parse_args()

    # If validating an existing script
    if args.validate:
        script_path = Path(args.validate)
        if not script_path.exists():
            print(f"Error: File not found: {args.validate}")
            sys.exit(1)

        script = script_path.read_text()
        result = validate_script(script)

        print(f"Script: {args.validate}")
        print(f"Word count: {result['word_count']}")
        print(f"Estimated duration: {result['duration']} seconds")

        if result['valid']:
            print("Status: VALID")
        else:
            print("Status: ISSUES FOUND")
            for issue in result['issues']:
                print(f"  - {issue}")

        sys.exit(0 if result['valid'] else 1)

    # Generate script outline
    outline = generate_script_outline(args.topic, args.hook)

    # Create metadata for when script is completed
    metadata = {
        "topic": args.topic,
        "pillar": args.pillar,
        "hook_type": args.hook,
        "word_count": "[TBD]",
        "duration": "[TBD]",
        "avatar_id": AVATAR_ID,
        "voice_id": VOICE_ID,
        "timestamp": datetime.now().isoformat()
    }

    output = outline

    # Save or print
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output)
        print(f"Script outline saved to: {args.output}")
    else:
        print(output)

    print(f"\nHeyGen Config:")
    print(f"  Avatar ID: {AVATAR_ID}")
    print(f"  Voice ID: {VOICE_ID}")
    print(f"  Max duration: {MAX_DURATION}s")
    print(f"  Target words: {MIN_WORDS}-{MAX_WORDS}")


if __name__ == "__main__":
    main()
