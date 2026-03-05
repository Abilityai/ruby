# Twitter API v2 Utilities

Shell scripts for accessing Twitter API v2 with OAuth 1.0a authentication. These scripts automatically load credentials from the agent's `.mcp.json` configuration.

## Requirements

- `bash`
- `curl`
- `jq` (for JSON parsing)
- `python3` (for OAuth signature generation)

All requirements are typically pre-installed on macOS/Linux.

## Scripts

### 1. `twitter_search.sh` - Search Recent Tweets

Search tweets from the last 7 days with full metadata.

**Usage:**
```bash
./twitter_search.sh <search_query> [max_results]
```

**Parameters:**
- `search_query` - Twitter search query (required)
- `max_results` - Number of tweets (10-100, default: 50)

**Returns:**
- Tweet text, created_at timestamp, public_metrics (likes, retweets, replies, quotes)
- Author info (username, name, verified status, follower count)

**Examples:**
```bash
# Search for AI agent tweets
./twitter_search.sh "AI agent" 50

# Search with OR operator
./twitter_search.sh "LangGraph OR CrewAI" 100

# Search with filters
./twitter_search.sh "AI adoption -filter:retweets lang:en" 50
```

**Output Structure:**
```json
{
  "data": [
    {
      "id": "1234567890",
      "text": "Tweet content here...",
      "created_at": "2025-12-01T10:30:00.000Z",
      "author_id": "123456",
      "public_metrics": {
        "retweet_count": 10,
        "reply_count": 5,
        "like_count": 50,
        "quote_count": 2,
        "impression_count": 1000
      }
    }
  ],
  "includes": {
    "users": [
      {
        "id": "123456",
        "username": "example",
        "name": "Example User",
        "verified": true,
        "public_metrics": {
          "followers_count": 10000,
          "following_count": 500,
          "tweet_count": 2000
        }
      }
    ]
  },
  "meta": {
    "result_count": 50
  }
}
```

### 2. `twitter_get_tweet.sh` - Get Tweet Details

Get full details for a specific tweet by ID.

**Usage:**
```bash
./twitter_get_tweet.sh <tweet_id>
```

**Parameters:**
- `tweet_id` - Numeric tweet ID (extract from URL)

**Returns:**
- Full tweet data with timestamp, metrics, and author info

**Examples:**
```bash
# Get tweet by ID
./twitter_get_tweet.sh 1460323737035677698

# Extract ID from URL: https://twitter.com/username/status/1460323737035677698
#                                                        ^^^^^^^^^^^^^^^^^^^
```

### 3. `twitter_get_user.sh` - Get User Profile

Get user profile details by ID or username.

**Usage:**
```bash
./twitter_get_user.sh <identifier> [id|username]
```

**Parameters:**
- `identifier` - User ID or username (required)
- `id|username` - Lookup type (default: id)

**Returns:**
- User profile with follower count, verification status, bio, location

**Examples:**
```bash
# Lookup by user ID
./twitter_get_user.sh 2244994945 id

# Lookup by username
./twitter_get_user.sh TwitterDev username
```

**Output Structure:**
```json
{
  "data": {
    "id": "2244994945",
    "name": "Twitter Dev",
    "username": "TwitterDev",
    "verified": true,
    "description": "The voice of the Twitter Dev team...",
    "location": "San Francisco, CA",
    "created_at": "2013-12-14T04:35:55.000Z",
    "profile_image_url": "https://...",
    "public_metrics": {
      "followers_count": 700000,
      "following_count": 1000,
      "tweet_count": 5000,
      "listed_count": 500
    }
  }
}
```

## Authentication

Scripts automatically load credentials from `.mcp.json`:

```json
{
  "mcpServers": {
    "twitter-mcp": {
      "env": {
        "API_KEY": "your_consumer_key",
        "API_SECRET_KEY": "your_consumer_secret",
        "ACCESS_TOKEN": "your_access_token",
        "ACCESS_TOKEN_SECRET": "your_access_token_secret"
      }
    }
  }
}
```

No additional configuration needed - credentials are shared with the Twitter MCP.

## Rate Limits

**Important:** Twitter API v2 has rate limits per 15-minute window:

| Endpoint | User-level Limit | Notes |
|----------|------------------|-------|
| `/2/tweets/search/recent` | 180 requests | ~9,000 tweets/15min (50 per request) |
| `/2/tweets/:id` | 900 requests | Individual tweet lookups |
| `/2/users/:id` | 900 requests | User profile lookups |

**Best Practices:**
- Cache results when possible
- Use search with max_results=100 to minimize requests
- Don't exceed rate limits (429 Too Many Requests)

## Error Handling

All scripts check for API errors and exit with status code 1:

