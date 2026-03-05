# Veo 3 Script Migration Requirements

## Objective
Migrate Ruby's Veo 3 video generation scripts from gcloud CLI / manual JWT authentication to the `google-genai` Python SDK for cleaner code, automatic token management, and access to newer Veo 3.1 features.

---

## Current State (Ruby)

### Scripts
| Script | Auth Method | Purpose |
|--------|-------------|---------|
| `veo3_generate.sh` | gcloud CLI | Text-to-video |
| `veo3_generate_from_image.sh` | gcloud CLI | Image-to-video |
| `veo3_generate_sa.sh` | Service account JWT | Text-to-video (Docker-friendly) |

### Current Argument Signatures
```bash
# veo3_generate.sh
./veo3_generate.sh "<prompt>" [output_file.mp4] [aspect_ratio]
# Example: ./veo3_generate.sh "A mountain lake" ~/Downloads/video.mp4 16:9

# veo3_generate_from_image.sh
./veo3_generate_from_image.sh <image_file> ["prompt"] [output_file.mp4] [aspect_ratio]
# Example: ./veo3_generate_from_image.sh dashboard.png "Animate with pulsing effects" ~/Downloads/video.mp4 16:9

# veo3_generate_sa.sh
./veo3_generate_sa.sh "<prompt>" [output_file.mp4] [aspect_ratio]
```

### Current Features
| Feature | veo3_generate.sh | veo3_generate_from_image.sh | veo3_generate_sa.sh |
|---------|------------------|----------------------------|---------------------|
| Text prompt | ✅ (required) | ✅ (optional) | ✅ (required) |
| Image input | ❌ | ✅ | ❌ |
| Output path | ✅ | ✅ | ✅ |
| Aspect ratio (16:9, 9:16) | ✅ | ✅ | ✅ |
| Progress feedback | ✅ | ✅ | ✅ |
| Auto-detect image MIME | ❌ | ✅ (png, jpg, jpeg, webp) | ❌ |
| Timeout handling | ❌ (infinite loop) | ❌ (infinite loop) | ❌ (infinite loop) |
| Model selection | ❌ (hardcoded) | ❌ (hardcoded) | ❌ (hardcoded) |
| Service account auth | ❌ | ❌ | ✅ |

### Current Limitations
- gcloud scripts require `gcloud auth login` (interactive, tokens expire)
- Service account script uses manual JWT creation (complex, error-prone)
- No timeout - scripts can hang indefinitely
- Hardcoded to `veo-3.0-generate-001` - no access to Veo 3.1 features
- No support for: reference images, scene extension, negative prompts, last frame
- Poll interval is 30 seconds (SDK recommends 10-15 seconds)

---

## Target State (After Migration)

### New Script
Single Python script: `.claude/scripts/generate_video.py`

### Credentials Path
```
.claude/scripts/trinity-vertex-ai-account.json
```
Copy from your-service or Trinity platform. This file should NOT be committed to git.

### Authentication Methods (Priority Order)
1. `GOOGLE_GENAI_USE_VERTEXAI=True` with service account file
2. `GOOGLE_SERVICE_ACCOUNT_KEY_PATH` environment variable
3. `GOOGLE_SERVICE_ACCOUNT_KEY` environment variable (JSON content)
4. Default application credentials (ADC)

### Python SDK Approach
Use `google-genai` SDK which handles:
- Automatic token refresh
- Cleaner API surface
- Access to Veo 3.1 features
- Proper async polling

---

## Features to Retain (P0 - MANDATORY)

| Feature | Implementation | Notes |
|---------|---------------|-------|
| Text-to-video | `python generate_video.py "prompt" output.mp4` | Required argument |
| Image-to-video | `--image input.jpg` | Optional, auto-detects MIME |
| Output path | Positional argument | Required |
| Aspect ratio | `--aspect 16:9` or `--aspect 9:16` | Default: 16:9 |
| Progress feedback | Print status while polling | Every 10 seconds |
| Auto-detect MIME type | PNG, JPEG (.jpg, .jpeg), WebP | Error on unsupported |
| Timeout handling | 10 minute timeout | Clear error message |
| Exit codes | 0 success, 1 failure | Standard convention |

---

## New Features to Add

