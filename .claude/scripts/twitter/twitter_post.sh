#!/bin/bash
# Twitter API v2 - Post Tweet / Reply
# Uses OAuth 1.0a for user context authentication

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Load credentials from .mcp.json
API_KEY=$(jq -r '.mcpServers."twitter-mcp".env.API_KEY' "$AGENT_ROOT/.mcp.json")
API_SECRET_KEY=$(jq -r '.mcpServers."twitter-mcp".env.API_SECRET_KEY' "$AGENT_ROOT/.mcp.json")
ACCESS_TOKEN=$(jq -r '.mcpServers."twitter-mcp".env.ACCESS_TOKEN' "$AGENT_ROOT/.mcp.json")
ACCESS_TOKEN_SECRET=$(jq -r '.mcpServers."twitter-mcp".env.ACCESS_TOKEN_SECRET' "$AGENT_ROOT/.mcp.json")

# Check if credentials loaded
if [ "$API_KEY" = "null" ] || [ -z "$API_KEY" ]; then
    echo "Error: Could not load Twitter API credentials from .mcp.json" >&2
    exit 1
fi

# Parse arguments
TWEET_TEXT="$1"
REPLY_TO_ID="$2"  # Optional - if provided, this is a reply

if [ -z "$TWEET_TEXT" ]; then
    echo "Usage: $0 <tweet_text> [reply_to_tweet_id]" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 'Hello world!'" >&2
    echo "  $0 'This is a reply' 1234567890123456789" >&2
    exit 1
fi

# Check character limit
CHAR_COUNT=${#TWEET_TEXT}
if [ "$CHAR_COUNT" -gt 280 ]; then
    echo "Error: Tweet exceeds 280 characters ($CHAR_COUNT chars)" >&2
    exit 1
fi

# API endpoint
METHOD="POST"
ENDPOINT="https://api.twitter.com/2/tweets"

# Build JSON body
if [ -n "$REPLY_TO_ID" ]; then
    JSON_BODY=$(jq -n \
        --arg text "$TWEET_TEXT" \
        --arg reply_id "$REPLY_TO_ID" \
        '{
            "text": $text,
            "reply": {
                "in_reply_to_tweet_id": $reply_id
            }
        }')
else
    JSON_BODY=$(jq -n --arg text "$TWEET_TEXT" '{"text": $text}')
fi

# Generate OAuth 1.0a Authorization header (POST with no query params - body is separate)
AUTH_HEADER=$(python3 "$SCRIPT_DIR/oauth1_sign.py" \
    "$METHOD" \
    "$ENDPOINT" \
    "{}" \
    "$API_KEY" \
    "$API_SECRET_KEY" \
    "$ACCESS_TOKEN" \
    "$ACCESS_TOKEN_SECRET")

if [ $? -ne 0 ]; then
    echo "Error: Failed to generate OAuth header" >&2
    exit 1
fi

# Make API call
RESPONSE=$(curl -sS -X "$METHOD" \
    -H "Authorization: $AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "$JSON_BODY" \
    "$ENDPOINT")

# Check for errors
if echo "$RESPONSE" | jq -e '.errors' > /dev/null 2>&1; then
    echo "API Error:" >&2
    echo "$RESPONSE" | jq '.errors' >&2
    exit 1
fi

# Check for rate limit
if echo "$RESPONSE" | jq -e '.status == 429' > /dev/null 2>&1; then
    echo "Rate limit exceeded" >&2
    exit 1
fi

# Output result
TWEET_ID=$(echo "$RESPONSE" | jq -r '.data.id // "unknown"')
echo "Posted successfully!"
echo "Tweet ID: $TWEET_ID"
echo "$RESPONSE" | jq '.'
