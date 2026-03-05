#!/bin/bash
# Twitter API v2 - Search Recent Tweets
# Returns tweets from last 7 days with timestamps and metrics

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
QUERY="$1"
MAX_RESULTS="${2:-50}"  # Default 50 tweets

if [ -z "$QUERY" ]; then
    echo "Usage: $0 <search_query> [max_results]" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 'AI agent' 50" >&2
    echo "  $0 'LangGraph OR CrewAI' 100" >&2
    exit 1
fi

# Validate max_results (10-100)
if [ "$MAX_RESULTS" -lt 10 ] || [ "$MAX_RESULTS" -gt 100 ]; then
    echo "Error: max_results must be between 10 and 100" >&2
    exit 1
fi

# API endpoint and parameters
METHOD="GET"
ENDPOINT="https://api.twitter.com/2/tweets/search/recent"

# Query parameters (will be added to URL)
QUERY_PARAMS=$(jq -n \
    --arg q "$QUERY" \
    --arg mr "$MAX_RESULTS" \
    '{
        "query": $q,
        "max_results": $mr,
        "tweet.fields": "created_at,public_metrics,author_id",
        "expansions": "author_id",
        "user.fields": "username,name,verified,public_metrics"
    }')

# Generate OAuth 1.0a Authorization header
AUTH_HEADER=$(python3 "$SCRIPT_DIR/oauth1_sign.py" \
    "$METHOD" \
    "$ENDPOINT" \
    "$QUERY_PARAMS" \
    "$API_KEY" \
    "$API_SECRET_KEY" \
    "$ACCESS_TOKEN" \
    "$ACCESS_TOKEN_SECRET")

if [ $? -ne 0 ]; then
    echo "Error: Failed to generate OAuth header" >&2
    exit 1
fi

# Build query string for curl
QUERY_STRING=$(echo "$QUERY_PARAMS" | python3 -c '
import json
import urllib.parse
import sys
params = json.load(sys.stdin)
print(urllib.parse.urlencode(params))
')

FULL_URL="${ENDPOINT}?${QUERY_STRING}"

# Make API call
RESPONSE=$(curl -sS -X "$METHOD" \
    -H "Authorization: $AUTH_HEADER" \
    "$FULL_URL")

# Check for errors
if echo "$RESPONSE" | jq -e '.errors' > /dev/null 2>&1; then
    echo "API Error:" >&2
    echo "$RESPONSE" | jq '.errors' >&2
    exit 1
fi

# Output clean JSON
echo "$RESPONSE" | jq '.'
