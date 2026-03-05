---
name: blotato-publisher
description: Publish content to social platforms via Blotato API. Use when posting to Twitter, LinkedIn, Instagram, TikTok, YouTube Shorts, Threads, or Facebook.
allowed-tools: Bash, Read, Write
---

# Blotato Publisher

Multi-platform social media publishing via Blotato API.

## Quick Start

**Post text to Twitter:**
```bash
python3 ~/.claude/skills/blotato-publisher/scripts/post.py --platform twitter --text "Your post content here"
```

**Post video to TikTok:**
```bash
python3 ~/.claude/skills/blotato-publisher/scripts/post.py --platform tiktok --text "Caption" --media "https://gofile.io/d/abc123"
```

**Schedule a post:**
```bash
python3 ~/.claude/skills/blotato-publisher/scripts/post.py --platform linkedin --text "Post content" --schedule "2026-01-26T08:00:00-08:00"
```

## Platform Account IDs

| Platform | Account ID | Notes |
|----------|------------|-------|
| YouTube | `8598` | Shorts only |
| Instagram | `9987` | Reels, posts, stories |
| LinkedIn | `4180` | Text, images, carousels |
| Twitter/X | `4790` | Text, images, threads |
| Threads | `3435` | Text, images |
| TikTok | `21395` | Video only |

## API Endpoints

**Base URL:** `https://api.blotato.com/v1`

| Action | Method | Endpoint |
|--------|--------|----------|
| Create post | POST | `/posts` |
| Get post status | GET | `/posts/{id}` |
| Delete post | DELETE | `/posts/{id}` |
| List accounts | GET | `/accounts` |

## Media Handling

### Direct Upload (Images)
- Max 5MB for images
- Supported: PNG, JPG, GIF, WebP

### URL-based (Videos/Images)
Media must be hosted externally. Choose based on your use case:

| Use Case | Upload To | Why |
|----------|-----------|-----|
| **Metricool tracked posts** | Cloudinary ONLY | GoFile URLs expire, causing download errors |
| **Blotato-only, ≤2 days** | GoFile | Free, unlimited size |
| **Blotato-only, >2 days** | Cloudinary | Permanent URLs |
| **Large videos (>100MB)** | GoFile (Blotato-only) | Cloudinary free limit is 100MB |

**GoFile** (short-term, Blotato-only):
```bash
bash ~/.claude/skills/blotato-publisher/scripts/upload_gofile.sh /path/to/video.mp4
```
- URLs expire in 10-30 days
- NEVER use with Metricool

**Cloudinary** (long-term, Metricool-compatible):
```bash
# Use mcp__cloudinary-asset-mgmt__upload-asset
```
- Permanent URLs (never expire)
- 100MB video limit on free plan
- REQUIRED for Metricool posts

### Validate URL Before Posting
```bash
# Verify URL is accessible
bash ~/.claude/skills/schedule-post/scripts/validate_media_url.sh "https://..."
```

## Post Types

### Text Post
```json
{
  "account_id": "4790",
  "content": "Your text here",
  "post_type": "text"
}
```

### Image Post
```json
{
  "account_id": "9987",
  "content": "Caption",
  "media_urls": ["https://..."],
  "post_type": "image"
}
```

### Video Post
```json
{
  "account_id": "21395",
  "content": "Caption",
  "media_urls": ["https://gofile.io/d/..."],
  "post_type": "video"
}
```

### Twitter Thread
```json
{
  "account_id": "4790",
  "content": ["Tweet 1", "Tweet 2", "Tweet 3"],
  "post_type": "thread"
}
```

### Carousel (LinkedIn/Instagram)
```json
{
  "account_id": "4180",
  "content": "Caption",
  "media_urls": ["slide1.png", "slide2.png", "..."],
  "post_type": "carousel"
}
```

## Scheduling

**Format:** ISO 8601 with timezone
```
2026-01-26T08:00:00-08:00  # 8am Pacific
2026-01-26T16:00:00+00:00  # 4pm UTC
```

**Limits:**
- GoFile URLs: Schedule max 2 days out
- Cloudinary URLs: No limit
- Direct upload: No limit

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `401` | Invalid API key | Check BLOTATO_API_KEY in .env |
| `404` | Invalid account ID | Verify account ID from mapping |
| `413` | File too large | Compress or use URL |
| `422` | Invalid media URL | Ensure URL is publicly accessible |

## Environment Variables

Required in `.env`:
```
BLOTATO_API_KEY=your_api_key
GOFILE_API_TOKEN=your_token
GOFILE_ROOT_FOLDER=your_folder_id
```

## Best Practices

1. **Always track posts** - Update schedule.json after posting
2. **Use Cloudinary for scheduled** - GoFile expires too quickly
3. **Plain text only** - No markdown in post content
4. **Test URLs first** - Verify media URLs are accessible
5. **Rate limits** - Max 100 posts/day per account

## Limitations

- No analytics (use Metricool MCP instead)
- No query for existing posts (maintain schedule.json locally)
- Twitter large videos may fail (compress to <50MB)
- No edit after posting (delete and repost)
