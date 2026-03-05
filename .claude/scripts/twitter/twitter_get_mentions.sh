#!/bin/bash
# Twitter API v2 - Get Mentions for the creator
# Returns tweets that mention {{TWITTER_HANDLE}} (user ID: ${TWITTER_USER_ID})
# Uses Bearer Token authentication

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load Bearer Token
CONFIG_FILE="$SCRIPT_DIR/twitter_config.sh"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "Error: $CONFIG_FILE not found" >&2
    exit 1
fi

# the creator's user ID
USER_ID="${TWITTER_USER_ID}"

# Parse arguments
MAX_RESULTS="${1:-100}"
SINCE_ID="${2:-}"  # Optional: only get mentions newer than this ID

# Validate max_results (5-100)
if [ "$MAX_RESULTS" -lt 5 ] || [ "$MAX_RESULTS" -gt 100 ]; then
    echo "Error: max_results must be between 5 and 100" >&2
    exit 1
fi

# Build API URL
BASE_URL="https://api.twitter.com/2/users/${USER_ID}/mentions"
PARAMS="max_results=${MAX_RESULTS}"
PARAMS="${PARAMS}&tweet.fields=created_at,public_metrics,author_id,conversation_id,in_reply_to_user_id"
PARAMS="${PARAMS}&expansions=author_id"
PARAMS="${PARAMS}&user.fields=username,name,public_metrics,verified"

# Add since_id if provided
if [ -n "$SINCE_ID" ]; then
    PARAMS="${PARAMS}&since_id=${SINCE_ID}"
fi

FULL_URL="${BASE_URL}?${PARAMS}"

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
