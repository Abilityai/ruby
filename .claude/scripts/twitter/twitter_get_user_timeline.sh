#!/bin/bash
# Twitter API v2 - Get User Timeline (Recent Tweets)
# Returns recent tweets from a specific user
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

# Parse arguments
USER_ID="$1"
MAX_RESULTS="${2:-10}"
EXCLUDE_TYPES="${3:-retweets,replies}"  # Default: exclude RTs and replies

if [ -z "$USER_ID" ]; then
    echo "Usage: $0 <user_id> [max_results] [exclude_types]" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 2244994945 10                    # Get 10 tweets from user" >&2
    echo "  $0 2244994945 5 retweets            # Exclude only retweets" >&2
    echo "  $0 2244994945 20 ''                 # Include everything" >&2
    echo "" >&2
    echo "exclude_types: comma-separated list of 'retweets' and/or 'replies'" >&2
    exit 1
fi

# Validate max_results (5-100)
if [ "$MAX_RESULTS" -lt 5 ] || [ "$MAX_RESULTS" -gt 100 ]; then
    echo "Error: max_results must be between 5 and 100" >&2
    exit 1
fi

# Build API URL
BASE_URL="https://api.twitter.com/2/users/${USER_ID}/tweets"
PARAMS="max_results=${MAX_RESULTS}"
PARAMS="${PARAMS}&tweet.fields=created_at,public_metrics,conversation_id"

# Add exclude types if provided
if [ -n "$EXCLUDE_TYPES" ]; then
    PARAMS="${PARAMS}&exclude=${EXCLUDE_TYPES}"
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
