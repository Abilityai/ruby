---
name: content-library
description: Manage long-form content workflow for articles and YouTube videos. Use when checking "content status", "what needs review", "article pipeline", tracking YouTube repurposing, or marking content as published. Also use when user says "I published X" or asks "what articles are pending".
automation: manual
allowed-tools: Read, Write, Bash, Glob
argument-hint: [command] [args]
---

# Content Library

Manage the workflow for long-form content (articles, YouTube videos) from creation through publishing.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Content Library | `.claude/memory/content_library.yaml` | ✓ | ✓ | Main tracking database |
| Published Archive | `.claude/memory/published_content.md` | ✓ | ✓ | Historical archive |
| Article Drafts | `Articles/drafts/` (Google Drive) | ✓ | | Draft folder structure |
| Article Published | `Articles/published/` (Google Drive) | | ✓ | Published folder (move target) |

## Quick Reference

| Command | Description |
|---------|-------------|
| `/content-library` | Show content needing attention |
| `/content-library articles` | List all articles by status |
| `/content-library youtube` | List YouTube videos and repurposing status |
| `/content-library add article "Title"` | Add new article |
| `/content-library add youtube "Title" [url]` | Add new YouTube video |
| `/content-library status [id]` | Show status of specific content |
| `/content-library update [id] [status]` | Update content status |
| `/content-library publish [id] [platform] [url]` | Mark as published |

## File Location

```
.claude/memory/content_library.yaml
```

## Content Types

### Articles

Long-form written content requiring manual publishing:
- LinkedIn Articles
- Medium posts
- X/Twitter Articles (Premium only)
- Substack posts
- Blog posts

**Workflow:** `idea` -> `draft` -> `review` -> `approved` -> `published`

### YouTube Videos

Published videos tracked for repurposing:
- Track what's been repurposed
- Identify videos needing content distribution
- Monitor repurposing completeness

**Workflow:** `published` (always - videos are already on YouTube)

## Workflow Commands

### Show Content Needing Attention

When invoked without arguments, show:
1. Articles in `review` status (waiting for the creator)
2. Articles in `approved` status (ready to publish)
3. YouTube videos with incomplete repurposing

```bash
# Read the content library
cat .claude/memory/content_library.yaml
```

Then summarize:
- **Needs Review:** [count] articles
- **Ready to Publish:** [count] articles
- **Needs Repurposing:** [count] videos

### Add New Article

When user creates an article via `/create-article` or manually:

1. Generate ID from title (kebab-case)
2. Add entry to `content_library.yaml`
3. Set status to `draft`
4. Set `drive_path` to `Articles/drafts/[id]`

```yaml
- id: article-id-here
  title: "Article Title"
  status: draft
  drive_path: Articles/drafts/article-id-here
  created: 2026-02-10
  pillars: []
  target_platforms: []
  published: {}
  notes: ""
```

### Update Status

Valid transitions:
- `idea` -> `draft` (content written)
- `draft` -> `review` (ready for the creator)
- `review` -> `approved` (user approved)
- `review` -> `draft` (needs changes)
- `approved` -> `published` (manually published)

When updating to `published`:
1. Update status in content_library.yaml
2. Move folder from `Articles/drafts/` to `Articles/published/` in Google Drive
3. Add entry to `published_content.md`

### Mark as Published

When user says "I published [article] to [platform]":

1. Find the article by ID or title match
2. Add platform to `published` dict with date and URL
3. If all target platforms published, update status to `published`
4. Update `published_content.md` archive

```yaml
published:
  linkedin:
    date: 2026-02-10
    url: https://linkedin.com/pulse/...
  medium:
    date: 2026-02-11
    url: https://medium.com/@yourhandle/...
```

### Add YouTube Video

When a new YouTube video is published:

1. Generate ID from title
2. Add entry with `status: published`
3. Initialize repurposing counters to 0

