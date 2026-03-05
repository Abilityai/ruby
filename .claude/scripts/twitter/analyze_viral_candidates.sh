#!/bin/bash
# Analyze Twitter API results for viral velocity and influence scoring
# Input: JSON from twitter_search_bearer.sh
# Output: Filtered, scored candidates for reply engagement

set -euo pipefail

# Read JSON from stdin or file
INPUT="${1:-/dev/stdin}"

if [ "$INPUT" != "/dev/stdin" ] && [ -f "$INPUT" ]; then
  TWEETS=$(cat "$INPUT")
else
  TWEETS=$(cat)
fi

echo "Analyzing tweets for viral candidates..." >&2

# Calculate viral velocity and influence scores
echo "$TWEETS" | jq -r '
# Combine tweets with their author data
.data as $tweets |
.includes.users as $users |

# Process each tweet
$tweets[] |
. as $tweet |

# Find matching author
($users[] | select(.id == $tweet.author_id)) as $author |

# Calculate metrics
{
  tweet_id: .id,
  author_username: $author.username,
  author_id: $author.id,
  author_followers: $author.public_metrics.followers_count,
  author_verified: $author.verified,

  # Tweet data
  text: .text,
  created_at: .created_at,

  # Engagement metrics
  likes: .public_metrics.like_count,
  retweets: .public_metrics.retweet_count,
  replies: .public_metrics.reply_count,
  quotes: .public_metrics.quote_count,
  bookmarks: .public_metrics.bookmark_count,
  impressions: .public_metrics.impression_count,

  # Calculated metrics
  hours_old: ((now - (.created_at | fromdateiso8601)) / 3600 | floor),
  total_engagement: (.public_metrics.like_count + .public_metrics.retweet_count + .public_metrics.reply_count + .public_metrics.quote_count)
} |

# Filter out tweets less than 1 hour old
select(.hours_old > 0) |

# Calculate viral velocity (engagement per hour)
.viral_velocity = ((.total_engagement / .hours_old) | floor) |

# Calculate engagement rate (engagement / followers)
.engagement_rate = (if .author_followers > 0 then
  (.total_engagement / .author_followers) * 100
else 0 end) |

# Calculate influence score
# Formula: (E_avg / sqrt(F_count)) × engagement_bonus × verified_bonus
.influence_score = (
  (.engagement_rate / ((.author_followers | sqrt) / 1000)) *
  (if .engagement_rate > 5 then 2.0
   elif .engagement_rate > 2 then 1.5
   else 1.0 end) *
  (if .author_verified then 1.3 else 1.0 end)
) |

# Classify viral velocity
.viral_classification = (
  if .viral_velocity > 200 then "🔥 EXPLOSIVE"
  elif .viral_velocity > 100 then "✅ STRONG"
  elif .viral_velocity > 50 then "🟨 MODERATE"
  else "🔴 WEAK"
  end
) |

# Classify influence
.influence_classification = (
  if .influence_score > 10 then "🔥 HIGH-VALUE INFLUENCER"
  elif .influence_score > 5 then "✅ ACTIVE INFLUENCER"
  elif .influence_score > 1 then "🟨 MODERATE REACH"
  else "🔴 LOW INFLUENCE"
  end
) |

# Classify timing
.timing_classification = (
  if .hours_old < 6 then "⏰ TOO EARLY - Monitor for 6h"
  elif .hours_old < 24 then "✅ POST TODAY (optimal window)"
  elif .hours_old < 48 then "⚠️ POST TOMORROW (late but OK)"
  else "❌ TOO LATE (>48h - skip)"
  end
) |

# Overall score (0-100)
.overall_score = (
  (.viral_velocity / 5) +  # Max 40 points for velocity
  (.influence_score * 5) +  # Max 50 points for influence
  (if .hours_old >= 6 and .hours_old < 24 then 10 else 0 end)  # 10 points for optimal timing
) |

# Filter candidates
select(.viral_velocity >= 50) |      # At least MODERATE velocity
select(.influence_score >= 1.0) |    # At least MODERATE influence
select(.hours_old >= 6) |            # Not too early
select(.hours_old < 48) |            # Not too late

# Sort by overall score
.
' | jq -s 'sort_by(-.overall_score)' | jq '
# Format output
.[] | {
  tweet_id,
  author: {
    username: .author_username,
    id: .author_id,
    followers: .author_followers,
    verified: .author_verified
  },
  metrics: {
    viral_velocity: .viral_velocity,
    viral_class: .viral_classification,
    influence_score: (.influence_score | floor * 10) / 10,
    influence_class: .influence_classification,
    timing_class: .timing_classification,
    overall_score: (.overall_score | floor)
  },
  engagement: {
    likes: .likes,
    retweets: .retweets,
    replies: .replies,
    total: .total_engagement
  },
  timing: {
    created_at: .created_at,
    hours_old: .hours_old
  },
  text: .text[0:200]
}
'
