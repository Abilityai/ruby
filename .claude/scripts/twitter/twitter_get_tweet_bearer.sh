#!/bin/bash
# Twitter API v2 - Get Tweet Details by ID (Bearer Token Auth)
# Returns full tweet data including timestamp and metrics

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load Bearer Token from config
CONFIG_FILE="$SCRIPT_DIR/twitter_config.sh"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "Error: $CONFIG_FILE not found" >&2
    exit 1
fi

# Parse arguments
TWEET_ID="$1"

if [ -z "$TWEET_ID" ]; then
    echo "Usage: $0 <tweet_id>" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 1460323737035677698" >&2
    echo "" >&2
    echo "Extract tweet ID from URL:" >&2
    echo "  https://twitter.com/username/status/1460323737035677698" >&2
    echo "                                    ^^^^^^^^^^^^^^^^^^^" >&2
    exit 1
fi

# Build API URL
BASE_URL="https://api.twitter.com/2/tweets/${TWEET_ID}"
FULL_URL="${BASE_URL}?tweet.fields=created_at,public_metrics,author_id,conversation_id,lang&expansions=author_id&user.fields=username,name,verified,public_metrics"

# Make API call
RESPONSE=$(curl -sS -X GET \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    "$FULL_URL")

# Check for errors
if echo "$RESPONSE" | jq -e '.errors' > /dev/null 2>&1; then
    echo "API Error:" >&2
    echo "$RESPONSE" | jq '.errors' >&2
    exit 1
fi

# Output clean JSON
echo "$RESPONSE" | jq '.'
