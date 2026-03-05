#!/bin/bash
# Batch fetch Twitter user details for influencer list
# Usage: ./batch_get_influencers.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GET_USER_SCRIPT="$SCRIPT_DIR/twitter_get_user_bearer.sh"

# List of usernames to fetch
USERNAMES=(
    # AI Researchers & Thought Leaders
    "ylecun" "demishassabis" "sama" "karpathy" "drfeifei"
    # AI Agent Framework Creators
    "hwchase17" "joao_g_s" "joereis"
    # AI Startup Founders
    "alexandr_wang" "aravsrinivas" "ClementDelangue" "aidangomez" "bindureddy"
    # AI Journalists
    "karenhao" "sharon" "rowancheung"
    # Enterprise AI Leaders
    "alliekmiller" "cassiekozyrkov" "tessalau"
    # VCs
    "eladgil" "sarahguo" "a16z"
    # Developer Advocates
    "AndrewYNg" "rasbt" "huggingface"
    # Rising Stars
    "michi_sato" "chipro" "mathemagic1an"
    # Additional Targets
    "AnthropicAI" "DarioAmodei" "jared_kaplan"
    "satyanadella" "ericboyd"
    "JeffDean" "sundarpichai"
    "gdb" "ilyasut"
    "jackclark"
    # Additional thought leaders
    "pmarca" "gdb" "shreyas" "naval" "paulg" "lennysan"
    "emollick" "ylecun"
)

# Output file
OUTPUT_FILE=".claude/memory/influencer_twitter_data.json"
TEMP_DIR="/tmp/twitter_influencers_$$"
mkdir -p "$TEMP_DIR"

echo "Fetching Twitter data for ${#USERNAMES[@]} influencers..."
echo "Output: $OUTPUT_FILE"
echo ""

# Fetch each user (with rate limit protection)
for i in "${!USERNAMES[@]}"; do
    username="${USERNAMES[$i]}"
    echo "[$((i+1))/${#USERNAMES[@]}] Fetching @$username..."

    # Call API
    if result=$("$GET_USER_SCRIPT" "$username" username 2>&1); then
        echo "$result" > "$TEMP_DIR/${username}.json"
        echo "  ✓ Success"
    else
        echo "  ✗ Failed: $result"
        # Create placeholder for failed fetch
        echo '{"data": {"username": "'"$username"'", "error": "fetch_failed"}}' > "$TEMP_DIR/${username}.json"
    fi

    # Rate limit protection - 300 requests per 15 min window
    # Wait 3 seconds between requests (20 per minute, well under limit)
    if [ $i -lt $((${#USERNAMES[@]} - 1)) ]; then
        sleep 3
    fi
done

echo ""
echo "Combining results into single JSON..."

# Combine all JSON files into array
jq -s '[.[] | .data]' "$TEMP_DIR"/*.json > "$OUTPUT_FILE"

# Cleanup
rm -rf "$TEMP_DIR"

echo "✓ Complete! Saved to: $OUTPUT_FILE"
echo ""
echo "Summary:"
jq 'length as $total | map(select(.error != "fetch_failed")) | length as $success | {total: $total, success: $success, failed: ($total - $success)}' "$OUTPUT_FILE"
