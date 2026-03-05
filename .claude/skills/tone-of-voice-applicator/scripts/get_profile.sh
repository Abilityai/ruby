#!/bin/bash

# Download and display a tone of voice profile from Google Drive
# Usage: ./get_profile.sh [twitter|linkedin|heygen|text_post|newsletter|community|carousel|longform]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUBY_ROOT="${AGENT_ROOT}"
GOOGLE_DRIVE_SCRIPT="$RUBY_ROOT/.claude/scripts/google/google_drive.py"

# Profile ID mapping
declare -A PROFILE_IDS=(
    ["twitter"]="YOUR_TWITTER_TOV_ID"
    ["linkedin"]="YOUR_LINKEDIN_TOV_ID"
    ["heygen"]="YOUR_HEYGEN_TOV_ID"
    ["text_post"]="YOUR_TEXT_POST_TOV_ID"
    ["newsletter"]="YOUR_NEWSLETTER_TOV_ID"
    ["longform"]="YOUR_LONGFORM_TOV_ID"
    ["community"]="YOUR_COMMUNITY_TOV_ID"
    ["carousel"]="YOUR_CAROUSEL_TOV_ID"
)

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <profile_type>"
    echo ""
    echo "Available profiles:"
    echo "  twitter    - Twitter/X posts and threads"
    echo "  linkedin   - LinkedIn posts and articles"
    echo "  heygen     - HeyGen video scripts (30-sec max)"
    echo "  text_post  - General social media text"
    echo "  newsletter - Weekly newsletter style"
    echo "  longform   - YouTube descriptions, blog posts"
    echo "  community  - Slack/Discord community posts"
    echo "  carousel   - LinkedIn/Instagram carousels"
    exit 1
fi

PROFILE_TYPE="$1"
PROFILE_ID="${PROFILE_IDS[$PROFILE_TYPE]}"

if [ -z "$PROFILE_ID" ]; then
    echo "Error: Unknown profile type: $PROFILE_TYPE"
    echo "Available: ${!PROFILE_IDS[*]}"
    exit 1
fi

# Create profiles directory if needed
PROFILES_DIR="$SKILL_DIR/profiles"
mkdir -p "$PROFILES_DIR"

OUTPUT_FILE="$PROFILES_DIR/${PROFILE_TYPE}_profile.md"

echo "Downloading $PROFILE_TYPE tone of voice profile..."
echo "Profile ID: $PROFILE_ID"

# Download the profile
python3 "$GOOGLE_DRIVE_SCRIPT" download "$PROFILE_ID" "$OUTPUT_FILE"

if [ -f "$OUTPUT_FILE" ]; then
    echo ""
    echo "Profile saved to: $OUTPUT_FILE"
    echo ""
    echo "=== Profile Contents ==="
    cat "$OUTPUT_FILE"
else
    echo "Error: Failed to download profile"
    exit 1
fi