### P1 - High Priority
| Feature | CLI Flag | Notes |
|---------|----------|-------|
| Model selection | `--model veo-3.1-generate-preview` | Default: veo-3.0-generate-001 |
| Reference images | `--ref face.png body.png` | Character/asset consistency |
| Duration | `--duration 8` | Options: 4, 6, 8 (default: 8) |
| Resolution | `--resolution 720p` | Options: 720p, 1080p, 4k (default: 720p) |
| Negative prompt | `--negative "cartoon, low quality"` | Exclusion terms |

### P2 - Nice to Have
| Feature | CLI Flag | Notes |
|---------|----------|-------|
| Scene extension | `--extend previous.mp4` | Continue from last second |
| Last frame | `--last-frame end.jpg` | Interpolate to end state |
| Verbose mode | `--verbose` | Full API response logging |
| Dry run | `--dry-run` | Print request without sending |
| Number of videos | `--count 2` | Generate multiple (1-4) |

---

## Models to Support

| Model ID | Speed | Quality | Audio | Notes |
|----------|-------|---------|-------|-------|
| `veo-3.0-generate-001` | Normal | Good | ✅ | Current default |
| `veo-3.0-fast-generate-001` | Fast | Lower | ✅ | Quick previews |
| `veo-3.1-generate-preview` | Normal | Better | ✅ Enhanced | Improved quality, better prompts |
| `veo-3.1-fast-generate-preview` | Fast | Good | ✅ Enhanced | Fast with better audio |
| `veo-2.0-generate-001` | Normal | Good | ❌ | Stable, no audio |

**Model Aliases** (for convenience):
- `3.0` → `veo-3.0-generate-001`
- `3.0-fast` → `veo-3.0-fast-generate-001`
- `3.1` → `veo-3.1-generate-preview`
- `3.1-fast` → `veo-3.1-fast-generate-preview`
- `2.0` → `veo-2.0-generate-001`

---

## CLI Interface Design

### Basic Usage
```bash
# Text-to-video (equivalent to veo3_generate.sh)
python generate_video.py "A mountain lake at sunrise" output.mp4

# With aspect ratio
python generate_video.py "A mountain lake" output.mp4 --aspect 9:16

# Image-to-video (equivalent to veo3_generate_from_image.sh)
python generate_video.py "Animate this scene" output.mp4 --image input.jpg

# Image-to-video without prompt
python generate_video.py "" output.mp4 --image input.jpg
```

### Advanced Usage
```bash
# Model selection
python generate_video.py "prompt" output.mp4 --model 3.1

# Reference images for character consistency
python generate_video.py "A woman walking" output.mp4 --ref face.png body.png

# With negative prompt
python generate_video.py "A cinematic lion" output.mp4 --negative "cartoon, drawing"

# Scene extension (continue previous video)
python generate_video.py "The butterfly lands on a flower" output.mp4 --extend prev.mp4

# First and last frame interpolation
python generate_video.py "Ghost swinging" output.mp4 --image start.jpg --last-frame end.jpg

# High resolution
python generate_video.py "Epic drone shot" output.mp4 --resolution 4k --model 3.1

# Debug mode
python generate_video.py "Test prompt" output.mp4 --verbose --dry-run
```

### Full Example
```bash
python generate_video.py "A woman making coffee in a cozy kitchen" output.mp4 \
  --image starting_frame.jpg \
  --model 3.1 \
  --aspect 16:9 \
  --duration 8 \
  --resolution 1080p \
  --ref character_ref.png kitchen_style.png \
  --negative "cartoon, anime, low quality" \
  --verbose
```

---

## Dependencies

### Python Packages
```
google-genai>=1.0.0
```

Note: `google-genai` includes `google-auth` as a dependency.

### System Requirements
- Python 3.9+
- Service account JSON file with Vertex AI permissions

### Files Required
- `trinity-vertex-ai-account.json` - Service account credentials
- Location: `.claude/scripts/trinity-vertex-ai-account.json`

---

## Configuration

### Environment Variables
```bash
# Required for Vertex AI (vs Gemini API)
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT=mcp-server-project-455215
GOOGLE_CLOUD_LOCATION=us-central1

# Service account (one of these)
GOOGLE_SERVICE_ACCOUNT_KEY_PATH=/path/to/trinity-vertex-ai-account.json
# OR
GOOGLE_SERVICE_ACCOUNT_KEY='{"type":"service_account",...}'  # JSON content
```

