---
name: schedule-week
description: Plan and schedule content for the upcoming week. Use when user asks to "plan the week", "schedule content", or "what should we post".
automation: gated
allowed-tools: Bash, Read, Write
calls:
  - content-library
  - schedule-tracker
  - schedule-post
  - content-pillar-tagger
---

# Schedule Week

Plan and schedule the content calendar for the upcoming week.

## Purpose

Create a balanced weekly content schedule that covers all platforms and content pillars.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Schedule | `.claude/memory/schedule.json` | ✓ | ✓ | Current schedule + new posts |
| Content Library | `.claude/memory/content_library.yaml` | ✓ | | Available content |
| Content Inventory | Generated Content folders | ✓ | | Unpublished content |
| Output Calendar | `.claude/reports/calendars/` | | ✓ | Weekly calendar file |

---

## Process

### Step 1: Read Current State

**Read fresh state at start.**

```bash
# Read current schedule
cat .claude/memory/schedule.json | jq '.scheduled_posts[] | select(.status == "scheduled")'

# Read content library for available content
cat .claude/memory/content_library.yaml

# Check what's been posted recently
cat .claude/memory/schedule.json | jq '.scheduled_posts[-20:] | .[] | select(.status == "posted")'
```

### Step 2: Audit Existing Content

Analyze:
- What's been posted recently (avoid repetition)
- What angles are underutilized
- What performed well (replicate)
- What content is available in Generated Content folders

### Step 3: Apply Weekly Targets

| Day | Twitter | LinkedIn | Other |
|-----|---------|----------|-------|
| Mon | 8-10 posts | 1 post | - |
| Tue | 8-10 posts | 1 post | - |
| Wed | 8-10 posts | 1 post | - |
| Thu | 8-10 posts | 1 post | - |
| Fri | 8-10 posts | 1 post | - |
| Sat | 3-5 posts | - | - |
| Sun | 3-5 posts | - | - |

**Optimal Posting Times (EST):**
- **Best:** Wednesday 9 AM
- **Strong:** Tuesday/Thursday 9 AM
- **Good:** Monday/Friday 10 AM

### Step 4: Generate Draft Schedule

[APPROVAL GATE] - Review draft schedule before finalizing

Present to user:

```markdown
# Content Calendar: Week of [DATE]

## Monday
- [ ] 9:00 AM - Twitter: [content preview] (pillar: X, hook: Y)
- [ ] 10:00 AM - LinkedIn: [content preview] (pillar: X, hook: Y)
- [ ] 2:00 PM - Twitter: [content preview]

## Tuesday
- [ ] 9:00 AM - Twitter: [THREAD] [title] (pillar: X)
...

## Content Gaps
- Need more [pillar] content
- Video X not yet ready

## Notes
- [Any scheduling considerations]
```

Wait for user approval or modifications.

### Step 5: Schedule Approved Content

For each approved post:

```bash
python3 ~/.claude/skills/schedule-tracker/scripts/add_post.py \
  --platform twitter \
  --text "Content" \
  --time "2026-02-10T09:00:00-08:00" \
  --pillar "Deep Agent Architecture" \
  --hook "strange"
```

Or use `/schedule-post` for each item.

### Step 6: Write Updated State

**Write all state changes.**

1. Update schedule.json with new entries
2. Save calendar to `.claude/reports/calendars/week_[DATE].md`

---

## Arguments

- `--start [YYYY-MM-DD]`: Week starting date (default: next Monday)
- `--dry-run`: Preview without scheduling
- `--pillars [list]`: Focus on specific content pillars
- `--include-threads`: Include thread launches

## Example Usage

```bash
/schedule-week
/schedule-week --start 2026-02-10
/schedule-week --pillars "Trinity Platform,Deep Agent Architecture"
/schedule-week --dry-run
```

---

## Content Pillar Balance

Ensure weekly coverage:
1. **Trinity Platform** - 30% of content
2. **Deep Agent Architecture** - 25%
3. **AI Adoption Psychology** - 20%
4. **Shallow vs Deep** - 15%
5. **Production Patterns** - 10%

Tag every post with pillar + hook type (MANDATORY).

---

## Completion Checklist

- [ ] Current schedule read fresh
- [ ] Content library read fresh
- [ ] Recent posts analyzed (avoid repetition)
- [ ] Available content inventory checked
- [ ] Draft calendar created with targets
- [ ] Content pillars balanced across week
- [ ] [APPROVAL GATE] User approved schedule
- [ ] Posts scheduled via schedule-tracker
- [ ] schedule.json updated
- [ ] Calendar saved to reports folder
- [ ] User notified of completion

## Error Recovery

If scheduling fails mid-execution:

1. **Check partial state:**
   ```bash
   cat .claude/memory/schedule.json | jq '.scheduled_posts | length'
   ```

2. **Common issues:**
   - Blotato API error: Retry individual posts
   - Invalid time format: Fix and retry

3. **Recovery:**
   - Note which posts were scheduled vs. pending
   - Resume from first failed post
