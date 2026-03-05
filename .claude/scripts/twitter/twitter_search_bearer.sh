#!/bin/bash
# Twitter API v2 - Search Recent Tweets (Bearer Token Auth)
# Returns tweets from last 7 days with timestamps and metrics
# Uses OAuth 2.0 Bearer Token (simpler than OAuth 1.0a)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Load Bearer Token from .mcp.json or use environment variable
if [ -n "$TWITTER_BEARER_TOKEN" ]; then
    BEARER_TOKEN="$TWITTER_BEARER_TOKEN"
else
    # Try to load from a config file if it exists
    CONFIG_FILE="$SCRIPT_DIR/twitter_config.sh"
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
    else
        echo "Error: TWITTER_BEARER_TOKEN not set" >&2
        echo "" >&2
        echo "Set environment variable:" >&2
        echo "  export TWITTER_BEARER_TOKEN='your_bearer_token'" >&2
        echo "" >&2
        echo "Or create $CONFIG_FILE with:" >&2
        echo "  BEARER_TOKEN='your_bearer_token'" >&2
        exit 1
    fi
fi

# Parse arguments
QUERY="$1"
MAX_RESULTS="${2:-50}"  # Default 50 tweets

if [ -z "$QUERY" ]; then
    echo "Usage: $0 <search_query> [max_results]" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 'AI agent' 50" >&2
    echo "  $0 'LangGraph OR CrewAI' 100" >&2
    echo "  $0 'AI adoption -filter:retweets lang:en' 50" >&2
    exit 1
fi

# Validate max_results (10-100)
if [ "$MAX_RESULTS" -lt 10 ] || [ "$MAX_RESULTS" -gt 100 ]; then
    echo "Error: max_results must be between 10 and 100" >&2
    exit 1
fi

# Build API URL with parameters
BASE_URL="https://api.twitter.com/2/tweets/search/recent"

# URL encode the query
ENCODED_QUERY=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$QUERY'))")

# Build full URL with all parameters
# Note: reply_settings field tells us who can reply (everyone, following, mentionedUsers)
FULL_URL="${BASE_URL}?query=${ENCODED_QUERY}&max_results=${MAX_RESULTS}&tweet.fields=created_at,public_metrics,author_id,conversation_id,lang,reply_settings&expansions=author_id&user.fields=username,name,verified,public_metrics"

# Make API call with Bearer Token
RESPONSE=$(curl -sS -X GET \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    "$FULL_URL")

# Check for errors
if echo "$RESPONSE" | jq -e '.errors' > /dev/null 2>&1; then
    echo "API Error:" >&2
    echo "$RESPONSE" | jq '.errors' >&2
    exit 1
fi

# Check for rate limit info in case of 429
if echo "$RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
    STATUS=$(echo "$RESPONSE" | jq -r '.status')
    if [ "$STATUS" = "429" ]; then
        echo "Rate limit exceeded. Please wait before making more requests." >&2
        exit 1
    fi
fi

# Output clean JSON
echo "$RESPONSE" | jq '.'
