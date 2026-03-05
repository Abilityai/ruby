---
name: create-heygen-video
description: Generate HeyGen avatar video, convert to vertical, and post
automation: gated
allowed-tools: Bash, Read, Write
depends-on: knowledge-base-query, heygen-script-writer
---

# Create HeyGen Video

End-to-end video creation: Generate HeyGen avatar video -> Convert to vertical -> Add intro -> Upload -> Post to platforms.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Script (if topic) | Knowledge base agent | ✓ | | Generated script from topic |
| HeyGen Video | HeyGen API | | ✓ | Generated avatar video |
| Cloudinary | Cloudinary API | | ✓ | Uploaded video URL |
| Creatomate | Creatomate API | | ✓ | Converted vertical video |
| Intro Templates | Google Drive `Intro_Templates/` | ✓ | | Branded intro clips |
| ContentHub | `ContentHub/Published/` | | ✓ | Archived metadata |

## Quick Start

```bash
# Generate HeyGen video
mcp__heygen__generate_avatar_video
  avatar_id: "${HEYGEN_AVATAR_ID}"
  voice_id: "${HEYGEN_VOICE_ID}"
  script: "Your 30-second script here"

# Add intro and convert
.claude/scripts/prepend_intro.sh input.mp4 output.mp4 grow_blur
```

## Usage

```
/create-heygen-video <script or topic> <platforms> [intro=template]
```

**Parameters:**
- **script or topic**: Full script OR topic for the knowledge base agent to create
- **platforms**: instagram, tiktok, youtube, linkedin
- **intro**: Template name or "none" (default: grow_blur)

**Examples:**
```
/create-heygen-video "Script: AI agents are transforming..." instagram,tiktok
/create-heygen-video "Create video about AI adoption barriers" instagram intro=smoke_waves
/create-heygen-video "Deep Agents aren't just automation" tiktok intro=none
```

## Workflow

### 1. Script Generation (if needed)

If topic provided (not full script):
```bash
cd ${KNOWLEDGE_BASE_AGENT_PATH} && \
claude -p "Create a 30-second HeyGen video script about [TOPIC]. Structure: Hook (5s) -> Insight (20s) -> CTA (5s)." \
--output-format json
```

### 2. HeyGen Video Generation

```bash
mcp__heygen__generate_avatar_video
  avatar_id: "${HEYGEN_AVATAR_ID}"
  voice_id: "${HEYGEN_VOICE_ID}"
  script: "<script_text>"
```

Poll for completion (~30-60 seconds):
```bash
mcp__heygen__get_avatar_video_status video_id: "<id>"
```

### 3. Download HeyGen Video

Download from HeyGen URL to local temp.

### 4. Upload to Cloudinary

```bash
mcp__cloudinary-asset-mgmt__upload-asset
  source: "/tmp/heygen_video.mp4"
  resourceType: "video"
```

### 5. Convert Video (Creatomate)

**For Vertical Platforms:**
```bash
curl -X POST 'https://api.creatomate.com/v1/renders' \
  -H 'Authorization: Bearer $CREATOMATE_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "template_id": "vertical-crop-template",
    "modifications": {
      "Video": "<cloudinary_url>"
    }
  }'
```

Adds:
- Crop to 1080x1920 vertical
- Yellow karaoke captions

Poll until `status: "succeeded"`.

### 5.5. Prepend Branded Intro

```bash
.claude/scripts/prepend_intro.sh input.mp4 output.mp4 [template_name]
```

**Templates:**
| Template | Duration | Style |
|----------|----------|-------|
| `grow_blur` | 2s | Growing circles with blur (DEFAULT) |
| `radiate_blur` | 2s | Radiating light with blur |
| `smoke_waves` | 2s | Horizontal smoke waves |
| `curves` | 2s | Flowing gradient curves |
| `silk` | 2s | Abstract silk shapes |
| `grow` | 3s | Expanding blobs (sharper) |
| `radiate` | 3s | Radiating light (sharper) |

Use `intro=none` to skip.

### 6. Upload Final Video

Upload converted video to Cloudinary for permanent URL.

### 7. Post to Platforms

Use blotato-publisher:
```bash
python3 ~/.claude/skills/blotato-publisher/scripts/post.py \
  --platform instagram,tiktok \
  --text "Caption" \
  --media "<cloudinary_url>"
```

### 8. Archive & Confirm

Save metadata to ContentHub/Published/. Report all URLs to user.

## Avatar & Voice Configuration

### Primary Avatar (RECOMMENDED)
- **ID**: `${HEYGEN_AVATAR_ID}`
- **Description**: Sitting in striped shirt, coworking space
- **Quality**: 8/10 BEST
- **MANDATORY Voice**: `${HEYGEN_VOICE_ID}`

### Alternative Avatars
| ID | Description | Quality |
|----|-------------|---------|
| `a2d4d1f5a4064ba099370dbc91fb80e1` | Black shorts | 6/10 |
| `219661545ed74aa5be9036c310cebb07` | Table, studio | 6/10 |
| `739854ac2b5748e09f41e2719e83ec3f` | Black shirt, podcast | 6/10 |

### Voice Options
| ID | Style |
|----|-------|
| `${HEYGEN_VOICE_ID}` | Casual, conversational (DEFAULT) |
| `0f15fbc688e54d91936a4ed9b8085c73` | Professional, authoritative |

## Script Guidelines (30 Seconds Max)

### Structure
1. **Hook (5s)**: Attention-grabbing question/statement
2. **Insight (20s)**: the creator's unique perspective
3. **CTA (5s)**: Call to action

### Example Script
```
Hook: "Why do smart companies resist AI agents?"

Insight: "It's not technical - it's psychological. Admitting AI is better at parts of your job threatens your professional identity. That threat triggers dopamine-reinforced resistance."

CTA: "Understanding this psychology is the first step to adoption."
```

## Platform Notes

| Platform | Format | Notes |
|----------|--------|-------|
| Instagram | 1080x1920 | Reels, max 60s |
| TikTok | Vertical | First 3s critical |
| YouTube Shorts | 1080x1920 | Max 60s |
| LinkedIn | Both | Vertical = higher engagement |

## Cost Tracking

| Component | Cost |
|-----------|------|
| the knowledge base agent (if script gen) | ~$0.30-0.40 |
| HeyGen generation | ~$0.10 |
| Creatomate conversion | ~$0.05 |
| **Total** | ~$0.45-0.55 |

## Error Handling

| Error | Solution |
|-------|----------|
| HeyGen fails | Retry once, then suggest text post |
| Creatomate fails | Try blur-pad mode, then no captions |
| Upload fails | Retry, check file size |
| Posting fails | Save video, suggest manual posting |

## Completion Checklist

- [ ] Script ready (provided or generated via knowledge base)
- [ ] Script within 30-second limit
- [ ] [APPROVAL GATE] Script approved by user
- [ ] HeyGen video generated successfully
- [ ] Video downloaded from HeyGen
- [ ] Video uploaded to Cloudinary
- [ ] Video converted to vertical via Creatomate (if vertical platforms)
- [ ] Branded intro prepended (unless intro=none)
- [ ] Final video uploaded to Cloudinary
- [ ] Posted to target platforms via Blotato
- [ ] All URLs reported to user

## Related Skills

- `create-veo-video` - AI-generated cinematic videos (Veo 3.1)
- `heygen-script-writer` - Script generation
- `knowledge-base-query` - Knowledge base
- `blotato-publisher` - Multi-platform posting
