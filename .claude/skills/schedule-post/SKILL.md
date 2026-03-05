---
name: schedule-post
description: Schedule content for future posting. Use when scheduling social media posts for later.
allowed-tools: Bash, Read, Write
depends-on: blotato-publisher, schedule-tracker, tone-of-voice-applicator
---

# Schedule Post

Schedule content to be posted at a specific future date and time.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Schedule Tracker | `.claude/memory/schedule.json` | ✓ | ✓ | Check conflicts, track posts |

## Quick Start

```bash
# Schedule LinkedIn post for tomorrow 9am
python3 ~/.claude/skills/blotato-publisher/scripts/post.py \
  --platform linkedin \
  --text "Your content" \
  --schedule "2026-01-26T09:00:00-08:00"
```

## Usage

```
/schedule-post <date/time> <platforms> <content type> <content>
```

**Parameters:**
- **date/time**: Natural language or ISO 8601
  - "tomorrow at 9am"
  - "next Monday 2pm"
  - "2026-01-26T09:00:00-08:00"
- **platforms**: Comma-separated list or "all"
- **content type**: text | image | video | carousel
- **content**: Post text + media path/URL

**Examples:**
```
/schedule-post "tomorrow at 9am" linkedin text "New article on AI adoption"
/schedule-post "next Monday 2pm" instagram,tiktok video "AI insights" /path/to/video.mp4
```

## Media Hosting Decision Tree

```
Is this a Metricool post (analytics tracked)?
├── YES → ALWAYS use Cloudinary (permanent URLs required)
│   ├── Video ≤100MB → Upload to Cloudinary
│   ├── Video >100MB → Use Blotato instead (no Metricool)
│   └── Images ≤10MB → Upload to Cloudinary
│
└── NO (Blotato only) → Check scheduling window
    ├── ≤2 days out → GoFile OK (free, unlimited size)
    └── >2 days out → Cloudinary (permanent URLs)
```

## CRITICAL: Metricool Requirements

Metricool downloads media URLs when publishing. **URLs MUST be accessible**.

### Why Posts Fail

| Error | Cause | Solution |
|-------|-------|----------|
| "Error downloading the image: null" | Missing `media` array | Include `media: [{url, type}]` |
| "Error downloading the image: [url]" | Expired GoFile URL | Use Cloudinary instead |
| "Error downloading the image: [url]" | Private/inaccessible URL | Test URL accessibility first |

### Pre-Scheduling Validation (REQUIRED for Metricool)

```bash
# 1. Test URL is accessible (must return HTTP 200)
curl -sI "https://res.cloudinary.com/..." | head -1
# Expected: HTTP/1.1 200 OK

# 2. Verify file type matches
curl -sI "https://res.cloudinary.com/..." | grep -i content-type
# Expected: image/png, video/mp4, etc.
```

## File Size Limits

| Service | Images | Videos | Best For |
|---------|--------|--------|----------|
| **Cloudinary (Free)** | 10MB | 100MB | Metricool posts, permanent storage |
| **Cloudinary (Plus)** | 10MB | 2GB | Large videos with analytics |
| **GoFile** | Unlimited | Unlimited | Blotato-only posts ≤2 days out |

### Handling Large Videos (>100MB)

**Option 1: Blotato Only (No Analytics)**
```bash
# Upload to GoFile (unlimited size)
bash ~/.claude/skills/blotato-publisher/scripts/upload_gofile.sh /path/to/large_video.mp4

# Schedule via Blotato (skip Metricool)
python3 ~/.claude/skills/blotato-publisher/scripts/post.py \
  --platform linkedin \
  --video "https://gofile.io/d/XXXXX" \
  --schedule "2026-01-26T09:00:00-08:00"
```

**Option 2: Compress Video First**
```bash
# Compress to under 100MB
ffmpeg -i large_video.mp4 -vcodec libx264 -crf 28 -preset fast compressed.mp4

# Then upload to Cloudinary
```

## Workflow

### 0. Check Schedule Conflicts (REQUIRED)

**Before scheduling, ALWAYS check for existing posts at the target time:**

```bash
# Read schedule.json and check for conflicts within 2-hour window
cat .claude/memory/schedule.json | jq --arg target "2026-01-26T09:00:00" '
  .scheduled_posts[] |
  select(.status=="scheduled") |
  select(.scheduled_time | startswith($target[0:10])) |
  {time: .scheduled_time, platforms, preview: .content_text[0:50]}
'
```

