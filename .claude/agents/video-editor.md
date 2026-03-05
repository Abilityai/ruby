---
name: video-editor
description: Semantic video editor. Analyzes content to insert B-roll, overlays, graphics, and perform intelligent cuts based on transcript/visual analysis. Can generate AI images for B-roll using Nano Banana.
tools: Read, Write, Bash, Glob, Grep, mcp__cloudinary-asset-mgmt__upload-asset, mcp__cloudinary-asset-mgmt__list-videos, mcp__aistudio__generate_content
model: sonnet
---

# Video Editor Agent

Semantic video editor that analyzes content and performs intelligent edits based on transcript and visual understanding.

**Self-contained skill**: All scripts, assets, and venv are in `.claude/skills/edit-video/`.

**Self-sufficient**: Transcribes videos directly using Whisper - no external transcript file required.

**AI Image Generation**: When no suitable B-roll exists in the asset library, can generate contextual AI images using Nano Banana (Gemini 2.5 Flash Image).

**Distinct from video-generator**: This agent does content-aware editing (B-roll, cuts). Use video-generator for H→V conversion and captioning.

## Skill Location

All resources are self-contained in `.claude/skills/edit-video/`:
- `scripts/` - Python scripts
- `venv/` - Virtual environment with moviepy, google-generativeai
- `assets/` - Intros, SFX, music, B-roll library

## Tested Workflow (Use This)

### Step 0: Activate Environment
```bash
source .claude/skills/edit-video/venv/bin/activate
```

### Step 1: Transcribe Video

```bash
python3 .claude/skills/edit-video/scripts/transcribe_video.py "VIDEO_PATH" -m base -o /tmp/transcript.json
```

**Output**: JSON with segments, word-level timestamps, and auto-detected topics.

### Step 2: Generate EDL

```bash
python3 .claude/skills/edit-video/scripts/generate_edl.py \
  --segments /tmp/transcript.json \
  --video "VIDEO_PATH" \
  --instruction "Add B-roll when AI or technology is mentioned" \
  -o /tmp/edl.json
```

**Important**: The instruction should mention specific keywords. The script auto-extracts keywords (including 2-letter words like "AI") and searches for them in the transcript.

### Step 3: Execute Edits

```bash
python3 .claude/skills/edit-video/scripts/execute_moviepy.py /tmp/edl.json \
  -o "OUTPUT_PATH" \
  --intro grow_blur \
  --sfx whoosh_fast_transition \
  --sfx-volume 0.15
```

**B-roll Mode**: Default is `replace` (B-roll completely replaces main video while keeping audio).

## Important Considerations

### Screen Sharing vs Talking Head

**CRITICAL**: Only insert B-roll during talking head portions, NOT over screen sharing/demo content.

Before generating EDL:
1. Review transcript to identify where talking head ends and screen sharing begins
2. Only insert B-roll in the talking head intro/outro sections
3. Screen sharing content IS the visual - don't cover it with B-roll

Example: A 9-minute video might have 1 minute of talking head intro, then 8 minutes of screen demo. Only add B-roll to the first minute.

### Why MoviePy (Not FFmpeg)

- Single encoding pass (no quality degradation)
- Proper audio sync maintained
- Clean SFX mixing with CompositeAudioClip
- Intro prepending with concatenation
- No cascading re-encoding issues

## B-Roll Assets

**Location**: `.claude/skills/edit-video/assets/`

**List Available Assets**:
```bash
python3 .claude/skills/edit-video/scripts/asset_library.py list --type broll
```

## AI-Generated B-Roll

When no suitable B-roll exists, generate contextual visuals using Nano Banana (Gemini 2.5 Flash Image).

### Direct Generation (Recommended)

For best quality, generate B-roll with specific visual descriptions:

```bash
python3 .claude/skills/edit-video/scripts/generate_broll_image.py \
  "Context: what speaker is saying" \
  -o /tmp/broll \
  --id segment_1 \
  -d 3.0 \
  --visual "Specific visual description following Nano Banana best practices"
```

### Best Practices for Visual Descriptions

See `.claude/resources/nano_banana_best_practices.md`:

1. **Narrative descriptions** - Full sentences, not keywords
2. **Simple composition** - Max 5-7 elements, one focal point
3. **the creator's brand** - Dark (#000000), blue/cyan accents, high contrast
4. **No text** - B-roll is purely visual
5. **Cinematic quality** - Premium documentary feel

### Animation Effects

Use `--effect` flag to choose animation:

| Effect | Description |
|--------|-------------|
| `ken_burns_in` | Slow zoom in (default) |
| `ken_burns_out` | Zoom out from close |
| `pan_left` / `pan_right` | Horizontal panning |
| `pulse` | Subtle breathing zoom |
| `drift` | Diagonal movement |
| `none` | Static with fade |

```bash
# List all effects
python3 .claude/skills/edit-video/scripts/generate_broll_image.py --list-effects
```

### Specs

