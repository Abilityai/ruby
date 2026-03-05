#!/bin/bash
# Fetch missing influencers identified from deep research document

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GET_USER_SCRIPT="$SCRIPT_DIR/twitter_get_user_bearer.sh"

# Missing high-value accounts from deep research
USERNAMES=(
    # Agentic Builders (Critical)
    "yoheinakajima" "jerryjliu0" "swyx" "simonw" "HamelHusain"
    # Strategic Architects
    "RonaldvanLoon" "OfficialLoganK" "DrJimFan"
    # Researchers
    "AnimaAnandkumar" "Thom_Wolf" "julien_c" "jeremyphoward" "fchollet"
    # Rising Stars
    "mattshumer_" "mckaywrigley" "tunguz" "svpino"
    # Newsletters
    "TheRundownAI" "bensbites" "AlphaSignalAI" "tldr_ai" "TheNeuron" "LastWeekInAI"
    # Additional from research
    "Tim_Dettmers" "GaryMarcus" "lexfridman" "mustafasuleyman"
)

OUTPUT_FILE=".claude/memory/influencer_twitter_data_v2.json"
TEMP_DIR="/tmp/twitter_influencers_v2_$$"
mkdir -p "$TEMP_DIR"

echo "Fetching ${#USERNAMES[@]} missing influencers from deep research..."
echo ""

for i in "${!USERNAMES[@]}"; do
    username="${USERNAMES[$i]}"
    echo "[$((i+1))/${#USERNAMES[@]}] @$username..."

    if result=$("$GET_USER_SCRIPT" "$username" username 2>&1); then
        echo "$result" > "$TEMP_DIR/${username}.json"
        echo "  ✓"
    else
        echo "  ✗ Failed"
        echo '{"data": {"username": "'"$username"'", "error": "fetch_failed"}}' > "$TEMP_DIR/${username}.json"
    fi

    if [ $i -lt $((${#USERNAMES[@]} - 1)) ]; then
        sleep 3
    fi
done

echo ""
echo "Combining results..."
jq -s '[.[] | .data]' "$TEMP_DIR"/*.json > "$OUTPUT_FILE"
rm -rf "$TEMP_DIR"

echo "✓ Complete: $OUTPUT_FILE"
jq 'length as $total | map(select(.error != "fetch_failed")) | length as $success | {total: $total, success: $success, failed: ($total - $success)}' "$OUTPUT_FILE"
