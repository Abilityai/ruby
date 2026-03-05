#!/bin/bash
# Generate contextual Twitter reply using the creator's voice
# Input: Target tweet data (JSON)
# Output: Generated reply with self-critique score

set -euo pipefail

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUBY_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
GDRIVE_SCRIPT="$RUBY_DIR/.claude/scripts/google/google_drive.py"
KB_AGENT_DIR="${KNOWLEDGE_BASE_AGENT_PATH}"

# Google Drive file IDs
TWITTER_TOV_ID="YOUR_TWITTER_TOV_ID"

# Check if Gemini API is available
if ! command -v mcp__aistudio__generate_content &> /dev/null; then
  echo "ERROR: Gemini API (mcp__aistudio__generate_content) not available" >&2
  exit 1
fi

# Read input (tweet data JSON)
TWEET_DATA="${1:-}"
if [ -z "$TWEET_DATA" ]; then
  echo "ERROR: No tweet data provided" >&2
  echo "Usage: $0 <tweet_data_json>" >&2
  exit 1
fi

# Extract tweet details
TWEET_TEXT=$(echo "$TWEET_DATA" | jq -r '.text')
TWEET_AUTHOR=$(echo "$TWEET_DATA" | jq -r '.author.username')
TWEET_ID=$(echo "$TWEET_DATA" | jq -r '.tweet_id')

# Optional: Call the knowledge base agent for knowledge base insights
USE_KB_AGENT="${USE_KB_AGENT:-auto}"  # auto|yes|no
KB_INSIGHTS=""

if [ "$USE_KB_AGENT" = "yes" ] || [ "$USE_KB_AGENT" = "auto" ]; then
  echo "Checking knowledge base for relevant insights..." >&2

  # Extract key topics from tweet
  TOPICS=$(echo "$TWEET_TEXT" | grep -oiE '(AI agent|LangGraph|CrewAI|autonomous|agentic|prompt engineering|AI adoption|multi-agent)' | head -3 | tr '\n' ', ' | sed 's/,$//')

  if [ -n "$TOPICS" ]; then
    echo "Found topics: $TOPICS" >&2

    # Call the knowledge base agent (headless mode)
    KB_PROMPT="Quick search: What unique insights does the creator have about: $TOPICS? Return 2-3 key points in bullet form. Keep it brief (under 100 words)."

    KB_RESULT=$(cd "$KB_AGENT_DIR" && claude -p "$KB_PROMPT" --output-format json 2>/dev/null || echo '{"result":""}')
    KB_INSIGHTS=$(echo "$KB_RESULT" | jq -r '.result // ""')

    if [ -n "$KB_INSIGHTS" ] && [ "$KB_INSIGHTS" != "null" ]; then
      echo "✓ Got insights from knowledge base" >&2
    else
      echo "⚠ No relevant insights found in knowledge base" >&2
      KB_INSIGHTS=""
    fi
  fi
fi

# Download tone of voice profile from Google Drive
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

CREATOR_PROFILE="$TEMP_DIR/twitter_tov.md"
echo "Downloading Twitter tone of voice profile..." >&2

if [ ! -f "$GDRIVE_SCRIPT" ]; then
  echo "ERROR: Google Drive script not found at $GDRIVE_SCRIPT" >&2
  exit 1
fi

python3 "$GDRIVE_SCRIPT" download "$TWITTER_TOV_ID" "$CREATOR_PROFILE" 2>/dev/null
if [ ! -f "$CREATOR_PROFILE" ]; then
  echo "ERROR: Failed to download Twitter tone of voice profile" >&2
  exit 1
fi

TONE_PROFILE=$(cat "$CREATOR_PROFILE")

# General profile not used (was optional anyway)
GENERAL_INFO=""

# Get top existing replies (if available - simulated for now)
# In real implementation, this would call Twitter API to get replies
EXISTING_REPLIES="${EXISTING_REPLIES:-}"

