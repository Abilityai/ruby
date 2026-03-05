---
name: igcovers
description: Generate Instagram cover images from video transcript
allowed-tools: Bash, Read, Write
---

# Generate Instagram Cover Images

Generate 15 Instagram Reels/Stories cover images from a video transcript using Gemini AI and reference photos.

## Quick Start

```bash
# Generate IG covers for a video folder
python3 .claude/scripts/repurpose/generators/igcovers.py /path/to/folder

# With custom title
python3 .claude/scripts/repurpose/generators/igcovers.py /path/to/folder --title "Your Custom Title"

# Skip Google Drive upload (local only)
python3 .claude/scripts/repurpose/generators/igcovers.py /path/to/folder --no-upload
```

## Usage

```
/igcovers <folder_path> [--title "Custom Title"] [--no-upload]
```

**Arguments:**
- `folder_path`: Path to folder containing `transcript.md`
- `--title`: Optional custom title to use in all covers
- `--no-upload`: Skip uploading to Google Drive
- `--output`: Custom output directory
- `--folder-id`: Google Drive folder ID for upload

## Prerequisites

**Required:**
- Folder must contain `transcript.md`
- `GEMINI_API_KEY` environment variable must be set

**Reference Photos:**
- Automatically downloaded from Google Drive (`Reference Photos` folder)
- Cached locally at `~/.cache/ruby/reference_photos/`

## How It Works

1. **Prompt Generation**: Analyzes transcript and generates 15 unique cover prompts using `igcover_prompt_generator_v1.md`
2. **Image Generation**: Calls Gemini Image API (`gemini-3-pro-image-preview`) with:
   - Generated prompt
   - 6 reference photos of the creator
   - 9:16 aspect ratio (Instagram vertical standard)
3. **Output**: Saves images locally and optionally uploads to Google Drive

## Output Structure

```
[Folder]/
├── transcript.md                    # Source (READ-ONLY)
└── IGCovers_2026-02-04_14:30/       # Timestamped output folder
    ├── igcover_01.png
    ├── igcover_02.png
    ├── ...
    ├── igcover_15.png
    └── _prompts.json                # Generated prompts for reference
```

## Visual Style

Generated covers follow the creator's brand guidelines:
- **Background**: Light gray (#efefef)
- **Text**: Dark gray (#292929) in DM Sans Bold
- **Accent**: Vibrant red (#ff0000) circular gradient (85% transparent)
- **Aspect Ratio**: 9:16 vertical (1080x1920)
- **Optimized for**: Instagram Stories, Reels, TikTok

## Configuration

**Environment Variables:**
```bash
GEMINI_API_KEY=your_api_key_here  # Required
```

**Timeouts & Retries:**
- Image generation: 3 minutes per image
- Retry attempts: 3 with 5-second delay
- Rate limiting: 2 seconds between generations

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "transcript.md not found" | Missing source file | Add transcript to folder |
| "GEMINI_API_KEY not set" | Missing API key | Set GEMINI_API_KEY in .env |
| "No reference photos" | Photos not downloaded | Check Google Drive access |
| "Failed to generate" | API error | Check API quota, retry |

## Examples

```bash
# Basic usage
/igcovers Content/01.2026/My_Video_Topic

# With custom title (same title on all covers)
/igcovers Content/01.2026/My_Video_Topic --title "The Future of AI Agents"

# Local only (no Drive upload)
/igcovers Content/01.2026/My_Video_Topic --no-upload

# Custom output directory
/igcovers Content/01.2026/My_Video_Topic --output /tmp/igcovers
```

## Vertical Format Optimization

IG covers are optimized for the 9:16 vertical format:
- Subject positioning in lower/upper portions of frame
- Text layouts: top, bottom, center overlay, stacked
- Mobile-first readability
- Works for Instagram Stories, Reels, and TikTok

## Rate Limits

- Gemini Image API: ~15 requests per minute
- Each run generates 15 images (~2-3 minutes total)
- Built-in rate limiting prevents quota issues

## Related Skills

- `/thumbnails` - Generate YouTube thumbnails (16:9 horizontal)
- `/repurpose` - Generate text content from video
