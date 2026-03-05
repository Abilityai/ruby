#!/bin/bash
# Twitter API v2 - Get User Details by ID or Username
# Returns user profile including follower count and verification status

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
IDENTIFIER="$1"
LOOKUP_TYPE="${2:-id}"  # Default to 'id', can be 'username'

if [ -z "$IDENTIFIER" ]; then
    echo "Usage: $0 <user_id|username> [id|username]" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 2244994945 id          # Lookup by user ID" >&2
    echo "  $0 TwitterDev username    # Lookup by username" >&2
    exit 1
fi

# Set endpoint based on lookup type
if [ "$LOOKUP_TYPE" = "username" ]; then
    ENDPOINT="https://api.twitter.com/2/users/by/username/${IDENTIFIER}"
else
    ENDPOINT="https://api.twitter.com/2/users/${IDENTIFIER}"
fi

# API method and parameters
METHOD="GET"

# Query parameters
QUERY_PARAMS=$(jq -n \
    '{
        "user.fields": "created_at,description,location,public_metrics,verified,profile_image_url"
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
