# YouTube MCP Server Setup Instructions

## Overview
This setup enables Ruby to access and analyze your YouTube channel data through the Model Context Protocol (MCP).

**Your Channel:** https://www.youtube.com/channel/${YOUTUBE_CHANNEL_ID}

## What You Can Access

### ✅ Available Metrics
- **Video Statistics**: Views, likes, comments, shares
- **Engagement Metrics**: Engagement ratios, comment counts
- **Watch Time**: Estimated minutes watched, average view duration
- **Subscriber Growth**: Subscribers gained/lost per video
- **Video Metadata**: Titles, descriptions, tags, categories
- **Transcripts**: Full video transcripts with timestamps
- **Comments**: Video comments with sorting options
- **Channel Analytics**: Total subscribers, video count, channel statistics

### ❌ NOT Available (Google API Limitation)
- Thumbnail impressions
- Impression click-through rate (CTR)
- Traffic source breakdowns by impression

## Setup Steps

### Step 1: Get YouTube Data API v3 Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Click "Enable APIs and Services"
4. Search for "YouTube Data API v3"
5. Click "Enable"
6. Go to "Credentials" in the left sidebar
7. Click "+ CREATE CREDENTIALS" → "API Key"
8. Copy the API key
9. (Optional but recommended) Click "Edit API key" and restrict to:
   - **API restrictions**: Select "YouTube Data API v3"
   - **Application restrictions**: Set to "None" or restrict to your IP

### Step 2: Configure the MCP Server

Create a credentials file:

```bash
cd 
nano credentials.yml
```

Add your API key:

```yaml
youtube_api_key: "YOUR_API_KEY_HERE"
```

Save and exit (Ctrl+O, Enter, Ctrl+X)

### Step 3: Test the Installation

```bash
cd 
source venv/bin/activate
python test_server.py
```

This will test all 14 functions to ensure everything works.

### Step 4: Add to Claude Code Configuration

Edit your Claude Code MCP configuration:

**Mac Location:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add this to the `mcpServers` section:

```json
{
  "mcpServers": {
    "youtube": {
      "command": "python3",
      "args": [
        "
      ],
      "env": {
        "YOUTUBE_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

**Important:** Replace `YOUR_API_KEY_HERE` with your actual API key.

### Step 5: Restart Claude Desktop

After saving the configuration, restart Claude Desktop for the changes to take effect.

### Step 6: Verify Integration

Ask Corbin:
- "Get details about my YouTube channel ${YOUTUBE_CHANNEL_ID}"
- "List my recent YouTube videos"
- "Get statistics for video [VIDEO_ID]"

## Available Functions

The MCP server provides 14 functions:

1. **get_video_details** - Complete video information (views, likes, duration, etc.)
2. **get_channel_details** - Channel info (subscribers, video count)
3. **get_channel_videos** - Recent videos from channel
4. **get_channel_playlists** - List all playlists
5. **get_playlist_details** - Playlist metadata
6. **get_playlist_items** - Videos in a playlist
7. **search_videos** - Search YouTube with filters
8. **get_trending_videos** - Regional trending videos
9. **get_video_comments** - Comments with sorting
10. **get_video_transcript** - Full transcript with timestamps
11. **get_video_caption_info** - Available caption languages
12. **get_video_categories** - Video category list
13. **analyze_video_engagement** - Engagement metrics with benchmarks
14. **evaluate_video_for_knowledge_base** - Content quality evaluation

## API Quota Information

**Daily Quota:** 10,000 units (default free tier)

**Quota Costs:**
- Basic info (video details, channel info): 1 unit
- Search operations: 100+ units
- Caption operations: 50+ units

**Monitor usage at:** [Google Cloud Console - APIs & Services - Quotas](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas)

## Security Notes

- ⚠️ **Never commit** `credentials.yml` to version control
- ⚠️ Add `credentials.yml` to `.gitignore`
- ⚠️ Restrict API key to YouTube Data API v3 only
- ⚠️ Monitor quota usage to avoid unexpected issues

## Troubleshooting

### "API key not found" error
- Check `credentials.yml` exists and has correct format
- Verify API key in Claude config matches your actual key

### "Quota exceeded" error
- Check quota usage in Google Cloud Console
- Wait for daily reset (midnight Pacific Time)
- Consider requesting quota increase

### "Video not found" error
- Verify video ID is correct
- Check if video is private or deleted
- Ensure video is accessible

### MCP connection issues
- Verify Python path is correct in config
- Check all dependencies installed in venv
- Restart Claude Desktop after config changes

## Next Steps

Once configured, you can:
1. Analyze video performance trends
2. Track subscriber growth patterns
3. Review comment sentiment
4. Optimize content based on engagement metrics
5. Export data for further analysis
6. Monitor channel growth over time

## Support

For issues with:
- **MCP Server**: https://github.com/dannySubsense/youtube-mcp-server/issues
- **YouTube API**: https://developers.google.com/youtube/v3/getting-started
- **Claude Code**: https://github.com/anthropics/claude-code/issues
