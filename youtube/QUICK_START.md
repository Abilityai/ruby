# YouTube MCP Server - Quick Start Guide

## Your YouTube Channel
**URL:** https://www.youtube.com/channel/${YOUTUBE_CHANNEL_ID}

## One-Time Setup (Do This First!)

### 1. Get YouTube API Key (5 minutes)
```
1. Go to: https://console.cloud.google.com/
2. Create new project (or select existing)
3. Click "Enable APIs and Services"
4. Search "YouTube Data API v3" → Enable
5. Go to Credentials → Create Credentials → API Key
6. Copy the API key
7. (Optional) Restrict to YouTube Data API v3
```

### 2. Create Credentials File
```bash
cd 
cp credentials.yml.example credentials.yml
nano credentials.yml
```

Paste your API key:
```yaml
youtube_api_key: "YOUR_ACTUAL_API_KEY_HERE"
```

Save (Ctrl+O, Enter, Ctrl+X)

### 3. Configure Claude Code
Edit: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add to `mcpServers`:
```json
"youtube": {
  "command": "python3",
  "args": [
    "
  ],
  "env": {
    "YOUTUBE_API_KEY": "YOUR_ACTUAL_API_KEY_HERE"
  }
}
```

### 4. Restart Claude Desktop

Done! Now you can ask Corbin about your YouTube channel.

## Test Commands

Ask Corbin:
```
"Get details about my YouTube channel ${YOUTUBE_CHANNEL_ID}"
"List my recent YouTube videos"
"What are my most viewed videos?"
"Get transcript for video [VIDEO_ID]"
```

## What You Can Analyze

✅ **Available:**
- Video views, likes, comments
- Subscriber growth/loss
- Watch time and duration
- Video transcripts
- Comment analysis
- Engagement metrics
- Channel statistics

❌ **Not Available (API Limitation):**
- Thumbnail impressions
- Click-through rate
- Traffic source details

## Common Tasks

### Analyze Recent Videos
"Show me statistics for my last 10 YouTube videos"

### Get Video Transcript
"Get the transcript for video [VIDEO_ID]"

### Track Engagement
"Which of my videos have the best engagement rates?"

### Review Comments
"Show me recent comments on video [VIDEO_ID]"

### Channel Overview
"Give me an overview of my YouTube channel performance"

## Quota Management

- **Daily Limit:** 10,000 API units
- **Basic calls:** 1 unit each
- **Search calls:** 100 units each
- **Monitor at:** https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas

## File Locations

**Setup Instructions:** `

**MCP Server:** `

**Credentials:** `

## Security Reminders

⚠️ Never commit `credentials.yml` to git
⚠️ Don't share your API key
⚠️ The key is already in `.gitignore`

## Next Steps

Once configured, we can:
1. Build automated performance reports
2. Track video trends over time
3. Analyze which content performs best
4. Monitor subscriber growth patterns
5. Review comment sentiment
6. Optimize publishing strategy
