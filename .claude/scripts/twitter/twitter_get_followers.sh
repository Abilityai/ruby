#!/bin/bash
# Twitter API v2 - Get Followers List
# Returns followers for a user (default: configured user)
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
USER_ID="${1:-${TWITTER_USER_ID}}"  # Default to the creator's ID
MAX_RESULTS="${2:-100}"
PAGINATION_TOKEN="${3:-}"

# Validate max_results (1-1000)
if [ "$MAX_RESULTS" -lt 1 ] || [ "$MAX_RESULTS" -gt 1000 ]; then
    echo "Error: max_results must be between 1 and 1000" >&2
    exit 1
fi

# Build API URL
BASE_URL="https://api.twitter.com/2/users/${USER_ID}/followers"
PARAMS="max_results=${MAX_RESULTS}"
PARAMS="${PARAMS}&user.fields=created_at,description,public_metrics,verified,profile_image_url"

# Add pagination token if provided
if [ -n "$PAGINATION_TOKEN" ]; then
    PARAMS="${PARAMS}&pagination_token=${PAGINATION_TOKEN}"
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