```bash
if ! result=$(./twitter_search.sh "AI agent" 50); then
    echo "Search failed"
    exit 1
fi
```

Common errors:
- `401 Unauthorized` - Invalid credentials
- `429 Too Many Requests` - Rate limit exceeded
- `400 Bad Request` - Invalid query syntax

## Twitter Search Query Operators

Powerful search syntax available:

```bash
# Combine keywords
"AI agent" "LangGraph"

# OR operator
"LangGraph OR CrewAI OR AutoGPT"

# Exclude terms
"AI agent -crypto"

# Filter retweets
"AI adoption -filter:retweets"

# Language filter
"AI agent lang:en"

# From specific user
"from:karpathy AI"

# Engagement thresholds
"AI agent min_faves:100 min_retweets:20"

# Combine filters
"AI adoption enterprise -filter:retweets lang:en min_faves:50"
```

## Integration with trending-topics-researcher Agent

These scripts enable Phase 1 improvements:

1. **Viral Velocity Scoring** - Get timestamps and calculate engagement/hour
2. **Influence Scoring** - Get author follower counts and engagement rates
3. **Timing Intelligence** - Calculate tweet age for optimal posting windows

**Example workflow:**
```bash
# 1. Search for trending topics
results=$(./twitter_search.sh "AI agent architecture" 50)

# 2. Extract tweet IDs and timestamps
echo "$results" | jq -r '.data[] | "\(.id),\(.created_at),\(.public_metrics.like_count)"'

# 3. Get author details for top tweets
author_id=$(echo "$results" | jq -r '.data[0].author_id')
./twitter_get_user.sh "$author_id" id

# 4. Calculate viral velocity
# engagement_count / hours_since_posted
```

## Portability

All scripts are self-contained and portable:

1. Copy `.claude/scripts/twitter/` folder to another agent
2. Ensure target agent has Twitter credentials in `.mcp.json`
3. Scripts automatically detect agent root and load config

**Example:**
```bash
# Copy to another agent
cp -r Ruby/.claude/scripts/twitter the knowledge base agent/.claude/scripts/

# Works immediately (if the knowledge base agent has Twitter MCP configured)
cd the knowledge base agent
./.claude/scripts/twitter/twitter_search.sh "AI news" 50
```

## Testing

Quick test to verify setup:

```bash
# Test search
./twitter_search.sh "AI" 10

# Expected: JSON with 10 tweets about AI
# If error: Check .mcp.json credentials
```

## Advanced Usage

### Batch User Lookups

```bash
# Get follower counts for multiple users
cat tweet_ids.txt | while read tweet_id; do
    ./twitter_get_tweet.sh "$tweet_id" | jq -r '.includes.users[0].public_metrics.followers_count'
done
```

### Calculate Viral Velocity

```bash
# Search and calculate engagement rate
results=$(./twitter_search.sh "AI agent" 50)
echo "$results" | jq -r '
.data[] |
{
    id: .id,
    text: .text,
    created_at: .created_at,
    engagement: (.public_metrics.like_count + .public_metrics.retweet_count + .public_metrics.reply_count),
    hours_old: ((now - (.created_at | fromdateiso8601)) / 3600 | floor)
} |
select(.hours_old > 0) |
.velocity = (.engagement / .hours_old) |
select(.velocity > 20) |
"[\(.velocity | floor)/hr] \(.text[0:80])..."
'
```

### Filter by Author Influence

```bash
# Get tweets from high-influence authors only
results=$(./twitter_search.sh "AI agents" 100)
echo "$results" | jq '
.data as $tweets |
.includes.users as $users |
$tweets[] |
. as $tweet |
($users[] | select(.id == $tweet.author_id)) as $author |
select($author.public_metrics.followers_count > 10000) |
{
    tweet: $tweet.text,
    author: $author.username,
    followers: $author.public_metrics.followers_count
}
'
```

## Troubleshooting

**"Could not load Twitter API credentials"**
- Check that `.mcp.json` exists in agent root
- Verify `twitter-mcp` section has all 4 credentials

**"Invalid parameters" from oauth1_sign.py**
- Ensure python3 is installed: `python3 --version`
- Check that all 7 arguments are passed correctly

**"Rate limit exceeded (429)"**
- Wait 15 minutes for rate limit window to reset
- Check X-Rate-Limit-Reset header in response
- Reduce max_results or request frequency

**"Unauthorized (401)"**
- Verify Twitter API credentials are correct
- Check that tokens haven't been revoked
- Ensure OAuth 1.0a app permissions are correct

## References

- [Twitter API v2 Documentation](https://developer.twitter.com/en/docs/twitter-api)
- [Twitter Search Query Operators](https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query)
- [Rate Limits](https://developer.twitter.com/en/docs/twitter-api/rate-limits)
