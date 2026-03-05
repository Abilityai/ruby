---
name: schedule-prepared-content
description: Schedule social media content from a Generated Content folder. Use when processing repurposed video content.
allowed-tools: Bash, Read, Write
depends-on: blotato-publisher, schedule-tracker, content-pillar-tagger
---

# Schedule Prepared Content

Schedule social media content from a "Generated Content" folder produced by the CEO Content Engine.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Schedule Tracker | `.claude/memory/schedule.json` | ✓ | ✓ | Check conflicts, track posts |
| Generated Content | `[folder]/Generated Content_*/` | ✓ | | Source content files |

## Quick Start

```bash
# List files in Generated Content folder
ls "Shared Drive/Content/01.2026/Topic_Name/Generated Content/"

# Schedule a text post
python3 ~/.claude/skills/blotato-publisher/scripts/post.py \
  --platform twitter,linkedin \
  --text "CONTENT" \
  --schedule "2026-01-26T14:00:00-08:00"
```

## Workflow

### Step 0: Check Existing Schedule (REQUIRED)

**Before proposing any times, read the current schedule:**

```bash
cat .claude/memory/schedule.json | jq '
  .scheduled_posts[] |
  select(.status=="scheduled") |
  {date: .scheduled_time[0:10], time: .scheduled_time[11:19], platforms, preview: .content_text[0:40]}
' | head -50
```

**Use this to:**
1. Identify which dates/times are already booked
2. Avoid proposing times within 2 hours of existing posts
3. If conflicts are unavoidable, flag them explicitly in Step 4

### Step 1: Get Content Folder Path

Ask user for the Generated Content folder path:
- Example: `Shared Drive/Content/01.2026/Topic_Name/Generated Content`

### Step 2: Analyze Folder Contents

List and categorize files by type:

| File Pattern | Type | Platform |
|-------------|------|----------|
| `text_post_*.md` | Short cross-platform posts | Twitter, LinkedIn, Threads |
| `linkedin_post_*.md` | LinkedIn long-form posts | LinkedIn only |
| `community_post_*.md` | Community engagement posts | YouTube Community |
| `twitter_thread_*.md` | Twitter threads | Twitter (manual or Blotato) |
| `linkedin_carousel_*.pdf` | LinkedIn carousels | LinkedIn (manual upload) |
| `newsletter_*.md` | Email newsletters | Substack (manual) |

### Step 3: Preview Content

Read the first few lines of each file to show the user what content will be scheduled.

### Step 4: Propose Scheduling Plan

Calculate times starting from user-specified time:
- Space posts 2-4 hours apart
- Suggest appropriate platforms for each post type
- Show complete schedule in table format

```
PROPOSED SCHEDULE:

Automated Posts (via Blotato API):

| Time | Platforms | Content Preview |
|------|-----------|----------------|
| 2 PM | Twitter, LinkedIn | "Your AI model has a personality..." |
| 4 PM | LinkedIn | "The biggest mistake people make..." |

Manual Posts Required:
- LinkedIn Carousels (PDFs) - Post via LinkedIn UI
- Twitter Threads - Use Blotato or Twitter MCP
- Newsletters - Use email platform
```

### Step 5: Get User Confirmation

Present schedule and ask: "Ready to schedule these posts? (yes/no)"

### Step 6: Schedule Posts

For each approved post:

```bash
# Schedule via Blotato
python3 ~/.claude/skills/blotato-publisher/scripts/post.py \
  --platform twitter,linkedin \
  --text "CONTENT" \
  --schedule "2026-01-26T14:00:00-08:00"

# Track in schedule.json
python3 ~/.claude/skills/schedule-tracker/scripts/add_post.py \
  --platform twitter,linkedin \
  --text "CONTENT" \
  --time "2026-01-26T14:00:00-08:00" \
  --pillar "Deep Agent Architecture" \
  --hook strange
```

### Step 7: Provide Summary

```
SCHEDULED SUCCESSFULLY:

- 3 posts scheduled via Blotato
- Submission IDs: [list them]
- Added to schedule tracker: .claude/memory/schedule.json

MANUAL POSTING CHECKLIST:
- [ ] Upload LinkedIn Carousels
- [ ] Post Twitter threads
- [ ] Schedule newsletters
```

## Content Types Reference

| Type | Automation | Notes |
|------|------------|-------|
| Text posts | Full auto | Works on all platforms |
| Image posts | Full auto | Upload to Cloudinary first |
| LinkedIn posts | Full auto | Platform-specific formatting |
| Community posts | Full auto | YouTube Community tab |
| Twitter threads | Partial | Use Blotato or Twitter MCP (NOT Metricool) |
| Carousels | Manual | Upload PDF via LinkedIn UI |
| Newsletters | Manual | Copy to Substack/email platform |

## Important Notes

- **Convert times to ISO 8601** format with timezone
- **Space posts 2+ hours apart**
- Default platforms for text posts: `twitter,linkedin`
- **Never post without user confirmation**
- **Twitter max 4 images/tweet** - exclude Twitter for larger carousels
- **Tag all posts** with content_pillar and hook_type

## Related Skills

- `blotato-publisher` - API posting
- `schedule-tracker` - Track scheduled content
- `content-pillar-tagger` - Content categorization
