#!/bin/bash

# ============================================================================
# DEPRECATED: Use /post-queued-replies command instead
# ============================================================================
#
# This script is kept for emergency/backup use only.
#
# Primary method: /post-queued-replies (uses Twitter MCP directly)
# This script: Spawns Claude headless to call Twitter MCP (convoluted)
#
# Why /post-queued-replies is better:
#   - Direct MCP calls (no subprocess overhead)
#   - Better error handling and state updates
#   - Interactive progress display
#   - Integrated with Ruby's context
#
# Only use this script if:
#   - Ruby agent is unavailable
#   - Need true background posting (detached from terminal)
#   - Debugging posting issues
#
# ============================================================================

# Background Twitter Reply Poster
# Reads from reply queue and posts with random delays

QUEUE_FILE=".claude/memory/reply_queue.json"
STATE_FILE=".claude/memory/twitter_replies.txt"
LOG_FILE=".claude/memory/reply_posting.log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_color() {
    echo -e "${2}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

# Update the text-based state file
update_state_file() {
    local tweet_id="$1"
    local author="$2"
    local reply_preview="$3"
    local posted_tweet_id="$4"

    local today=$(date '+%Y-%m-%d')
    local now_time=$(date '+%H:%M')
    local cooldown_until=$(date -v+24H '+%Y-%m-%d %H:%M')
    local timestamp=$(date '+%Y-%m-%d %H:%M UTC')

    # Create temp file for modifications
    local temp_file=$(mktemp)

    # Update the header timestamp
    sed "s/^# Updated:.*/# Updated: $timestamp/" "$STATE_FILE" > "$temp_file"

    # Check if today's date matches in ## TODAY section
    if grep -q "Date: $today" "$temp_file"; then
        # Increment the reply count
        local current_count=$(grep "Replies:" "$temp_file" | head -1 | sed 's/Replies: \([0-9]*\).*/\1/')
        local new_count=$((current_count + 1))
        sed -i '' "s/Replies: $current_count\/10/Replies: $new_count\/10/" "$temp_file"
        sed -i '' "s/Last reply:.*/Last reply: $now_time UTC/" "$temp_file"
    else
        # New day - reset count
        sed -i '' "s/Date: .*/Date: $today/" "$temp_file"
        sed -i '' "s/Replies: [0-9]*\/10/Replies: 1\/10/" "$temp_file"
        sed -i '' "s/Last reply:.*/Last reply: $now_time UTC/" "$temp_file"
    fi

    # Add author cooldown (insert after ## AUTHOR COOLDOWNS line)
    # First remove old cooldown for this author if exists
    sed -i '' "/@$author until/d" "$temp_file"
    # Then add new cooldown
    sed -i '' "/^## AUTHOR COOLDOWNS/a\\
@$author until $cooldown_until
" "$temp_file"

    # Add to replied tweet IDs (insert after ## REPLIED TWEET IDs line)
    sed -i '' "/^## REPLIED TWEET IDs/a\\
$tweet_id
" "$temp_file"

    # Move temp file back
    mv "$temp_file" "$STATE_FILE"

    log "Updated state file: @$author cooldown, tweet $tweet_id added"
}

# Check if queue file exists
if [ ! -f "$QUEUE_FILE" ]; then
    log_color "No reply queue found at $QUEUE_FILE" "$RED"
    exit 1
fi

# Check if state file exists
if [ ! -f "$STATE_FILE" ]; then
    log_color "No state file found at $STATE_FILE" "$RED"
    exit 1
fi

# Read queue
QUEUE=$(cat "$QUEUE_FILE")
PENDING_COUNT=$(echo "$QUEUE" | jq '[.replies[] | select(.status == "pending")] | length')

if [ "$PENDING_COUNT" -eq 0 ]; then
    log_color "No pending replies in queue" "$GREEN"
    exit 0
fi

log_color "Found $PENDING_COUNT pending replies in queue" "$YELLOW"
log_color "Starting background posting process..." "$YELLOW"

