---
name: post-now
description: Post content immediately to social platforms. Use when posting to Twitter, LinkedIn, Instagram, TikTok, YouTube Shorts, Threads, or Facebook.
automation: manual
allowed-tools: Bash, Read, Write
depends-on: blotato-publisher, tone-of-voice-applicator, schedule-tracker
calls:
  - blotato-publisher
  - tone-of-voice-applicator
  - schedule-tracker
---

# Post Now

Post content immediately to one or more social media platforms.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| TOV Profiles | `Prompts/*.md` (Google Drive) | ✓ | | Platform voice profiles |
| Schedule | `.claude/memory/schedule.json` | | ✓ | Track posted content |
| Media (temp) | GoFile or Cloudinary | | ✓ | Uploaded media URLs |

## Quick Start

```bash
# Post text to Twitter
python3 ~/.claude/skills/blotato-publisher/scripts/post.py --platform twitter --text "Your post content here"

# Post video to TikTok
python3 ~/.claude/skills/blotato-publisher/scripts/post.py --platform tiktok --text "Caption" --media "https://gofile.io/d/abc123"
```

## Usage

```
/post-now <platforms> <content type> <content>
```

**Parameters:**
- **platforms**: Comma-separated list or "all"
  - linkedin, twitter, instagram, tiktok, youtube, threads, facebook, bluesky, pinterest
- **content type**: text | image | video | carousel
- **content**: Post text + media path/URL (if applicable)

**Examples:**
```
/post-now linkedin text "Just published my thoughts on AI adoption"
/post-now linkedin,twitter image "Check out this framework!" /path/to/image.png
/post-now instagram video "New video on AI psychology" /path/to/video.mp4
```

## Workflow

### 1. Apply Tone of Voice (if needed)

```bash
bash ~/.claude/skills/tone-of-voice-applicator/scripts/get_profile.sh linkedin
```

Review content against platform-specific voice guidelines.

### 2. Upload Media (if applicable)

For images/videos, upload first:

```bash
# For short-term posting (within 2 days)
bash ~/.claude/skills/blotato-publisher/scripts/upload_gofile.sh /path/to/video.mp4

# For longer-term - use Cloudinary MCP
mcp__cloudinary-asset-mgmt__upload-asset
```

### 3. Post via Blotato

```bash
python3 ~/.claude/skills/blotato-publisher/scripts/post.py \
  --platform linkedin \
  --text "Content" \
  --media "https://..."  # Optional, for media posts
```

### 4. Update Schedule Tracker

```bash
python3 ~/.claude/skills/schedule-tracker/scripts/add_post.py \
  --platform linkedin \
  --text "Content" \
  --time "$(date -Iseconds)" \
  --status posted
```

## Platform Account IDs

| Platform | ID | Notes |
|----------|-----|-------|
| YouTube | `8598` | Shorts only |
| Instagram | `9987` | Reels, posts, stories |
| LinkedIn | `4180` | Text, images, carousels |
| Twitter/X | `4790` | Text, images, threads |
| Threads | `3435` | Text, images |
| TikTok | `21395` | Video only |

## Platform Limits

| Platform | Character Limit | Media Limits |
|----------|-----------------|--------------|
| Twitter | 280 chars | Max 4 images/tweet |
| LinkedIn | 3000 chars | 9 images/carousel |
| Threads | 500 chars (strict) | - |
| Instagram | 2200 chars | 1080x1920 vertical video |

## Content Guidelines

- **Plain text only** - No markdown in post content
- **Apply tone of voice** - Use platform-specific voice profile
- **Tag content** - Include content pillar and hook type
- **Track posts** - Always update schedule.json after posting

## Error Handling

| Error | Solution |
|-------|----------|
| 401 Unauthorized | Check BLOTATO_API_KEY in .env |
| 404 Not Found | Verify account ID from mapping |
| 413 Too Large | Compress media or use URL |
| 422 Invalid Media | Ensure URL is publicly accessible |

## Related Skills

- `blotato-publisher` - Full API documentation
- `tone-of-voice-applicator` - Brand voice profiles
- `schedule-tracker` - Post tracking

## Completion Checklist

- [ ] Content reviewed against tone of voice profile
- [ ] Character limits verified for each platform
- [ ] Media uploaded (if applicable) - GoFile or Cloudinary
- [ ] Media URL validated (publicly accessible)
- [ ] Posted via Blotato API
- [ ] Post ID captured from response
- [ ] schedule.json updated with posted entry
- [ ] User notified of success/failure