### Script Constants
```python
# Defaults (can be overridden by env vars)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "mcp-server-project-455215")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Generation defaults
DEFAULT_MODEL = "veo-3.0-generate-001"
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_DURATION = 8
DEFAULT_RESOLUTION = "720p"

# Polling config
TIMEOUT_SECONDS = 600      # 10 minutes
POLL_INTERVAL_SECONDS = 10 # SDK recommended

# Credentials path (relative to script)
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "trinity-vertex-ai-account.json")
```

### Model Alias Mapping
```python
MODEL_ALIASES = {
    "3.0": "veo-3.0-generate-001",
    "3.0-fast": "veo-3.0-fast-generate-001",
    "3.1": "veo-3.1-generate-preview",
    "3.1-fast": "veo-3.1-fast-generate-preview",
    "2.0": "veo-2.0-generate-001",
}
```

---

## Error Handling

### User Errors
| Error | Behavior |
|-------|----------|
| Missing prompt and image | Print usage, exit 1 |
| Output path is directory | Suggest filename, exit 1 |
| Image file not found | Print path, exit 1 |
| Unsupported image format | List supported formats (PNG, JPEG, WebP), exit 1 |
| Invalid model name | List valid models, exit 1 |
| Invalid aspect ratio | List valid options (16:9, 9:16), exit 1 |
| Invalid duration | List valid options (4, 6, 8), exit 1 |
| Invalid resolution | List valid options (720p, 1080p, 4k), exit 1 |

### System Errors
| Error | Behavior |
|-------|----------|
| Missing credentials file | Print expected path, exit 1 |
| Missing google-genai package | Print `pip install google-genai`, exit 1 |
| Invalid credentials | Print auth error, suggest re-download, exit 1 |
| Network timeout | Print elapsed time, suggest retry, exit 1 |
| Generation timeout (10 min) | Print elapsed time, save prompt to .txt for retry, exit 1 |

### API Errors
| Error | Behavior |
|-------|----------|
| RAI filter / content policy | Print filter reason, save prompt to .txt, exit 1 |
| Quota exceeded | Print quota info, suggest waiting, exit 1 |
| No video in response | Print full response (if --verbose), exit 1 |
| Operation failed | Print error details, exit 1 |

### Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Authentication error |
| 4 | Timeout |
| 5 | Content policy violation |

---

## Backward Compatibility

### Wrapper Scripts
Keep thin bash wrappers for existing callers. These match the EXACT current argument order.

**veo3_generate.sh** (wrapper):
```bash
#!/bin/bash
# Wrapper for backward compatibility
# Usage: ./veo3_generate.sh "<prompt>" [output_file.mp4] [aspect_ratio]
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPT="$1"
OUTPUT="${2:-$HOME/Downloads/veo3_$(date +%Y%m%d_%H%M%S).mp4}"
ASPECT="${3:-16:9}"

python3 "$SCRIPT_DIR/generate_video.py" "$PROMPT" "$OUTPUT" --aspect "$ASPECT"
```

**veo3_generate_from_image.sh** (wrapper):
```bash
#!/bin/bash
# Wrapper for backward compatibility
# Usage: ./veo3_generate_from_image.sh <image_file> ["prompt"] [output_file.mp4] [aspect_ratio]
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE="$1"
PROMPT="${2:-}"
OUTPUT="${3:-$HOME/Downloads/veo3_$(date +%Y%m%d_%H%M%S).mp4}"
ASPECT="${4:-16:9}"

python3 "$SCRIPT_DIR/generate_video.py" "$PROMPT" "$OUTPUT" --image "$IMAGE" --aspect "$ASPECT"
```

### Deprecation Plan
1. **Phase 1**: Create `generate_video.py`, update wrappers to use it
2. **Phase 2**: Add deprecation warning to wrapper scripts (print to stderr)
3. **Phase 3**: Update all callers in CLAUDE.md and skills to use Python script directly
4. **Phase 4**: Archive old scripts to `.claude/scripts/archive/veo3_legacy/`

---

## Testing Checklist

