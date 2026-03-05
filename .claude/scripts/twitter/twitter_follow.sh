#!/bin/bash
# twitter_follow.sh - Follow a user on Twitter using API v2 with OAuth 1.0a
# Usage: ./twitter_follow.sh <target_user_id>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load credentials from MCP config or environment
API_KEY="${API_KEY:-TN7acvy3pm5XPwNGIfgeAujCz}"
API_SECRET="${API_SECRET_KEY:-BSxoF9qKXnuskFd1VM0v6zht0AQCX69VZB7qitN9FB5Q27xS37}"
ACCESS_TOKEN="${ACCESS_TOKEN:-${TWITTER_ACCESS_TOKEN}}"
ACCESS_TOKEN_SECRET="${ACCESS_TOKEN_SECRET:-NMkhuQyr5wf0sXD5CptoCdBWNn7KaWTeG5V8N1PAu7INH}"

# Our user ID (the creator's account)
MY_USER_ID="${TWITTER_USER_ID}"

TARGET_USER_ID="$1"

if [ -z "$TARGET_USER_ID" ]; then
    echo "Usage: $0 <target_user_id>" >&2
    echo "Example: $0 2728439146" >&2
    exit 1
fi

# API endpoint for following
URL="https://api.twitter.com/2/users/${MY_USER_ID}/following"

# Generate OAuth header (POST with JSON body - params empty for signature)
AUTH_HEADER=$(python3 "$SCRIPT_DIR/oauth1_sign.py" \
    "POST" \
    "$URL" \
    '{}' \
    "$API_KEY" \
    "$API_SECRET" \
    "$ACCESS_TOKEN" \
    "$ACCESS_TOKEN_SECRET")

# Make the request
curl -s -X POST "$URL" \
    -H "Authorization: $AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"target_user_id\": \"$TARGET_USER_ID\"}"
