---
name: insert-broll
description: Insert B-roll footage at specified timestamps or semantic markers. Simpler interface for the common B-roll insertion use case.
allowed-tools: Bash, Read, Write
---

# /insert-broll

Insert B-roll footage at specified timestamps or semantic markers.

**Self-sufficient**: Transcribes videos directly using Whisper.

**AI Image Generation**: When no suitable B-roll exists, can generate contextual images using Nano Banana.

## Usage

```
/insert-broll [video_path] [instruction]
```

**Examples:**
```
/insert-broll /path/to/video.mp4 "Add B-roll at 00:26"
/insert-broll /path/to/video.mp4 "Insert visuals when I mention AI"
```

## Workflow

### Step 1: Check Available B-Roll

```bash
python3 .claude/scripts/video/asset_library.py list --type broll
```

### Step 2: Determine Insertion Points

**For specific timestamp:**
Use timestamp directly from instruction.

**For semantic markers:**
```bash
# Transcribe first
python3 .claude/scripts/video/transcribe_video.py "$VIDEO_PATH" -m base -o /tmp/transcript.json

# Find keywords
python3 .claude/scripts/video/parse_transcript.py /tmp/transcript.json -k "AI" "technology"
```

### Step 3: Generate EDL

```bash
python3 .claude/scripts/video/generate_edl.py \
  --segments /tmp/transcript.json \
  --video "$VIDEO_PATH" \
  --instruction "Add B-roll when AI is mentioned" \
  -o /tmp/edl.json
```

**With AI-generated images** (when no assets match):
```bash
python3 .claude/scripts/video/generate_edl.py \
  --segments /tmp/transcript.json \
  --video "$VIDEO_PATH" \
  --instruction "Add B-roll when AI is mentioned" \
  --generate-images \
  -o /tmp/edl.json
```

### Step 4: Preview Insertions

```bash
cat /tmp/edl.json | jq '.edits[] | {at, duration, asset, reason}'
```

Show user what will be inserted and where.

### Step 5: Execute

```bash
python3 .claude/scripts/video/execute_ffmpeg.py /tmp/edl.json -o "${VIDEO_PATH%.mp4}_with_broll.mp4"
```

## B-Roll Behavior

**Default mode: `replace`**

B-roll REPLACES the main video for 3 seconds:
- Main video disappears during B-roll
- Original audio continues over B-roll
- This is what users expect

## Transition Sound Effects

Add whoosh sounds when B-roll appears. Use quick/standard SFX by default:

| SFX Name | Duration | Use Case |
|----------|----------|----------|
| `swoosh_flying` | 0.57s | Frequent B-rolls |
| `whoosh_fast_transition` | 1.33s | **DEFAULT** |
| `tech_slide` | 2.26s | Tech content |

**In EDL:**
```json
{
  "default_transition_sfx": "whoosh_fast_transition",
  "edits": [...]
}
```

Only use dramatic SFX (`whoosh_epic_trailer`, `impact_epic_trailer`) when explicitly requested.

## Direct AI Image Generation

Generate a single B-roll image/video directly:

```bash
python3 .claude/scripts/video/generate_broll_image.py \
  "Context about AI agents and machine learning" \
  -o /tmp/broll \
  --id custom_broll \
  -d 3.0
```

**Output**:
- Image: `/tmp/broll/broll_custom_broll.png`
- Video: `/tmp/broll/broll_custom_broll.mp4` (3 seconds with Ken Burns effect)

## Notes

- B-roll duration: 3 seconds by default
- Original audio preserved over B-roll
- Multiple insertions processed sequentially
- Output file: `_with_broll.mp4` suffix
- AI images use Nano Banana ($0.039/image) with the creator's brand styling

## Related

For advanced editing (cuts, speed changes, color correction), use `/edit-video` instead.
