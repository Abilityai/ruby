#!/bin/bash
# Twitter API v2 - Get User Details by ID or Username (Bearer Token Auth)
# Returns user profile including follower count and verification status

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
    BASE_URL="https://api.twitter.com/2/users/by/username/${IDENTIFIER}"
else
    BASE_URL="https://api.twitter.com/2/users/${IDENTIFIER}"
fi

FULL_URL="${BASE_URL}?user.fields=created_at,description,location,public_metrics,verified,profile_image_url"

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