# Check daily limit from text file
TODAY=$(date '+%Y-%m-%d')
CURRENT_DATE=$(grep "Date:" "$STATE_FILE" | head -1 | awk '{print $2}')
if [ "$CURRENT_DATE" = "$TODAY" ]; then
    CURRENT_REPLIES=$(grep "Replies:" "$STATE_FILE" | head -1 | sed 's/Replies: \([0-9]*\).*/\1/')
else
    CURRENT_REPLIES=0
fi

REMAINING=$((10 - CURRENT_REPLIES))
if [ "$REMAINING" -le 0 ]; then
    log_color "Daily limit reached ($CURRENT_REPLIES/10). Try again tomorrow." "$RED"
    exit 1
fi

log_color "Daily limit: $CURRENT_REPLIES/10 used, $REMAINING remaining" "$YELLOW"

# Process each pending reply
REPLY_INDEX=0
POSTED_COUNT=0
echo "$QUEUE" | jq -c '.replies[] | select(.status == "pending")' | while read -r reply; do
    REPLY_INDEX=$((REPLY_INDEX + 1))

    # Check if we've hit daily limit during processing
    if [ "$POSTED_COUNT" -ge "$REMAINING" ]; then
        log_color "Daily limit reached during session. Stopping." "$YELLOW"
        break
    fi

    TWEET_ID=$(echo "$reply" | jq -r '.tweet_id')
    REPLY_TEXT=$(echo "$reply" | jq -r '.reply_text')
    TARGET_USERNAME=$(echo "$reply" | jq -r '.target_username')

    # Generate random delay (2-15 minutes = 120-900 seconds)
    if [ $REPLY_INDEX -eq 1 ]; then
        DELAY=0  # First reply posts immediately
    else
        DELAY=$((120 + RANDOM % 780))
    fi

    DELAY_MIN=$(echo "scale=1; $DELAY / 60" | bc)

    if [ $DELAY -gt 0 ]; then
        log_color "Waiting ${DELAY_MIN} minutes before next post..." "$YELLOW"
        sleep $DELAY
    fi

    log_color "Posting reply to @${TARGET_USERNAME}..." "$YELLOW"

    # Post via Claude Code (using Twitter MCP)
    RESULT=$(python3 .claude/scripts/post_tweet_helper.py "$REPLY_TEXT" "$TWEET_ID" 2>&1)

    if [ $? -eq 0 ]; then
        NEW_TWEET_ID=$(echo "$RESULT" | jq -r '.tweet_id // "posted"')
        log_color "Posted! Tweet ID: $NEW_TWEET_ID" "$GREEN"
        POSTED_COUNT=$((POSTED_COUNT + 1))

        # Update queue status to 'posted'
        TEMP_FILE=$(mktemp)
        jq --arg tid "$TWEET_ID" --arg ntid "$NEW_TWEET_ID" \
            '(.replies[] | select(.tweet_id == $tid)) |= (. + {status: "posted", posted_tweet_id: $ntid, posted_at: (now | strftime("%Y-%m-%dT%H:%M:%SZ"))})' \
            "$QUEUE_FILE" > "$TEMP_FILE"
        mv "$TEMP_FILE" "$QUEUE_FILE"

        # Update state file (text format)
        REPLY_PREVIEW=$(echo "$REPLY_TEXT" | cut -c1-50)
        update_state_file "$TWEET_ID" "$TARGET_USERNAME" "$REPLY_PREVIEW" "$NEW_TWEET_ID"

    else
        log_color "Failed to post reply: $RESULT" "$RED"

        # Update queue status to 'failed'
        TEMP_FILE=$(mktemp)
        jq --arg tid "$TWEET_ID" --arg error "$RESULT" \
            '(.replies[] | select(.tweet_id == $tid)) |= (. + {status: "failed", error: $error, failed_at: (now | strftime("%Y-%m-%dT%H:%M:%SZ"))})' \
            "$QUEUE_FILE" > "$TEMP_FILE"
        mv "$TEMP_FILE" "$QUEUE_FILE"
    fi
done

log_color "Background posting complete!" "$GREEN"
log ""
log "Posted: $POSTED_COUNT replies"
log "Check .claude/memory/reply_queue.json for detailed results"
log "Check .claude/memory/twitter_replies.txt for updated state"
