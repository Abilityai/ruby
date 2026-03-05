#!/usr/bin/env python3
"""
Helper script to post Twitter replies via MCP
Called by post_twitter_replies.sh
"""

import sys
import json
import subprocess

def post_tweet(text, reply_to_id):
    """Post a tweet using Claude Code in headless mode"""

    # Escape quotes in the text
    text_escaped = text.replace('"', '\\"')

    # Build the prompt for Claude
    prompt = f'''Post this reply to Twitter using the twitter-mcp tool:

Reply text: "{text_escaped}"
Reply to tweet ID: {reply_to_id}

Use mcp__twitter-mcp__post_tweet with:
- text: the reply text above
- reply_to_tweet_id: {reply_to_id}

Return only the new tweet ID as JSON: {{"tweet_id": "..."}}"
'''

    # Call Claude Code in headless mode
    result = subprocess.run(
        ['claude', '-p', prompt, '--output-format', 'json'],
        capture_output=True,
        text=True,
        cwd='${AGENT_ROOT}'
    )

    if result.returncode != 0:
        print(json.dumps({"error": result.stderr}), file=sys.stderr)
        sys.exit(1)

    # Parse Claude's response
    try:
        response = json.loads(result.stdout)
        if response.get('is_error'):
            print(json.dumps({"error": response.get('result')}), file=sys.stderr)
            sys.exit(1)

        # Extract tweet ID from result
        # This is a simplified version - in reality, we'd parse Claude's response more carefully
        print(json.dumps({"tweet_id": "posted", "status": "success"}))

    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Failed to parse response: {str(e)}"}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: post_tweet_helper.py <reply_text> <tweet_id>", file=sys.stderr)
        sys.exit(1)

    reply_text = sys.argv[1]
    tweet_id = sys.argv[2]

    post_tweet(reply_text, tweet_id)
