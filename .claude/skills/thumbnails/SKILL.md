---
name: thumbnails
description: Generate YouTube thumbnails from video transcript
allowed-tools: Bash, Read, Write
---

# Generate YouTube Thumbnails

Generate 15 YouTube thumbnail images from a video transcript using Gemini AI and reference photos.

## Quick Start

```bash
# Generate thumbnails for a video folder
python3 .claude/scripts/repurpose/generators/thumbnails.py /path/to/folder

# With custom title
python3 .claude/scripts/repurpose/generators/thumbnails.py /path/to/folder --title "Your Custom Title"

# Skip Google Drive upload (local only)
python3 .claude/scripts/repurpose/generators/thumbnails.py /path/to/folder --no-upload
```

## Usage

```
/thumbnails <folder_path> [--mode solo|podcast] [--title "Custom Title"] [--no-upload]
```

**Arguments:**
- `folder_path`: Path to folder containing `transcript.md`
- `--mode`: Thumbnail mode (default: `solo`)
  - `solo`: Single person (creator) - standard videos
  - `podcast`: Two+ people talking - interviews/podcasts
- `--guest-photos`: Path to guest reference photos (alternative to `guests.md`)
  - Can be a directory containing images, or a single image file
  - Supports .png, .jpg, .jpeg formats
  - Up to 6 photos will be used
- `--title`: Optional custom title to use in all thumbnails
- `--no-upload`: Skip uploading to Google Drive
- `--output`: Custom output directory
- `--folder-id`: Google Drive folder ID for upload

## Podcast Mode

For podcasts/interviews, the skill needs guest information. Two options:

### Option 1: guests.md file (recommended)

Create `guests.md` in the video folder:

```markdown
# Podcast Guests

## Mrinal Wadhwa
- slug: mrinal
- twitter: @mrinalwadhwa
- linkedin: linkedin.com/in/mrinalwadhwa
- company: Autonomy
- role: Founder
- photos: guest_photos/mrinal_*.jpg
```

Then run:
```bash
/thumbnails /path/to/folder --mode podcast
```

### Option 2: Direct path

```bash
/thumbnails /path/to/folder --mode podcast --guest-photos /path/to/photos/
```

### [APPROVAL GATE] Guest Verification

Before generating thumbnails, the skill will display loaded guest info:

```
## Guest Profiles

### Guest 1: Mrinal Wadhwa
- Twitter: @mrinalwadhwa
- Photos: 3 found

Is this correct? [Yes / Edit guests.md / Abort]
```

User must confirm guest information is accurate before proceeding.

## Prerequisites

**Required:**
- Folder must contain `transcript.md`
- `GEMINI_API_KEY` environment variable must be set

**Reference Photos:**
- Automatically downloaded from Google Drive (`Reference Photos` folder)
- Cached locally at `~/.cache/ruby/reference_photos/`

## How It Works

1. **Prompt Generation**: Analyzes transcript and generates 15 unique thumbnail prompts using `youtube_thumbnail_prompt_generator_v3.md`
2. **Image Generation**: Calls Gemini Image API (`gemini-3-pro-image-preview`) with:
   - Generated prompt
   - 6 reference photos of the creator
   - 16:9 aspect ratio (YouTube standard)
3. **Output**: Saves images locally
4. **Google Drive Persistence**: Uploads Thumbnails folder to Drive

## Google Drive Persistence

**CRITICAL**: All generated thumbnails MUST be persisted to Google Drive. Local/temp folders are for working only.

After thumbnail generation completes:

```bash
# Upload Thumbnails folder to Drive (if working locally)
python3 .claude/scripts/google/google_drive.py upload-folder \
  "/tmp/Thumbnails_2026-02-11_14:30" \
  <parent_folder_id>
```

| Scenario | Action |
|----------|--------|
| Source is local (e.g., `/tmp/...`) | Upload to video's Drive folder |
| Source is on Drive | Built-in upload via `--folder-id` |
| `--no-upload` flag | Skip (for testing only) |

## Output Structure

```
[Folder]/
├── transcript.md                    # Source (READ-ONLY)
└── Thumbnails_2026-02-04_14:30/     # Timestamped output folder
    ├── thumbnail_01.png
    ├── thumbnail_02.png
    ├── ...
    ├── thumbnail_15.png
    └── _prompts.json                # Generated prompts for reference
```

## Visual Style

Generated thumbnails use the **cinematic lifestyle photography** aesthetic (see `broll-cinematic-lifestyle`):

- **Background**: Blurred with warm pastel red and light grey tones
- **Color Grading**: Kodak Portra 400 film - muted colors, low saturation, lifted shadows, subtle grain
- **Lighting**: Natural soft window light, shot on 35mm f/1.4 lens
- **Subject**: the creator's face from reference photos with authentic expression
- **Text**: White DM Sans Bold with subtle drop shadow
- **Mood**: Warm, human, authentic, emotionally engaging
- **Aspect Ratio**: 16:9 (1920x1080)

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
# Basic usage (solo mode)
/thumbnails Content/01.2026/My_Video_Topic

# Podcast/interview mode - requires guest reference photos
/thumbnails Content/01.2026/My_Podcast --mode podcast --guest-photos /path/to/guest/photos/

# Podcast with single guest image
/thumbnails Content/01.2026/My_Podcast --mode podcast --guest-photos /path/to/guest.jpg

# With custom title (same title on all thumbnails)
/thumbnails Content/01.2026/My_Video_Topic --title "AI Will Change Everything"

# Podcast with custom title
/thumbnails Content/01.2026/My_Podcast --mode podcast --guest-photos ~/Downloads/mrinal/ --title "The Future of AI Agents"

# Local only (no Drive upload)
/thumbnails Content/01.2026/My_Video_Topic --no-upload

# Custom output directory
/thumbnails Content/01.2026/My_Video_Topic --output /tmp/thumbnails
```

## Rate Limits

- Gemini Image API: ~15 requests per minute
- Each run generates 15 images (~2-3 minutes total)
- Built-in rate limiting prevents quota issues

## Completion Checklist

- [ ] Transcript.md exists and is readable
- [ ] Reference photos downloaded (creator + guests if podcast mode)
- [ ] 15 thumbnail prompts generated
- [ ] 15 thumbnail images generated
- [ ] **Thumbnails folder uploaded to Google Drive** (unless --no-upload)
- [ ] **Drive folder link provided to user**

## Related Skills

- `/igcovers` - Generate Instagram cover images (9:16 vertical)
- `/repurpose` - Generate text content from video
- `broll-cinematic-lifestyle` - Full style guide for the visual aesthetic
- `/google-drive-access` - File operations reference
