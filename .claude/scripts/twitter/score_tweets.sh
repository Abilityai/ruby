#!/bin/bash
# score_tweets.sh - Calculate opportunity scores for tweets from Twitter API response
# Usage: ./score_tweets.sh <twitter_api_json_file> <brand_snapshot_file> <state_file>

set -euo pipefail

TWITTER_JSON="$1"
BRAND_SNAPSHOT="$2"
STATE_FILE="$3"

# Extract content pillar keywords from brand snapshot (simplified - can be enhanced)
# For now, hardcode based on known structure
PILLAR_KEYWORDS_AI_ADOPTION="adoption|resistance|enterprise ai|transformation|change management|ai barriers"
PILLAR_KEYWORDS_AGENT_PATTERNS="langgraph|crewai|autogen|agent architecture|state management|agent framework|agentic"
PILLAR_KEYWORDS_HOT_TAKES="hot take|unpopular opinion|controversial|everyone thinks|contrarian"
PILLAR_KEYWORDS_FOUNDER="startup|founder|building|scaling|fundraising|yc|bootstrapped"
PILLAR_KEYWORDS_TECHNICAL="implementation|how to build|production|deployment|architecture|technical"

# Read cooldowns and tweet IDs from text-based state file (twitter_replies.txt)
# Extract tweet IDs from ## REPLIED TWEET IDs section
REPLIED_TWEETS=$(sed -n '/^## REPLIED TWEET IDs/,/^## /p' "$STATE_FILE" 2>/dev/null | grep -E '^[0-9]+$' || echo "")

# Extract usernames from ## AUTHOR COOLDOWNS section (format: @username until YYYY-MM-DD HH:MM)
# Filter to only include cooldowns that haven't expired yet
NOW=$(date '+%Y-%m-%d %H:%M')
COOLDOWN_AUTHORS=""
while IFS= read -r line; do
    if [[ "$line" =~ ^@([a-zA-Z0-9_]+)\ until\ ([0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}) ]]; then
        username="${BASH_REMATCH[1]}"
        until_time="${BASH_REMATCH[2]}"
        # Compare dates (string comparison works for ISO format)
        if [[ "$until_time" > "$NOW" ]]; then
            COOLDOWN_AUTHORS="$COOLDOWN_AUTHORS$username"$'\n'
        fi
    fi
done < <(sed -n '/^## AUTHOR COOLDOWNS/,/^## /p' "$STATE_FILE" 2>/dev/null | grep '^@')

# Blacklist patterns (hardcoded, no longer in state file)
BLACKLIST_PATTERNS="crypto scam|buy now|airdrop|giveaway|follow for follow|investment opportunity|get rich"

# Main scoring pipeline
jq --arg replied_tweets "$REPLIED_TWEETS" \
   --arg cooldown_authors "$COOLDOWN_AUTHORS" \
   --arg blacklist "$BLACKLIST_PATTERNS" \
   --arg pillar_ai_adoption "$PILLAR_KEYWORDS_AI_ADOPTION" \
   --arg pillar_agent_patterns "$PILLAR_KEYWORDS_AGENT_PATTERNS" \
   --arg pillar_hot_takes "$PILLAR_KEYWORDS_HOT_TAKES" \
   --arg pillar_founder "$PILLAR_KEYWORDS_FOUNDER" \
   --arg pillar_technical "$PILLAR_KEYWORDS_TECHNICAL" \
   '
# Combine tweet data with author data
.data as $tweets |
.includes.users as $users |
$tweets[] |
. as $tweet |
($users[] | select(.id == $tweet.author_id)) as $author |

# Skip if already replied
select(($replied_tweets | split("\n") | map(select(length > 0)) | index($tweet.id)) == null) |

# Skip if author in cooldown
select(($cooldown_authors | split("\n") | map(select(length > 0)) | index($author.username)) == null) |

# Skip if matches blacklist patterns
select(($tweet.text | test($blacklist; "i")) == false) |

# Skip pure retweets (no original content)
select(($tweet.text | startswith("RT @")) == false) |

# Skip tweets with restricted replies (only "everyone" or null/missing is replyable)
# reply_settings: "everyone" (all can reply), "following" (author follows only), "mentionedUsers" (mentioned only)
select(($tweet.reply_settings == null) or ($tweet.reply_settings == "everyone")) |

# Calculate base metrics
{
    tweet_id: $tweet.id,
    tweet_text: $tweet.text,
    tweet_url: ("https://twitter.com/" + $author.username + "/status/" + $tweet.id),
    author_username: $author.username,
    author_id: $author.id,
    author_followers: $author.public_metrics.followers_count,
    author_verified: $author.verified,
    created_at: $tweet.created_at,
    hours_old: ((now - ($tweet.created_at | sub("\\.\\d+Z$"; "Z") | fromdateiso8601)) / 3600 | floor),
    likes: $tweet.public_metrics.like_count,
    retweets: $tweet.public_metrics.retweet_count,
    replies: $tweet.public_metrics.reply_count,
    quotes: $tweet.public_metrics.quote_count,
    bookmarks: $tweet.public_metrics.bookmark_count,
    impressions: $tweet.public_metrics.impression_count
} |