### Positive Cases
- [ ] Text-to-video generates successfully
- [ ] Image-to-video with prompt generates successfully
- [ ] Image-to-video without prompt generates successfully
- [ ] Aspect ratio 16:9 works
- [ ] Aspect ratio 9:16 works
- [ ] PNG input works
- [ ] JPEG (.jpg) input works
- [ ] JPEG (.jpeg) input works
- [ ] WebP input works
- [ ] Model 3.0 works
- [ ] Model 3.1 works
- [ ] Model alias "3.1" resolves correctly
- [ ] Duration 4s works
- [ ] Duration 6s works
- [ ] Duration 8s works
- [ ] Resolution 720p works
- [ ] Resolution 1080p works
- [ ] Reference images work (Veo 3.1)
- [ ] Negative prompt works
- [ ] Scene extension works
- [ ] Last frame interpolation works
- [ ] Verbose mode shows full output
- [ ] Dry run prints request without calling API
- [ ] Wrapper scripts maintain backward compatibility

### Negative Cases
- [ ] Missing prompt AND image shows error
- [ ] Invalid image format shows supported formats
- [ ] Missing image file shows path
- [ ] Invalid model name lists valid options
- [ ] Invalid aspect ratio lists valid options
- [ ] Invalid duration lists valid options
- [ ] Invalid resolution lists valid options
- [ ] Missing credentials shows expected path
- [ ] Timeout triggers after 10 minutes with clear message
- [ ] Network error is caught and reported
- [ ] RAI filter rejection is reported clearly

### Integration
- [ ] Works in Docker (service account only)
- [ ] Works locally with ADC
- [ ] Works with GOOGLE_SERVICE_ACCOUNT_KEY_PATH
- [ ] Works with GOOGLE_SERVICE_ACCOUNT_KEY (inline JSON)

---

## Implementation Order

### Phase 1: Core (P0)
1. Copy service account file from your-service
2. Create `generate_video.py` with:
   - Argument parsing (argparse)
   - Service account authentication
   - Text-to-video generation
   - Polling with timeout
   - Progress feedback
   - Exit codes
3. Test text-to-video
4. Add image-to-video support
5. Add MIME type detection
6. Update wrapper scripts
7. Test backward compatibility

### Phase 2: Enhanced (P1)
8. Add model selection with aliases
9. Add reference images support
10. Add duration option
11. Add resolution option
12. Add negative prompt support
13. Test all P1 features

### Phase 3: Advanced (P2)
14. Add scene extension
15. Add last frame interpolation
16. Add verbose mode
17. Add dry run mode
18. Add multi-video generation

### Phase 4: Documentation
19. Update CLAUDE.md sections:
    - "Veo 3 (Non-Avatar)" under Video Production
    - Add new CLI examples
    - Update auth requirements
20. Update any skills that reference veo3 scripts
21. Archive legacy scripts
22. Add inline help (`--help`)

---

## SDK Code Reference

### Basic Generation (from official docs)
```python
import time
from google import genai
from google.genai import types

client = genai.Client()

operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    prompt="Your prompt here",
    config=types.GenerateVideosConfig(
        aspect_ratio="16:9",
        resolution="720p",
        duration_seconds="8",
    ),
)

while not operation.done:
    print("Waiting...")
    time.sleep(10)
    operation = client.operations.get(operation)

video = operation.response.generated_videos[0]
client.files.download(file=video.video)
video.video.save("output.mp4")
```

### With Reference Images
```python
dress_ref = types.VideoGenerationReferenceImage(
    image=dress_image,
    reference_type="asset"
)

operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    prompt=prompt,
    config=types.GenerateVideosConfig(
        reference_images=[dress_ref, character_ref],
    ),
)
```

### Scene Extension
```python
operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    video=previous_video,  # Video object from previous generation
    prompt="Continue the scene...",
)
```

---

## Pricing Reference

| Model | Cost per Second |
|-------|-----------------|
| Veo 3.0 | $0.75 |
| Veo 3.0 Fast | Lower (TBD) |
| Veo 3.1 | $0.75 |
| Veo 3.1 Fast | Lower (TBD) |

**Note**: Generated videos are stored on Google servers for 2 days, then deleted.

---

## Sources

- [Veo on Vertex AI API Reference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/veo-video-generation)
- [Generate videos with Veo 3.1 in Gemini API](https://ai.google.dev/gemini-api/docs/video)
- [Veo 3.1 Announcement - Google Developers Blog](https://developers.googleblog.com/introducing-veo-3-1-and-new-creative-capabilities-in-the-gemini-api/)
- [Veo 3 Now Available in Gemini API](https://developers.googleblog.com/en/veo-3-now-available-gemini-api/)