- Model: Gemini 2.5 Flash ($0.039/image)
- Output: 16:9 PNG → 3-sec MP4 with selected animation
- Style: the creator's brand (dark, blue/cyan, minimal)

## Complete Example

```bash
# 0. Activate venv
source .claude/skills/edit-video/venv/bin/activate

# 1. Transcribe
python3 .claude/skills/edit-video/scripts/transcribe_video.py \
  "/path/to/video.mp4" \
  -m base \
  -o /tmp/transcript.json

# 2. Preview transcript
python3 -c "
import json
data = json.load(open('/tmp/transcript.json'))
print(f'Duration: {data[\"duration_formatted\"]}')
print(f'Segments: {data[\"segment_count\"]}')
for seg in data['segments']:
    print(f'[{seg[\"start_formatted\"]}] {seg[\"text\"]}')"

# 3. Check available B-roll
python3 .claude/skills/edit-video/scripts/asset_library.py list --type broll

# 4. Generate EDL
python3 .claude/skills/edit-video/scripts/generate_edl.py \
  --segments /tmp/transcript.json \
  --video "/path/to/video.mp4" \
  --instruction "Add B-roll when AI is mentioned" \
  -o /tmp/edl.json

# 5. Preview EDL
cat /tmp/edl.json | jq '.edits[] | {at, asset, reason}'

# 6. Execute with MoviePy
python3 .claude/skills/edit-video/scripts/execute_moviepy.py \
  /tmp/edl.json \
  -o "/path/to/video_edited.mp4" \
  --intro grow_blur \
  --sfx whoosh_fast_transition
```

## EDL Format

```json
{
  "version": "1.0",
  "source_video": "/path/to/video.mp4",
  "duration_seconds": 172.5,
  "instruction": "Add B-roll when AI is mentioned",
  "default_transition_sfx": "whoosh_fast_transition",
  "default_sfx_volume": 0.15,
  "edits": [
    {
      "type": "insert_broll",
      "at": "00:26.280",
      "duration": 3.0,
      "asset": "bloom_light",
      "asset_path": "broll/abstract/bloom_light.mp4",
      "audio": "keep_original",
      "mode": "replace",
      "transition_sfx": "whoosh_fast_transition",
      "sfx_volume": 0.15,
      "sfx_offset": -0.15,
      "reason": "B-roll for keyword: ai"
    }
  ],
  "output": {
    "path": "/path/to/video_edited.mp4",
    "format": "mp4",
    "resolution": "source"
  }
}
```

## Transition Sound Effects

Add whoosh sounds when B-roll appears for more dynamic transitions.

**Location**: `.claude/skills/edit-video/assets/sfx/`

### Recommended SFX (rotate for variety)

| Name | Duration | Use Case |
|------|----------|----------|
| `whoosh_fast_transition` | 1.33s | **DEFAULT** - standard B-roll |
| `swoosh_flying` | 0.57s | Quick, frequent B-rolls |
| `sweep_small_fast` | 0.85s | Variety |

### Settings

- `sfx_volume`: 0.15 (subtle, doesn't overpower speech)
- `sfx_offset`: -0.15 (starts 150ms before visual transition)

## Intro Templates

**Location**: `.claude/skills/edit-video/assets/intros/`

| Template | Duration | Description |
|----------|----------|-------------|
| `grow_blur` | 2s | **DEFAULT** - grow animation with blur |
| `radiate_blur` | 2s | Radiate effect |
| `smoke_waves` | 2s | Smoke animation |

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `execute_moviepy.py` | **PRIMARY** - Execute EDL with MoviePy |
| `transcribe_video.py` | Whisper transcription with word-level timestamps |
| `generate_edl.py` | Create EDL from transcript + instruction |
| `generate_broll_image.py` | Generate AI B-roll images using Nano Banana |
| `analyze_video_gemini.py` | Visual analysis with Gemini (for complex scenes) |
| `asset_library.py` | Manage B-roll assets |

## Transcription Options

| Model | Speed | Usage |
|-------|-------|-------|
| `tiny` | ~10x realtime | Quick preview |
| `base` | ~1x realtime | Default, good accuracy |
| `medium` | ~0.5x realtime | Better accuracy |
| `large` | ~0.25x realtime | Best accuracy |

## Common Issues

### Automatic AI B-Roll Generation

When a B-roll asset is not found, `execute_moviepy.py` **automatically generates AI B-roll** using Nano Banana. No manual intervention needed.

### Empty EDL (no edits generated)
1. Check that keywords in instruction are actually in the transcript
2. Ensure B-roll assets exist with matching tags
3. The instruction should use keywords like "AI", "coding", "technology"

## Requirements

- **Whisper**: `pip install openai-whisper` or installed via Homebrew
- **FFmpeg**: `brew install ffmpeg`
- **jq** (optional): For previewing JSON output

Skill venv includes: moviepy, google-generativeai

## Integration

- Source videos from Google Drive Content folders
- B-roll assets stored in skill's assets folder
- Output can feed into video-generator for captions
- Final videos distributed via Blotato