# Skip if too old
select(.hours_old >= 0 and .hours_old < 72) |

# Calculate derived metrics
. + {
    total_engagement: (.likes + .retweets + .replies),
    viral_velocity: ((.likes + .retweets + .replies) / (if .hours_old > 0 then .hours_old else 1 end)),
    engagement_rate: (((.likes + .retweets + .replies) / (.author_followers + 1)) * 100),
    influence_score: (((.likes + .retweets + .replies) / (.author_followers + 1)) / ((.author_followers / 1000 | sqrt) + 0.1))
} |

# Calculate component scores
. + {
    # 1. Viral Velocity Score (0-100)
    viral_velocity_score: (
        if .viral_velocity >= 100 then 100
        elif .viral_velocity >= 50 then 75
        elif .viral_velocity >= 20 then 50
        elif .viral_velocity >= 10 then 25
        else 10
        end
    ),

    # 2. Influence Score Normalized (0-100)
    influence_score_normalized: (
        if .influence_score * 20 > 80 then 80 else .influence_score * 20 end +
        (if .author_verified then 20 else 0 end) +
        (if .author_followers > 50000 then 10 else 0 end) |
        if . > 100 then 100 else . end
    ),

    # 3. Timing Score (0-100)
    timing_score: (
        if .hours_old >= 3 and .hours_old < 12 then 100
        elif .hours_old >= 12 and .hours_old < 24 then 80
        elif .hours_old >= 24 and .hours_old < 48 then 50
        elif .hours_old < 3 then 40
        elif .hours_old >= 48 and .hours_old < 72 then 20
        else 0
        end
    ),

    # 4. Content Pillar Match (0-100) and Matched Pillars
    matched_pillars: [
        (if (.tweet_text | ascii_downcase | test($pillar_ai_adoption)) then "AI Adoption Psychology" else empty end),
        (if (.tweet_text | ascii_downcase | test($pillar_agent_patterns)) then "Agent Design Patterns" else empty end),
        (if (.tweet_text | ascii_downcase | test($pillar_hot_takes)) then "Industry Hot Takes" else empty end),
        (if (.tweet_text | ascii_downcase | test($pillar_founder)) then "Founder Lessons" else empty end),
        (if (.tweet_text | ascii_downcase | test($pillar_technical)) then "Technical Deep Dives" else empty end)
    ],
    pillar_count: (
        [
            (if (.tweet_text | ascii_downcase | test($pillar_ai_adoption)) then 1 else 0 end),
            (if (.tweet_text | ascii_downcase | test($pillar_agent_patterns)) then 1 else 0 end),
            (if (.tweet_text | ascii_downcase | test($pillar_hot_takes)) then 1 else 0 end),
            (if (.tweet_text | ascii_downcase | test($pillar_founder)) then 1 else 0 end),
            (if (.tweet_text | ascii_downcase | test($pillar_technical)) then 1 else 0 end)
        ] | add
    ),

    # 5. Author Quality Score (0-100)
    author_quality_score: (
        if .author_verified then 100
        elif .author_followers > 50000 then 80
        elif .author_followers > 10000 then 60
        elif .author_followers > 5000 then 40
        elif .author_followers > 1000 then 20
        else 10
        end
    )
} |

# Add content_pillar_match score based on pillar_count
. + {
    content_pillar_match: (
        if .pillar_count >= 2 then 100
        elif .pillar_count == 1 then 80
        elif (.tweet_text | ascii_downcase | test("ai|agent|llm|gpt|claude")) then 40
        else 0
        end
    )
} |

# Calculate composite opportunity score
. + {
    opportunity_score: (
        (.viral_velocity_score * 0.30) +
        (.influence_score_normalized * 0.25) +
        (.timing_score * 0.20) +
        (.content_pillar_match * 0.15) +
        (.author_quality_score * 0.10)
    )
} |

# Add quality tier classification
. + {
    quality_tier: (
        if .opportunity_score >= 80 then "🔥 EXCELLENT"
        elif .opportunity_score >= 60 then "✅ GOOD"
        elif .opportunity_score >= 40 then "🟨 MODERATE"
        elif .opportunity_score >= 30 then "🟠 WEAK"
        elif .opportunity_score >= 20 then "🔴 POOR"
        else "❌ SKIP"
        end
    ),
    timing_window: (
        if .hours_old >= 3 and .hours_old < 12 then "✅ OPTIMAL"
        elif .hours_old >= 12 and .hours_old < 24 then "✅ GOOD"
        elif .hours_old >= 24 and .hours_old < 48 then "⚠️ LATE"
        elif .hours_old < 3 then "⏰ TOO EARLY"
        else "❌ TOO LATE"
        end
    )
}
' "$TWITTER_JSON" | jq -s 'sort_by(-.opportunity_score)'