```yaml
- id: video-id-here
  title: "Video Title"
  status: published
  drive_path: Content/MM.YYYY/Folder_Name
  published_date: 2026-02-10
  youtube_url: https://youtu.be/...
  pillars: []
  repurposed:
    twitter_threads: 0
    linkedin_posts: 0
    newsletters: 0
    shorts: 0
  notes: ""
```

### Track Repurposing

When social content is posted from a video:

1. Find the YouTube video entry
2. Increment the appropriate counter
3. Update `last_updated` in metadata

## Google Drive Integration

### Article Folder Structure

```
Shared Drive/
└── Articles/
    ├── drafts/           # Work in progress
    │   └── [article-id]/
    │       ├── article.md
    │       └── images/
    └── published/        # Completed articles
        └── [article-id]/
```

### Creating Article Folder

Use Google Drive API:
```bash
# Ensure Articles folder exists
python3 .claude/scripts/google/google_drive.py ensure-path "Articles/drafts"
python3 .claude/scripts/google/google_drive.py ensure-path "Articles/published"

# Create article folder
python3 .claude/scripts/google/google_drive.py mkdir "[article-id]" [drafts-folder-id]
```

### Moving to Published

When article is fully published:
```bash
python3 .claude/scripts/google/google_drive.py move [article-folder-id] [published-folder-id]
```

## Integration Points

### With /create-article

After creating an article:
1. `/create-article` generates content
2. Automatically add to content_library.yaml as `draft`
3. Create folder in `Articles/drafts/`

### With schedule.json

Content library tracks long-form content workflow.
Schedule.json tracks social post scheduling.
They are complementary, not overlapping.

### With published_content.md

When content is published:
1. Update content_library.yaml status
2. Add entry to published_content.md archive
3. Include platform, date, URL

## Examples

### Example 1: Check What Needs Attention

User: "What content needs my review?"

Actions:
1. Read content_library.yaml
2. Filter articles where status = "review"
3. List with titles and created dates

Response: "You have 2 articles waiting for review: 'Trinity Architecture' (created Feb 8) and 'Memory Patterns' (created Feb 5)"

### Example 2: Mark Article Published

User: "I just published the Trinity article on LinkedIn"

Actions:
1. Find article matching "trinity" in content_library.yaml
2. Add to published dict: `linkedin: {date: 2026-02-10, url: "..."}`
3. Ask for URL if not provided
4. Check if all target platforms done
5. Update published_content.md

Response: "Updated 'Trinity Architecture' - published to LinkedIn. Still pending: Medium, X Article."

### Example 3: Video Needs Repurposing

User: "What videos need repurposing?"

Actions:
1. Read content_library.yaml youtube section
2. Find videos where repurposed totals are low
3. List with repurposing stats

Response: "Claude Code Dev Workflow has 0 repurposed content. Sovereign Agents has 5 pieces out, newsletter still pending."

## Troubleshooting

### Article Not Found

If user references an article that doesn't exist:
1. Search by partial title match
2. List similar articles
3. Offer to add new entry

### Status Transition Invalid

If user tries invalid status change (e.g., draft -> published):
- Explain the workflow stages
- Suggest correct next status
- Allow override if user insists

### Google Drive Sync Issues

If Drive folder doesn't match yaml:
- Yaml is source of truth for status
- Drive is source of truth for content
- Reconcile by checking both

## Completion Checklist

**For status queries:**
- [ ] content_library.yaml read fresh
- [ ] Filtered by requested status/type
- [ ] Summary presented to user

**For adding content:**
- [ ] ID generated (kebab-case from title)
- [ ] Entry added to content_library.yaml
- [ ] Drive folder created (if article)
- [ ] Status set appropriately

**For status updates:**
- [ ] Entry found by ID or title match
- [ ] Status transition validated
- [ ] content_library.yaml updated
- [ ] published_content.md updated (if publishing)
- [ ] Drive folder moved (if publishing article)

**For publishing:**
- [ ] Platform and URL recorded
- [ ] All target platforms checked
- [ ] Status updated to published (if complete)
- [ ] published_content.md archive entry added
