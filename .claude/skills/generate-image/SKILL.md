---
name: generate-image
description: Generate images using Replicate's google/imagen-4-ultra model
allowed-tools: Bash, Read, Write
---

# Generate Image

Generate high-quality images using Google's Imagen 4 Ultra model via Replicate MCP.

## Quick Start

```bash
# Generate YouTube thumbnail (uses Replicate MCP)
mcp__replicate__create_predictions
  version: "google/imagen-4-ultra"
  input: {
    "prompt": "Professional YouTube thumbnail with bold text",
    "aspect_ratio": "16:9",
    "output_format": "png"
  }
  Prefer: "wait"
  jq_filter: ".output"
```

## Usage

```
/generate-image <description> [for <project_folder_path>]
```

**With project folder:**
```
/generate-image Create 3 YouTube thumbnails for 
```
Saves to: `<project_folder>/thumbnails/`

**Without project folder:**
```
/generate-image Create an Instagram post with motivational quote
```
Saves to: `$VAULT_BASE_PATH/generated_images/`

## Workflow

### 1. Create Prediction (Generate Image)

```
mcp__replicate__create_predictions
  version: "google/imagen-4-ultra"
  input: {
    "prompt": "<user's description>",
    "aspect_ratio": "16:9",
    "output_format": "png",
    "output_quality": 90
  }
  Prefer: "wait"
  jq_filter: ".output"
```

**CRITICAL**: Always use `jq_filter: ".output"` to get only the image URL.

### 2. Save Images Locally

**Replicate URLs expire in 24 hours!** Always save locally immediately.

```bash
# Determine save directory
if [[ -n "$PROJECT_FOLDER" ]]; then
  SAVE_DIR="$PROJECT_FOLDER/thumbnails"
else
  SAVE_DIR="$VAULT_BASE_PATH/generated_images"
fi

mkdir -p "$SAVE_DIR"
cd "$SAVE_DIR"
curl -o "thumbnail_v1_description.png" "<replicate_url>"
```

## Input Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | string | Image description (be specific) |
| `aspect_ratio` | string | "16:9", "9:16", "1:1", "4:3", "3:4" |
| `output_format` | string | "png", "jpg", "webp" |
| `output_quality` | int | 0-100 (default: 80) |
| `negative_prompt` | string | Things to avoid |
| `seed` | int | For reproducibility |
| `safety_tolerance` | int | 1-6 (higher = less filtering) |

## Aspect Ratios by Platform

| Platform | Aspect Ratio | Resolution |
|----------|-------------|------------|
| YouTube Thumbnails | 16:9 | 1920x1080 |
| Instagram Posts | 1:1 | 1080x1080 |
| Instagram Stories | 9:16 | 1080x1920 |
| LinkedIn Posts | 4:3 or 16:9 | - |
| Twitter Posts | 16:9 or 1:1 | - |
| Blog Headers | 16:9 or 3:1 | - |

## Prompt Engineering Tips

**For Text in Images (Thumbnails):**
```
"Very large bold text '[TEXT]' occupying 70% of frame,
[STYLE] font, [COLOR] on [BACKGROUND]. High contrast,
readable at thumbnail size. Professional design."
```

**For Photorealistic Images:**
```
"Photorealistic [SUBJECT], professional photography,
natural lighting, 8K resolution, sharp focus,
detailed, [STYLE] aesthetic"
```

**For Illustrations:**
```
"Clean modern illustration of [SUBJECT], [COLOR PALETTE],
minimalist design, vector style, professional branding"
```

## Example: YouTube Thumbnail

```
mcp__replicate__create_predictions
  version: "google/imagen-4-ultra"
  input: {
    "prompt": "Professional YouTube thumbnail with very large bold text 'ONE TRANSCRIPT' at the top in dark gray and '50 POSTS' at the bottom in bright red. Gradient background from soft pale red to light gray. High contrast, clean modern design.",
    "aspect_ratio": "16:9",
    "output_format": "png",
    "output_quality": 95
  }
  Prefer: "wait"
  jq_filter: ".output"
```

Then save:
```bash
mkdir -p "/path/to/project/thumbnails"
curl -o "/path/to/project/thumbnails/thumbnail_v1_one_transcript.png" "<replicate_url>"
```

## Filename Convention

Format: `thumbnail_v{number}_{description}.{ext}`

Examples:
- `thumbnail_v1_gradient_coral_gray.png`
- `thumbnail_v2_tech_dark_navy.png`
- `image_v1_product_photo.jpg`

## Error Handling

| Error | Solution |
|-------|----------|
| Model not found | Search with `mcp__replicate__search` |
| Prediction failed | Check content policies, try different prompt |
| Timeout | Remove `Prefer: "wait"`, poll status |
| Invalid aspect_ratio | Use: "1:1", "16:9", "9:16", "4:3", "3:4" |

## Cost

- **Imagen 4 Ultra**: ~$0.02-0.05 per image
- Use lower `output_quality` for drafts

## Best Practices

- **Always use jq_filter: ".output"** - Reduces response size by 95%
- **Save immediately** - Replicate URLs expire in 24 hours
- **Be specific** - Include lighting, style, mood, quality
- **Use Prefer: "wait"** - Synchronous generation up to 60 seconds
- **Set output_quality: 90-95** for final production images
