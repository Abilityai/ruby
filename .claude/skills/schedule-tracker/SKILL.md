---
name: schedule-tracker
description: Track scheduled and posted content in schedule.json. Use when scheduling content, checking posting status, or analyzing content performance.
automation: manual
allowed-tools: Read, Write, Bash
---

# Schedule Tracker

Maintain and query the content schedule database.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Schedule | `.claude/memory/schedule.json` | ✓ | ✓ | Main schedule database |

## Quick Start

**View upcoming posts:**
```bash
python3 ~/.claude/skills/schedule-tracker/scripts/query.py --status scheduled
```

**Add a new scheduled post:**
```bash
python3 ~/.claude/skills/schedule-tracker/scripts/add_post.py --platform twitter --text "Content" --time "2026-01-26T10:00:00-08:00"
```

**Mark post as completed:**
```bash
python3 ~/.claude/skills/schedule-tracker/scripts/update_status.py --id "post-id-here" --status posted
```

## File Location

```
.claude/memory/schedule.json
```

## Schema

### Post Entry
```json
{
  "id": "unique-post-id-YYYY-MM-DD",
  "created_at": "2026-01-25T12:00:00Z",
  "scheduled_time": "2026-01-26T08:00:00-08:00",
  "posted_time": null,
  "platforms": ["twitter", "linkedin"],
  "content_type": "text|video|image|carousel|thread",
  "content_pillar": "Deep Agent Architecture",
  "hook_type": "strange",
  "content_text": "The actual post content...",
  "media_url": "https://...",
  "media_urls": ["https://...", "https://..."],
  "youtube_cta": "https://youtu.be/...",
  "metricool_ids": {"twitter": "123", "linkedin": "456"},
  "blotato_ids": {"twitter": "789"},
  "status": "scheduled|posted|failed|canceled",
  "notes": "Any additional context",
  "updated_at": "2026-01-25T12:00:00Z"
}
```

### Status Values

| Status | Meaning |
|--------|---------|
| `scheduled` | Queued for future posting |
| `posted` | Successfully published |
| `failed` | Posting attempt failed |
| `canceled` | Manually canceled |
| `unverified` | Posted but not confirmed via API |

## Workflows

### Adding a New Post

1. Generate unique ID: `{topic-slug}-{platform}-{YYYY-MM-DD}`
2. Set `created_at` to current timestamp
3. Set `status` to `scheduled`
4. Include `content_pillar` and `hook_type` (MANDATORY)
5. Write to schedule.json

### After Posting

1. Update `status` to `posted`
2. Set `posted_time` to actual post time
3. Add platform-specific IDs (metricool_ids, blotato_ids)
4. Update `updated_at`

### Querying

**By status:**
```python
posts = [p for p in data["scheduled_posts"] if p["status"] == "scheduled"]
```

**By platform:**
```python
posts = [p for p in data["scheduled_posts"] if "twitter" in p["platforms"]]
```

**By date range:**
```python
from datetime import datetime
start = datetime(2026, 1, 1)
end = datetime(2026, 1, 31)
posts = [p for p in data["scheduled_posts"]
         if start <= parse(p["scheduled_time"]) <= end]
```

## Content Inventory

Track unpublished content separately:

```json
{
  "content_inventory": {
    "unpublished_content_folders": [
      "Video_Topic_Name - 2 threads, 4 LI posts"
    ],
    "unpublished_videos": [
      "video_name.mp4 - ready for posting"
    ],
    "estimated_content_pieces": {
      "twitter_threads": 12,
      "linkedin_posts": 14
    },
    "last_inventory_date": "2026-01-25"
  }
}
```

## Posting Stats

Track performance against targets:

```json
{
  "posting_stats": {
    "period": "2026-01-01 to 2026-01-25",
    "verified_posts": {
      "linkedin": 15,
      "twitter_original": 20,
      "instagram": 10
    },
    "targets_per_week": {
      "linkedin": 5,
      "twitter": 35,
      "instagram": 7
    }
  }
}
```

## 11-Touch Rule

Track touch points per topic/campaign:

```json
{
  "touch_tracking": {
    "Trinity Demo": {
      "touches": 8,
      "first_touch": "2025-12-01",
      "last_touch": "2025-12-15",
      "platforms_used": ["youtube", "twitter", "linkedin"],
      "expires": "2026-03-01"
    }
  }
}
```

**Rule:** 11 exposures before audience notices. Resets every 90 days.

## Best Practices

1. **Always update after posting** - Don't leave stale `scheduled` entries
2. **Include tracking IDs** - metricool_ids, blotato_ids for verification
3. **Tag everything** - content_pillar and hook_type are mandatory
4. **Verify posts** - Cross-check with Metricool API for actual posting
5. **Clean up regularly** - Archive old posts monthly

## Integration Points

- **Blotato Publisher** - Get post IDs after scheduling
- **Metricool Manager** - Verify posting and get analytics
- **Content Pillar Tagger** - Ensure consistent taxonomy

## Completion Checklist

**For adding posts:**
- [ ] schedule.json read fresh
- [ ] Unique ID generated
- [ ] content_pillar and hook_type included (MANDATORY)
- [ ] Entry added with status: scheduled
- [ ] schedule.json written

**For updating status:**
- [ ] Post found by ID
- [ ] Status updated (scheduled → posted/failed/canceled)
- [ ] posted_time set (if posting)
- [ ] Platform IDs recorded (metricool_ids, blotato_ids)
- [ ] updated_at timestamp set
- [ ] schedule.json written

**For queries:**
- [ ] schedule.json read fresh
- [ ] Filtered by requested criteria
- [ ] Results formatted and presented
