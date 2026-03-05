# YouTube Analytics Infrastructure for Ruby

## Overview
This folder contains the infrastructure for Ruby to access and analyze the creator's YouTube channel data.

**Channel:** https://www.youtube.com/channel/${YOUTUBE_CHANNEL_ID}

## Current Status
✅ MCP Server installed and configured
✅ Dependencies installed in virtual environment
✅ Documentation created
⏳ **Awaiting API key configuration**

## Quick Links

- **[Quick Start Guide](QUICK_START.md)** - Fast setup in 5 minutes
- **[Detailed Setup Instructions](SETUP_INSTRUCTIONS.md)** - Complete documentation
- **[MCP Server Directory](youtube-mcp-server/)** - Server code and configuration

## Setup Checklist

1. ⏳ Get YouTube Data API v3 key from Google Cloud Console
2. ⏳ Create `credentials.yml` file with API key
3. ⏳ Add to Claude Code MCP configuration
4. ⏳ Restart Claude Desktop
5. ⏳ Test connection with Corbin

See [QUICK_START.md](QUICK_START.md) for step-by-step instructions.

## What's Installed

### MCP Server: youtube-mcp-server
- **Source:** https://github.com/dannySubsense/youtube-mcp-server
- **Location:** `
- **Python Environment:** Virtual environment with all dependencies
- **Functions:** 14 YouTube API functions available

### Capabilities

**Video Analytics:**
- View counts, likes, comments, shares
- Watch time and average duration
- Engagement metrics and ratios
- Video metadata (title, description, tags)

**Channel Analytics:**
- Total subscribers
- Subscriber growth/loss
- Video count and statistics
- Channel metadata

**Content Analysis:**
- Full video transcripts with timestamps
- Comment retrieval and analysis
- Playlist management
- Search and discovery

**Advanced Features:**
- Engagement analysis with benchmarks
- Content evaluation for quality
- Trending video tracking
- Multi-language caption support

### Limitations (YouTube API)
These metrics are NOT available programmatically:
- ❌ Thumbnail impressions
- ❌ Impression click-through rate (CTR)
- ❌ Detailed traffic source breakdowns

## File Structure

```
youtube/
├── README.md                          # This file
├── QUICK_START.md                     # 5-minute setup guide
├── SETUP_INSTRUCTIONS.md              # Detailed setup documentation
└── youtube-mcp-server/                # MCP server installation
    ├── youtube_mcp_server.py          # Main server code
    ├── test_server.py                 # Test suite
    ├── requirements.txt               # Python dependencies
    ├── credentials.yml.example        # API key template
    ├── credentials.yml                # YOUR API KEY (gitignored)
    ├── venv/                          # Python virtual environment
    └── .gitignore                     # Protects credentials
```

## Security

- API credentials stored in `credentials.yml` (gitignored)
- Never commit API keys to version control
- Recommend restricting API key to YouTube Data API v3 only
- Monitor quota usage to prevent unexpected issues

## API Quota

- **Daily Limit:** 10,000 units (free tier)
- **Typical Usage:**
  - Get video details: 1 unit
  - Get channel info: 1 unit
  - Search videos: 100 units
  - Get captions: 50 units

**Monitor at:** https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas

## Usage Examples

Once configured, you can ask Corbin:

```
"Analyze my YouTube channel performance"
"Show me statistics for my last 10 videos"
"Which videos have the best engagement?"
"Get the transcript for video XYZ"
"What are my most recent comments?"
"Compare performance of videos from this month vs last month"
```

## Next Steps After Setup

1. **Initial Analysis:** Review channel overview and recent video performance
2. **Identify Trends:** Track which content types perform best
3. **Content Optimization:** Use engagement metrics to improve future videos
4. **Automation:** Set up regular performance reports
5. **Growth Tracking:** Monitor subscriber growth patterns
6. **Comment Management:** Review and analyze audience feedback

## Troubleshooting

**Can't find Claude config file:**
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- May need to create it if it doesn't exist

**API quota exceeded:**
- Check usage at Google Cloud Console
- Resets daily at midnight Pacific Time
- Consider requesting quota increase if needed

**MCP server not connecting:**
- Verify Python path in config is correct
- Check credentials.yml has valid API key
- Restart Claude Desktop after config changes
- Test server manually: `python test_server.py`

## Support Resources

- **YouTube API Docs:** https://developers.google.com/youtube/v3
- **MCP Server Issues:** https://github.com/dannySubsense/youtube-mcp-server/issues
- **Claude Code Help:** https://github.com/anthropics/claude-code/issues

## Version Information

- **MCP Server Version:** Latest from GitHub (as of 2025-10-25)
- **Python Version:** 3.14.0
- **MCP SDK Version:** 1.19.0
- **YouTube Data API:** v3

---

**Status:** Infrastructure ready, awaiting API key configuration
**Last Updated:** 2025-10-25
**Maintained By:** Ruby
