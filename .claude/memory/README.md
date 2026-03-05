# Ruby Memory Directory

This directory contains Ruby's local state tracking files. These files maintain the agent's knowledge of scheduled posts, content workflow status, and engagement tracking.

## Files

### `schedule.json` (from schedule.template.json)
Main schedule tracker file that mirrors your posting platform's scheduling queue.

**Why we need this:**
- Many posting APIs don't provide GET endpoints to query scheduled posts
- This local tracker allows Ruby to know what's scheduled
- Provides a single source of truth for scheduled content

**Structure:** `scheduled_posts[]`, `content_inventory`, `posting_stats`, `touch_tracking`, `metadata`
**Status values:** `scheduled`, `posted`, `failed`, `canceled`

### `content_library.yaml` (from content_library.template.yaml)
Tracks long-form content workflow for articles and YouTube videos.

**Article workflow:** idea -> draft -> review -> approved -> published
**YouTube tracking:** Videos + repurposing completeness (threads, LinkedIn posts, newsletters, shorts)

### `reply_queue.json` (from reply_queue.template.json)
Queue of Twitter replies waiting to be posted. Populated by `/find-viral-replies`, consumed by `/post-queued-replies`.

### `twitter_replies.txt`
Plain text file of reply drafts. Created empty, populated during Twitter engagement workflows.

## Setup

Copy templates to create your live state files:

```bash
cp schedule.template.json schedule.json
cp content_library.template.yaml content_library.yaml
cp reply_queue.template.json reply_queue.json
touch twitter_replies.txt
```

## Best Practices

1. **Always update after scheduling** - Keep the tracker in sync with your posting platform
2. **Use consistent ID format** - Makes entries easy to find (e.g., `post-YYYY-MM-DD-platform`)
3. **Update status after posts publish** - Keeps history accurate
4. **Don't delete old entries** - Keep for audit trail
5. **Verify posting platform dashboard** - This is a mirror, not the source of truth

## Integration

| File | Updated By | Read By |
|------|------------|---------|
| `schedule.json` | `/schedule-post`, `/schedule-prepared-content` | `/schedule-tracker`, all publishing skills |
| `content_library.yaml` | `/content-library`, `/create-article` | `/repurpose`, `/schedule-week` |
| `reply_queue.json` | `/find-viral-replies` | `/post-queued-replies` |
