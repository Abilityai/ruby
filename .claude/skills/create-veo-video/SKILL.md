---
name: create-veo-video
description: Generate AI videos using Google Veo 3.1 via Vertex AI. Use for cinematic B-roll, product demos, or any AI-generated video content (not avatar videos - use create-heygen-video for HeyGen avatars).
allowed-tools: Bash, Read, Write
---

# Create Veo Video

Generate AI videos using Google's Veo 3.1 model via Vertex AI. Produces 8-second cinematic clips with audio.

## Quick Start

```bash
# Simple generation
.claude/skills/create-veo-video/.venv/bin/python \
  .claude/skills/create-veo-video/scripts/generate_video.py \
  "A coffee cup steaming on a wooden table, morning light" \
  /tmp/coffee.mp4

# Vertical video for social
.claude/skills/create-veo-video/.venv/bin/python \
  .claude/skills/create-veo-video/scripts/generate_video.py \
  "Person walking through city streets" \
  /tmp/walk.mp4 --aspect 9:16

# With reference images for consistency
.claude/skills/create-veo-video/.venv/bin/python \
  .claude/skills/create-veo-video/scripts/generate_video.py \
  "Woman making coffee in kitchen" \
  /tmp/video.mp4 --ref /path/to/face.png /path/to/body.png
```

## Usage

```
/create-veo-video <prompt> [output_path] [--aspect 16:9|9:16] [--model MODEL]
```

**Parameters:**
- **prompt**: Detailed description of the video scene
- **output_path**: Where to save (default: /tmp/veo_output.mp4)
- **--aspect**: 16:9 (horizontal), 9:16 (vertical), 1:1 (square)
- **--model**: veo-3.1-generate-preview (default), veo-3.1-fast-generate-preview
- **--ref**: Reference images for character/object consistency

**Examples:**
```
/create-veo-video "Coffee being poured into a white mug, steam rising"
/create-veo-video "Person typing on laptop" --aspect 9:16
/create-veo-video "Woman walking" --ref face.png body.png
```

## Scripts

### generate_video.py - Single Video Generation

```bash
VENV=.claude/skills/create-veo-video/.venv/bin/python
SCRIPT=.claude/skills/create-veo-video/scripts/generate_video.py

# Basic usage
$VENV $SCRIPT "prompt" output.mp4

# With options
$VENV $SCRIPT "prompt" output.mp4 --aspect 9:16 --model veo-3.1-fast-generate-preview

# With reference images
$VENV $SCRIPT "prompt" output.mp4 --ref image1.png image2.png
```

### chain_video.py - Create Longer Videos

Chain multiple 8-second clips for longer videos using frame-to-video technique:

```bash
VENV=.claude/skills/create-veo-video/.venv/bin/python
SCRIPT=.claude/skills/create-veo-video/scripts/chain_video.py

# Step 1: Generate first clip, extract last frame
$VENV $SCRIPT --generate "Initial scene description" \
  --output clip_01.mp4 \
  --extract-last clip_01_last.png \
  --ref face.png

# Step 2: Continue from last frame
$VENV $SCRIPT --first-frame clip_01_last.png \
  --prompt "Continue the scene..." \
  --output clip_02.mp4 \
  --extract-last clip_02_last.png

# Step 3: Repeat for more clips
$VENV $SCRIPT --first-frame clip_02_last.png \
  --prompt "Final action..." \
  --output clip_03.mp4

# Step 4: Concatenate with ffmpeg
ffmpeg -f concat -safe 0 -i <(echo -e "file 'clip_01.mp4'\nfile 'clip_02.mp4'\nfile 'clip_03.mp4'") -c copy final.mp4
```

### Extract Frame from Existing Video

```bash
$VENV $SCRIPT --extract-from existing.mp4 --extract-last last_frame.png
```

## Models

| Model | Quality | Speed | Use Case |
|-------|---------|-------|----------|
| `veo-3.1-generate-preview` | Highest | 2-5 min | Production content |
| `veo-3.1-fast-generate-preview` | Good | 1-2 min | Drafts, testing |
| `veo-3.0-generate-001` | Good | 2-4 min | Older, stable |
| `veo-3.0-fast-generate-001` | OK | 1-2 min | Quick tests |

## Prompt Best Practices

1. **Be specific about scene elements**
   - Bad: "A person walking"
   - Good: "A woman in a red coat walking through autumn leaves in Central Park, golden hour lighting"

2. **Describe camera movement**
   - "Slow dolly forward toward the subject"
   - "Aerial drone shot circling the building"
   - "Static wide shot, subject walks left to right"

3. **Include lighting and mood**
   - "Soft morning light streaming through windows"
   - "Dramatic sunset silhouette"
   - "Cozy warm interior lighting"

4. **Specify audio when needed**
   - "Ambient city sounds, distant traffic"
   - "Person speaks naturally, explaining the concept"
   - "Quiet room, only keyboard typing sounds"

## Reference Images

Use 1-3 reference images for character/object consistency:
- Face close-up for identity
- Full body for clothing/posture
- Object details for props

**Note:** Cannot use reference images AND first-frame chaining together.

## Output Specs

- **Duration**: ~8 seconds per generation
- **Resolution**: 720p (extension) or 1080p
- **Format**: MP4 with audio
- **Aspect ratios**: 16:9, 9:16, 1:1

## Workflow Integration

### For B-roll Generation

```bash
# Generate B-roll for video editing
.claude/skills/create-veo-video/.venv/bin/python \
  .claude/skills/create-veo-video/scripts/generate_video.py \
  "Close-up of hands typing on mechanical keyboard, soft desk lamp lighting" \
  /tmp/broll_typing.mp4
```

### For Social Media

```bash
# Vertical for TikTok/Reels
.claude/skills/create-veo-video/.venv/bin/python \
  .claude/skills/create-veo-video/scripts/generate_video.py \
  "Person looking at phone with surprised expression" \
  /tmp/social.mp4 --aspect 9:16

# Then post with blotato
python3 ~/.claude/skills/blotato-publisher/scripts/post.py \
  --platform tiktok,instagram \
  --media /tmp/social.mp4
```

## Cost & Limits

- **Cost**: ~$0.05-0.10 per 8-second video
- **Rate limit**: Vertex AI quotas apply
- **Timeout**: 10 minutes max wait

## Error Handling

| Error | Solution |
|-------|----------|
| Service account not found | Check scripts/trinity-vertex-ai-account.json |
| Timeout | Retry, or use fast model |
| No videos in response | Content may violate policies, adjust prompt |
| Reference image not found | Verify file paths exist |

## When to Use Which Skill

| Use Case | Skill |
|----------|-------|
| Avatar talking head | `/create-heygen-video` |
| Cinematic B-roll | `/create-veo-video` (this) |
| AI-generated scenes | `/create-veo-video` (this) |
| Product demos | `/create-veo-video` (this) |
| Avatar on camera | `/create-heygen-video` |

## Related Skills

- `create-heygen-video` - HeyGen avatar videos
- `edit-video` - Insert B-roll into existing videos
- `insert-broll` - Simple B-roll insertion
- `blotato-publisher` - Post videos to social platforms