**If conflicts exist:**
1. Show user the existing posts at/near that time
2. Ask: "Schedule anyway (high volume) or choose different time?"
3. Only proceed after explicit confirmation

**No conflicts?** Continue to Step 1.

### 1. Check File Size

```bash
# Get file size in MB
du -m /path/to/video.mp4 | cut -f1
```

### 2. Upload Media

**For Cloudinary (Metricool posts, permanent):**
```python
mcp__cloudinary-asset-mgmt__upload-asset(
    resourceType="image",  # or "video"
    uploadRequest={
        "file": "file:///path/to/media.mp4",
        "public_id": "ruby/scheduled/post_name",
        "tags": "scheduled,linkedin"
    }
)
# Returns: {"secureUrl": "https://res.cloudinary.com/..."}
```

**For GoFile (Blotato-only, ≤2 days):**
```bash
bash ~/.claude/skills/blotato-publisher/scripts/upload_gofile.sh /path/to/video.mp4
# Returns: https://gofile.io/d/XXXXX
```

### 3. Validate URL (Metricool Only)

```bash
# REQUIRED before Metricool scheduling
URL="https://res.cloudinary.com/dfs5yfioa/..."
HTTP_STATUS=$(curl -sI "$URL" | head -1 | awk '{print $2}')
if [ "$HTTP_STATUS" != "200" ]; then
  echo "ERROR: URL not accessible (HTTP $HTTP_STATUS)"
  exit 1
fi
echo "URL validated successfully"
```

### 4. Schedule via Blotato

```bash
python3 ~/.claude/skills/blotato-publisher/scripts/post.py \
  --platform linkedin \
  --text "Content" \
  --image "https://res.cloudinary.com/..." \
  --schedule "2026-01-26T09:00:00-08:00"
```

### 5. Track in Schedule

```bash
python3 ~/.claude/skills/schedule-tracker/scripts/add_post.py \
  --platform linkedin \
  --text "Content" \
  --time "2026-01-26T09:00:00-08:00" \
  --pillar "Deep Agent Architecture" \
  --hook strange
```

## Metricool Info Payload Structure

When using Metricool's `post_schedule_post()` directly:

```json
{
  "text": "Post content here",
  "providers": [{"network": "linkedin"}],
  "media": [
    {
      "url": "https://res.cloudinary.com/dfs5yfioa/...",
      "type": "image"
    }
  ],
  "mediaAltText": ["Alt text for accessibility"],
  "publicationDate": {
    "dateTime": "2026-01-26T09:00:00",
    "timezone": "America/Los_Angeles"
  },
  "autoPublish": true
}
```

**CRITICAL:** The `media` array MUST be present and populated for image/video posts.

## Schedule Format

**ISO 8601 with timezone:**
```
2026-01-26T08:00:00-08:00  # 8am Pacific
2026-01-26T16:00:00+00:00  # 4pm UTC
```

## Best Posting Times

| Platform | Best Times |
|----------|-----------|
| LinkedIn | Mon-Fri 9-11am, 12-2pm |
| Twitter | 9-11am, 12-1pm, 5-6pm |
| Instagram | 11am-1pm, 7-9pm |
| TikTok | 6-10am, 7-11pm |

## Content Tagging (Required)

Every scheduled post MUST include:
- `--pillar` - Content pillar (Deep Agent Architecture, AI Adoption Psychology, etc.)
- `--hook` - Hook type (scary, strange, sexy, free_value, familiar)

## Scheduling Summary

| Scenario | Upload To | Schedule Via | Analytics |
|----------|-----------|--------------|-----------|
| Text only | N/A | Blotato | Optional |
| Image/Video ≤100MB | Cloudinary | Blotato + Metricool | Yes |
| Video >100MB, ≤2 days | GoFile | Blotato only | No |
| Video >100MB, >2 days | Compress first | Cloudinary | Yes |

## Error Handling

| Error | Solution |
|-------|----------|
| URL expired | Re-upload to Cloudinary |
| URL not accessible | Verify with `curl -I` before scheduling |
| File too large for Cloudinary | Use Blotato-only or compress |
| Invalid date | Use ISO 8601 format with timezone |
| Past date | Cannot schedule in the past |
| "Error downloading the image: null" | Include `media` array in payload |

## Related Skills

- `blotato-publisher` - Full API documentation
- `schedule-tracker` - Post tracking and analytics
- `content-pillar-tagger` - Content categorization
- `upload-media` - Media upload utilities