# Generate reply prompt
GENERATION_PROMPT=$(cat <<EOF
You are generating a Twitter reply for {{USER_NAME}}.

TWEET TO REPLY TO:
Author: @${TWEET_AUTHOR}
Text: "${TWEET_TEXT}"

EXISTING REPLIES (if any):
${EXISTING_REPLIES:-"No existing replies shown yet."}

THE CREATOR'S TWITTER VOICE PROFILE:
${TONE_PROFILE}

THE CREATOR'S BACKGROUND (for context):
${GENERAL_INFO}

KNOWLEDGE BASE INSIGHTS (if relevant):
${KB_INSIGHTS:-"None retrieved."}

TASK:
Generate a Twitter reply (max 280 characters) that:
1. Sounds authentically like the creator (see voice profile)
2. Adds unique value to the conversation
3. Is inquisitive, not declarative (ask specific questions)
4. Adds technical nuance or contrarian insight
5. Stands out from existing replies
6. Invites further discussion
7. NO emojis, NO "Great post!", NO generic praise

CRITICAL VOICE CHARACTERISTICS:
- Casual but credible (lowercase aesthetic)
- Ask specific follow-up questions
- Challenge assumptions politely
- Reference practical experience
- Add technical depth
- Contrarian when appropriate

EXAMPLES OF GOOD REPLIES:
- "interesting - what's your definition of 'agent' here? i'd argue the key differentiator is autonomous goal pursuit vs. reactive responses"
- "have you tried this with langgraph? curious how the state management compares to your current approach"
- "the tradeoff here is reliability vs. autonomy - which matters more depends on use case. what's yours?"

EXAMPLES OF BAD REPLIES (NEVER DO THIS):
- "Great insight! 🔥"
- "Thanks for sharing!"
- "100% agree"
- "This is so true"

Generate the reply now. Output ONLY the reply text, nothing else.
EOF
)

# Generate reply via Gemini
echo "Generating reply..." >&2

REPLY_RAW=$(echo "$GENERATION_PROMPT" | \
  mcp__aistudio__generate_content \
  --user_prompt "$GENERATION_PROMPT" \
  --temperature 0.8 \
  --model "gemini-2.0-flash-exp" 2>&1)

# Extract reply from Gemini response
REPLY=$(echo "$REPLY_RAW" | jq -r '.result // .text // .' | head -1)

# Trim whitespace and quotes
REPLY=$(echo "$REPLY" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/^"//;s/"$//')

# Check character count
CHAR_COUNT=${#REPLY}
if [ $CHAR_COUNT -gt 280 ]; then
  echo "⚠ Warning: Reply is $CHAR_COUNT characters (truncating to 280)" >&2
  REPLY="${REPLY:0:280}"
fi

echo "Generated reply ($CHAR_COUNT chars)" >&2

# Self-critique (Reflexion loop)
CRITIQUE_PROMPT=$(cat <<EOF
Review this Twitter reply for quality and authenticity.

TARGET TWEET: "${TWEET_TEXT}"
GENERATED REPLY: "${REPLY}"

THE CREATOR'S VOICE PROFILE (key points):
- Inquisitive, asks specific questions
- Adds technical nuance
- Casual but credible
- NO emojis, NO generic praise
- Contrarian when appropriate

SCORING CRITERIA (0-10):
- Sounds authentic to the creator's voice (not robotic)
- Adds unique value (not generic)
- Invites discussion (asks good questions)
- Technically informed
- No spam signals

Score this reply 0-10 (10 = perfect).
If score < 7, explain what's wrong and suggest improvements.

Output format:
SCORE: [0-10]
ISSUES: [if any]
SUGGESTIONS: [if any]
EOF
)

echo "Running self-critique..." >&2

CRITIQUE_RAW=$(echo "$CRITIQUE_PROMPT" | \
  mcp__aistudio__generate_content \
  --user_prompt "$CRITIQUE_PROMPT" \
  --temperature 0.3 \
  --model "gemini-2.0-flash-exp" 2>&1)

CRITIQUE=$(echo "$CRITIQUE_RAW" | jq -r '.result // .text // .')

# Extract score
SCORE=$(echo "$CRITIQUE" | grep -oiE 'SCORE:?\s*[0-9]+' | grep -oE '[0-9]+' | head -1)
SCORE=${SCORE:-5}  # Default to 5 if not found

echo "Self-critique score: $SCORE/10" >&2

# Output JSON result
cat <<JSON
{
  "tweet_id": "$TWEET_ID",
  "tweet_author": "$TWEET_AUTHOR",
  "tweet_text": "$TWEET_TEXT",
  "reply": "$REPLY",
  "char_count": $CHAR_COUNT,
  "score": $SCORE,
  "critique": $(echo "$CRITIQUE" | jq -Rs .),
  "used_knowledge_base": $([ -n "$KB_INSIGHTS" ] && echo "true" || echo "false"),
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON
