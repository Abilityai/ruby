#!/bin/bash
# Twitter API v2 - Like a Tweet
# Uses OAuth 1.0a authentication (requires write permissions)
# Usage: ./twitter_like.sh <tweet_id>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load credentials
API_KEY="${API_KEY:-TN7acvy3pm5XPwNGIfgeAujCz}"
API_SECRET="${API_SECRET_KEY:-BSxoF9qKXnuskFd1VM0v6zht0AQCX69VZB7qitN9FB5Q27xS37}"
ACCESS_TOKEN="${ACCESS_TOKEN:-${TWITTER_ACCESS_TOKEN}}"
ACCESS_TOKEN_SECRET="${ACCESS_TOKEN_SECRET:-NMkhuQyr5wf0sXD5CptoCdBWNn7KaWTeG5V8N1PAu7INH}"

# the creator's user ID
MY_USER_ID="${TWITTER_USER_ID}"

TWEET_ID="$1"

if [ -z "$TWEET_ID" ]; then
    echo "Usage: $0 <tweet_id>" >&2
    echo "Example: $0 EXAMPLE_TWEET_ID" >&2
    exit 1
fi

# API endpoint for liking
URL="https://api.twitter.com/2/users/${MY_USER_ID}/likes"

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
RESPONSE=$(curl -s -X POST "$URL" \
    -H "Authorization: $AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "{\"tweet_id\": \"$TWEET_ID\"}")

# Check for success
if echo "$RESPONSE" | jq -e '.data.liked == true' > /dev/null 2>&1; then
    echo "✓ Liked tweet $TWEET_ID"
    echo "$RESPONSE" | jq '.'
elif echo "$RESPONSE" | jq -e '.errors' > /dev/null 2>&1; then
    echo "Error liking tweet:" >&2
    echo "$RESPONSE" | jq '.errors' >&2
    exit 1
else
    echo "$RESPONSE" | jq '.'
fi
