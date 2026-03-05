---
name: edit-video
description: Semantic video editor with human-in-loop B-roll planning. Transcribes, analyzes content, proposes B-roll plan for approval, then generates and inserts. Uses Veo 3.1 with diorama style by default + AI-generated background music.
automation: gated
allowed-tools: Bash, Read, Write, Glob, Grep
calls:
  - analyze-video
  - create-veo-video
  - nano-banana-image-generator
---

# /edit-video

Semantic video editor with agent-driven B-roll planning and human approval.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Source Video | User-provided path | ✓ | | Input video file |
| Transcript | `/tmp/transcript.json` | | ✓ | Whisper transcription |
| Diorama Style | `.claude/skills/broll-diorama-style/SKILL.md` | ✓ | | B-roll prompt guide |
| Text Style | `.claude/skills/text-overlay-style/SKILL.md` | ✓ | | Text overlay guide |
| Music Library | `assets/music/catalog.json` | ✓ | ✓ | Track library |
| Intro Templates | Google Drive `Intro_Templates/` | ✓ | | Video bookends |
| EDL | `/tmp/edl.json` | | ✓ | Edit decision list |
| Output Video | User-specified or `*_edited.mp4` | | ✓ | Final rendered video |

**B-Roll Generation**: Uses Google Veo 3.1 with **diorama style by default** (miniature handcrafted worlds). AI background music is **enabled by default** via Suno API.

## Configuration Defaults

All parameters have sensible defaults but can be overridden when calling the skill.

### B-Roll Source Settings (Veo + Diorama Style)
| Parameter | Default | Options | Description |
|-----------|---------|---------|-------------|
| `broll_source` | `veo` | `veo`, `image` | **Veo** = video B-roll (primary), **image** = static Nano Banana |
| `broll_style` | `diorama` | see below | Veo visual style (only for `veo` source) |
| `broll_fast` | false | true/false | Use faster Veo model (lower quality, 1-2 min vs 2-5 min) |

**Veo B-Roll Styles:**
| Style | Description | Best For |
|-------|-------------|----------|
| `diorama` | Miniature handcrafted worlds in shoeboxes | **DEFAULT** - educational explainers, computer architecture, processes |
| `cinematic` | Dark, dramatic, documentary-style | General tech content, interviews |
| `abstract` | Flowing particles, neural networks, data viz | AI concepts, abstract ideas |
| `tech` | Clean technology, modern gadgets, screens | Software, product content |
| `minimal` | Single subject, lots of negative space | Simple concepts, quotes |

**MANDATORY for Diorama Style**: Read the full style guide at `.claude/skills/broll-diorama-style/SKILL.md` before writing prompts. Key elements: shoebox containers, craft materials, wire-and-bead workers, **red game-piece foreman (easter egg in every B-roll)**, warm lighting, tilt-shift effect.

### B-Roll Count Settings
| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `min_broll` | 2 | 0-20 | Minimum B-roll insertions |
| `max_broll` | 8 | 1-20 | Maximum B-roll insertions |
| `broll_duration` | 8.0s | 3.0-8.0s | Default duration per B-roll (full Veo output) |
| `min_spacing` | 20s | 10-60s | Minimum seconds between B-rolls |
| `target_spacing` | 60s | 30-120s | Target spacing between B-rolls |

### Animation Settings
| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `zoom_buildup` | 4.0s | 0-6.0s | Zoom duration before B-roll (0 = disabled) |
| `zoom_amount` | 1.06 | 1.0-1.15 | Zoom scale (1.06 = 6% zoom) |
| `default_effect` | `ken_burns_in` | see list | Internal B-roll animation |
| `default_overlay` | `none` | see list | How B-roll enters frame |

### Audio Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| `use_sfx` | true | Enable transition sound effects |
| `sfx_name` | `whoosh_fast_transition` | Default SFX |
| `sfx_volume` | 0.15 | SFX volume (0.0-1.0) |
| `sfx_offset` | -0.15s | Start SFX before visual |
| `use_music` | false | Add background music (file path or asset name) |
| `music_volume` | 0.08 | Background music volume |
| `music_fade_in` | 3.0s | Music fade-in duration |
| `music_fade_out` | 3.0s | Music fade-out duration |

### AI Music Generation Settings (ENABLED BY DEFAULT)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `music_generate` | **true** | Generate AI background music using Suno API |
| `music_style` | auto | Music style (e.g., "Ambient, Electronic, Cinematic") |
| `music_mood` | auto | Music mood (e.g., "inspiring", "thoughtful", "professional") |
| `music_model` | `V5` | Suno model: V3_5, V4, V4_5, V4_5PLUS, V4_5ALL, **V5** (best) |

**AI Music Generation** uses the kie.ai Suno API to create custom instrumental background music based on video content analysis. The agent analyzes the transcript to determine appropriate mood, style, and energy for the music. **Enabled by default** - use `--no-music` to disable.

**Requirements**: Set `KIE_API_KEY` environment variable (get key at https://kie.ai/api-key)

### Music Library (IMPORTANT - Check Before Generating)

**Before generating new music**, check the existing library at `assets/music/catalog.json`.

**Workflow:**
1. Read `assets/music/catalog.json` to see available tracks
2. Match content type to track's `best_for` tags
3. Match desired mood to track's `mood` tags
4. If a track fits, use `background_music` field with the filename
5. Only generate new music if no existing track matches

**Available Tracks:**
| Track | Style | Best For |
|-------|-------|----------|
| `ambient_inspiring_corporate_01.mp3` | Ambient, Corporate, Inspiring | Job posts, Professional content, Interviews, Explainers |
| `GottaFeel.mp3` | Electronic, Upbeat | Montages, Product launches |

**Using existing music in EDL:**
```json
{
  "music_generate": false,
  "background_music": "assets/music/ambient_inspiring_corporate_01.mp3"
}
```

**When to generate new music:**
- No existing track matches the content mood/style
- User explicitly requests a different style
- Content has unique requirements (specific genre, tempo, cultural context)

**Saving new tracks:**
When generating new music that works well:
1. Copy to `assets/music/` with descriptive name: `{style}_{mood}_{number}.mp3`
2. Add entry to `catalog.json` with full metadata (style, mood, best_for, avoid_for, notes)
3. This builds the library for future use

### Color Correction Settings
| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `color_correction` | disabled | - | Enable global color correction |
| `warmth` | 0.0 | -0.1 to 0.1 | Warm/cool adjustment (positive = warmer) |
| `brightness` | 1.0 | 0.9 to 1.1 | Brightness multiplier |

**Recommended warmth values:**
- `0.03` - Subtle warmth (recommended for most videos)
- `0.05` - Moderate warmth
- `0.08` - Strong warmth (too intense for most cases)
- `-0.03` - Subtle cool tint

### Structure Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| `use_intro` | true | Prepend short branded intro |
| `intro_template` | `grow_blur_short` | Short intro (~2s) from Google Drive |
| `use_outro` | true | Append branded outro |
| `outro_template` | `curves_v2` | Default outro (~8s) from Google Drive |

**Intro/Outro Assets** (from Google Drive `Intro_Templates/`):
- **Short intros (~2s)**: `grow_blur_short` (DEFAULT), `smoke_waves_short`, `curves_short`, `radiate`, `radiate_blur`, `grow`
- **Long intros (~8s)**: `grow_blur`, `smoke_waves`, `curves`, `silk`
- **Outros (~8s)**: `converging_circles`, `converging_v2`, `curves_receding`, `curves_v2` (DEFAULT), `pulse_fade`

### Override Examples

```
# Default: Veo diorama B-roll + AI music
/edit-video video.mp4

# Use cinematic style instead of diorama
/edit-video video.mp4 --broll-style cinematic

# Use abstract Veo style for AI-heavy content
/edit-video video.mp4 --broll-style abstract

# Use static image B-roll (diagrams/frameworks)
/edit-video video.mp4 --broll-source image

# Faster Veo generation (lower quality)
/edit-video video.mp4 --broll-fast

# Disable AI music generation
/edit-video video.mp4 --no-music

# Custom music style/mood
/edit-video video.mp4 --music-style "Ambient, Electronic"
/edit-video video.mp4 --music-mood inspiring

# Standard options still work
/edit-video video.mp4 --no-intro --no-outro --max-broll 4
/edit-video video.mp4 --intro grow_blur --outro converging_circles

# Color correction (subtle warmth recommended)
/edit-video video.mp4 --warm  # Apply subtle warmth (0.03)
/edit-video video.mp4 --warmth 0.05  # Custom warmth value
```

When user provides overrides, parse them and apply to the EDL generation.

## Workflow Overview

```
User: /edit-video video.mp4 "Add B-roll for key concepts"

1. Transcribe video
2. Agent analyzes transcript + reads guidelines
3. Agent proposes B-roll plan (table with timestamps, context, visual prompts)
4. User reviews and approves/modifies
5. Agent generates B-roll images and assembles video
```

## Step 1: Transcribe Video

```bash
source .claude/skills/edit-video/venv/bin/activate
python3 .claude/skills/edit-video/scripts/transcribe_video.py "$VIDEO_PATH" -m base -o /tmp/transcript.json
```

Read the transcript output and the full text.

## Step 2: Analyze and Plan B-Roll

**First, parse any user overrides** from the command (e.g., `--max-broll 4`, `--no-intro`).
Apply these to the default configuration above.

Read these reference files:
- **`.claude/skills/broll-diorama-style/SKILL.md`** - **MANDATORY** for diorama prompts (default style)
- `.claude/skills/edit-video/broll_placement_guide.md` - When/what to insert
- `.claude/resources/nano_banana_best_practices.md` - For static image prompts (only if using `--broll-source image`)

### B-Roll Planning Criteria

**High-Priority Moments** (from broll_placement_guide.md):
- Definitions of abstract terms
- Lists/Frameworks (multi-part concepts)
- Comparisons (before/after, vs)
- Key thesis statements
- Counter-intuitive claims

**Skip B-Roll When**:
- Speaker is showing screen/demo
- Personal stories or emotional moments
- Quick asides or parenthetical comments

### Propose B-Roll Plan

Present a table to the user:

```
Here's my B-roll plan for review:

| # | Time | Context | Visual Prompt |
|---|------|---------|---------------|
| 1 | 0:26 | "AI tools reduce critical thinking" | Schematic diagram on black background: brain icon with neural pathways, some nodes fading from cyan to gray, suggesting cognitive decline. Clean geometric style, white/cyan on black. |
| 2 | 1:08 | "four pillars of agent memory" | Framework diagram: 4 hexagonal nodes arranged in a square, connected by thin cyan lines to a central circle. Each hexagon contains a simple icon. Black background, minimal, high contrast. |
| 3 | 2:15 | "unlike a calculator, an AGI has opinions" | Split comparison: LEFT - simple calculator icon in gray. RIGHT - glowing brain with thought bubbles in cyan. Visual weight favors right side. Black background. |

**Duration**: 3s each | **SFX**: whoosh_fast_transition | **Spacing**: 49s, 67s apart

Approve these, or suggest changes?
```

### Visual Prompt Requirements (MANDATORY)

**Separation of Concerns:**
- **Agent**: Writes complete, validated prompts with all style requirements
- **Script**: Executes prompts exactly as provided - NO wrapping, NO modification

---

#### Veo B-Roll Prompts (PRIMARY)

For cinematic video B-roll, write prompts describing motion and atmosphere:

```
[Visual description - what to show]

CINEMATOGRAPHY:
- Camera movement (slow dolly, orbit, static with motion in frame)
- Depth of field and focus
- Lighting style (dramatic rim light, volumetric rays, soft ambient)

ATMOSPHERE:
- Dark/black background environment
- Color accents: Electric cyan (#00ffff), white highlights
- Professional documentary aesthetic

NO text, NO UI elements, NO faces. 8 seconds of seamless motion.
```

**Veo Prompt Examples by Style:**

**Diorama (DEFAULT) - MUST read `.claude/skills/broll-diorama-style/SKILL.md`:**
```
Miniature diorama of a content pipeline in a wooden cigar box.

SCENE LAYOUT:
- Left: raw footage arrives as tiny film reels on a ribbon conveyor
- Center: editing station where wire-and-bead workers splice reels
- Right: finished videos roll into shipping crates

CRAFT MATERIALS:
- Cardboard walls with visible hot glue seams
- Toothpick support beams, ribbon conveyors
- Thimble smokestacks on mini editing machines

CHARACTERS:
- 3 wire-and-bead workers operating machines
- Red game-piece foreman supervising from elevated platform

LIGHTING:
- Warm desk lamp from above-left
- Fairy lights along conveyor belt

CAMERA:
- Slow pan left-to-right following the workflow
- Tilt-shift shallow depth of field
- 8 seconds

MOOD: Handcrafted, busy, whimsical
```

**Cinematic:**
```
Close-up of hands typing on a mechanical keyboard, soft desk lamp creating rim light.
Slow push-in camera movement. Shallow depth of field with bokeh in background.
Dark environment, keys illuminated by cyan LED underglow.
Subtle ambient sound of keystrokes. Professional, focused atmosphere.
```

**Abstract:**
```
Neural network visualization - glowing nodes connected by pulsing cyan pathways.
Particles flowing through the network like data. Camera slowly orbiting the structure.
Pure black void with bioluminescent glow on connections.
Hypnotic, meditative movement. Silent or soft ambient tone.
```

**Tech:**
```
Modern laptop screen displaying abstract code patterns (not readable text).
Slow dolly past the device, reflections on glass surface.
Clean desk environment, minimal, dark with selective lighting.
Professional, corporate aesthetic. Quiet room ambiance.
```

---

#### Nano Banana Prompts (for `--broll-source image`)

For static diagram/framework B-roll, read these guides first:
- `/tmp/Brand_Broll_Style_Prompt.md` (download from Google Drive ID: YOUR_BROLL_STYLE_ID)
- `.claude/resources/nano_banana_best_practices.md`

```
Create a [DIAGRAM TYPE] for a tech video B-roll.

CONCEPT: [One sentence describing what to visualize]

VISUAL STRUCTURE:
- [Layout description - e.g., "central element with 4 surrounding nodes"]
- [Max 5-7 specific visual elements to include]
- [Relationship/connection description if applicable]

STYLE REQUIREMENTS (the creator's brand - MANDATORY):
- Background: Pure black (#000000) - NO gradients, NO dark blue
- Primary elements: White (#ffffff) and cyan (#00ffff)
- Success indicators: Green (#22c55e) for checkmarks
- Error indicators: Red (#ef4444) for X marks
- Borders: Dark gray (#333333) - subtle, not prominent
- Composition: Clean, minimal, maximum 10 elements, plenty of negative space
- NO TEXT whatsoever - purely visual icons and shapes
- 16:9 aspect ratio
- High contrast, mobile-optimized
```

**Nano Banana Limits (CRITICAL):**
- Maximum 10 visual boxes/shapes
- Maximum 10 text pieces (prefer ZERO for B-roll)
- Maximum 3 hierarchy levels
- Focus on ONE key concept per diagram
- Use visual metaphors that explain at a glance

---

#### When to Use Which Source

| Content Type | Recommended Source | Why |
|--------------|-------------------|-----|
| Abstract AI concepts | `veo` + `abstract` | Motion adds life to abstract ideas |
| Technology in action | `veo` + `cinematic` | Real motion is more engaging |
| Frameworks/hierarchies | `image` | Static diagrams are clearer |
| Comparisons (A vs B) | `image` | Side-by-side requires static layout |
| Process flows | Either | Veo for dynamic, image for precise |
| Emotional/dramatic moments | `veo` + `cinematic` | Cinematic footage builds tension |

## Step 3: Handle User Feedback

If user says:
- "Approved" / "LGTM" / "Go" → Proceed to generation
- Provides corrections → Update the plan and re-present
- "Skip #2" → Remove that entry
- "Change #3 to..." → Update that specific prompt

## Step 4: Generate B-Roll and Execute

Once approved, create the EDL file and execute:

```bash
# Create EDL with approved prompts
cat > /tmp/edl.json << 'EOF'
{
  "version": "1.0",
  "source_video": "/path/to/video.mp4",
  "default_transition_sfx": "whoosh_fast_transition",
  "default_sfx_volume": 0.15,
  "edits": [
    {
      "type": "insert_broll",
      "at": "00:26.280",
      "duration": 3.0,
      "visual_prompt": "Schematic diagram on black background...",
      "context": "AI tools reduce critical thinking",
      "sfx_offset": -0.15
    }
  ],
  "output": {
    "path": "/path/to/video_edited.mp4"
  }
}
EOF

# Execute with MoviePy
python3 .claude/skills/edit-video/scripts/execute_moviepy.py /tmp/edl.json
```

The execute script will:
1. Generate each B-roll image using the `visual_prompt`
2. Convert to video with Ken Burns effect
3. Insert at specified timestamps with SFX
4. Render final video

## EDL Format

The EDL (Edit Decision List) captures all configurable parameters. Fields with defaults shown:

```json
{
  "version": "1.0",
  "source_video": "/path/to/video.mp4",

  // B-ROLL SOURCE (Veo + Diorama default)
  "broll_source": "veo",          // "veo" (default) or "image" (Nano Banana)
  "broll_style": "diorama",       // Veo style: diorama (default), cinematic, abstract, tech, minimal
  "broll_fast": false,            // Use faster Veo model (lower quality)

  // Global SFX settings (overridable per-edit)
  "default_transition_sfx": "whoosh_fast_transition",
  "default_sfx_volume": 0.15,

  // Intro/outro
  "intro": "grow_blur_short",     // short intro (~2s), null to skip
  "outro": "curves_v2",           // outro (~8s), null to skip

  // Background music (file-based)
  "background_music": null,       // path or asset name
  "music_volume": 0.08,
  "music_fade_in": 3.0,
  "music_fade_out": 3.0,

  // AI Music Generation (ENABLED BY DEFAULT)
  "music_generate": true,         // generate AI music via Suno API (default: true)
  "music_style": null,            // e.g., "Ambient, Electronic, Cinematic"
  "music_mood": null,             // e.g., "inspiring", "thoughtful", "professional"
  "music_model": "V5",            // Suno model: V3_5, V4, V4_5, V4_5PLUS, V4_5ALL, V5
  "music_transcript": "",         // transcript for music analysis (auto-populated)

  // Color correction (applied to entire video)
  "color_correction": {
    "warmth": 0.03,               // -0.1 to 0.1, positive = warmer (0.03 recommended)
    "brightness": 1.0             // 0.9 to 1.1, multiplier
  },

  // Zoom buildup (applied to talking head before each B-roll)
  "zoom_buildup": 4.0,            // seconds, 0 to disable
  "zoom_amount": 1.06,            // 1.06 = 6% zoom
  "zoom_overlap": 0,              // seconds to continue zoom into B-roll

  "edits": [
    {
      "type": "insert_broll",
      "at": "00:26.280",
      "duration": 4.0,                    // 2.5-6.0s
      "visual_prompt": "Agent-written prompt for Veo or Nano Banana",
      "context": "What the speaker is saying",

      // Per-edit source override (optional)
      "broll_source": "veo",              // override global source for this edit
      "broll_style": "abstract",          // override style for this edit

      // Animation (only for image source)
      "effect": "ken_burns_in",           // internal B-roll animation
      "overlay_effect": "slide_left",     // how it enters frame

      // SFX (per-edit overrides)
      "transition_sfx": "tech_slide",     // null to skip SFX for this edit
      "sfx_volume": 0.10,
      "sfx_offset": -0.15,

      // Zoom (per-edit overrides)
      "zoom_buildup": 4.0,                // 0 to disable for this edit
      "zoom_amount": 1.08
    }
  ],
  "output": {
    "path": "/path/to/output.mp4"
  }
}
```

**Key field**: `visual_prompt` - This is written by the agent based on context, NOT auto-generated from keywords.

### Animation Effects
Two types of effects for variety:

**Internal Effects** (`effect`) - Built into the B-roll video via FFmpeg:
| Effect | Description |
|--------|-------------|
| `ken_burns_in` | Slow zoom in (default) |
| `ken_burns_out` | Zoom out, reveals full image |
| `ken_burns_pan` | Zoom + pan right |
| `pan_left` / `pan_right` | Horizontal pan |
| `pulse` | Subtle breathing zoom |
| `drift` | Diagonal movement with zoom |
| `none` | Static with fade |

**Overlay Effects** (`overlay_effect`) - How B-roll enters the frame via MoviePy:
| Effect | Description |
|--------|-------------|
| `slide_left` | Slide in from left |
| `slide_right` | Slide in from right |
| `slide_up` | Slide in from below |
| `slide_down` | Slide in from above |
| `scale_in` | Grow from center |
| `none` | No transition (default) |

**Vary both** for visual interest - don't use same combination for all B-rolls.

### Duration Guidelines
- Simple concept: 4.0s (base 3s + 1s for transition)
- Framework/complex: 5.0s
- Comparison (2-panel): 5.0-5.5s

### Music Options
- `background_music`: Path to music file (absolute or name from `assets/music/`)
- `music_volume`: 0.0-1.0, default 0.08 (subtle background)
- `music_fade_in`: Fade-in duration in seconds (starts after intro)
- `music_fade_out`: Fade-out duration in seconds (ends before outro)

**Music Timing**: Music plays only during main content - it starts after the intro ends and fades out before the outro begins. Intro and outro are treated as "bookends" without background music.

**Long Videos**: For videos longer than the generated music (Suno max is 8 min), music automatically loops with a 2-second crossfade between loops for smooth transitions.

## Execution Options

```bash
python3 .claude/skills/edit-video/scripts/execute_moviepy.py edl.json \
  -o output.mp4 \
  --intro grow_blur_short \
  --outro curves_v2 \
  --sfx whoosh_fast_transition \
  --sfx-volume 0.15
```

## Available Assets

### Intro/Outro Templates (Google Drive `Intro_Templates/`)

Download before use:
```bash
python3 .claude/scripts/google/google_drive.py download <ID> /tmp/intro.mp4
```

**Short Intros (~2s)** - DEFAULT for regular videos:
| Name | Google Drive ID |
|------|-----------------|
| `grow_blur_short` (DEFAULT) | `YOUR_INTRO_GROW_BLUR_SHORT_ID` |
| `smoke_waves_short` | `YOUR_INTRO_SMOKE_WAVES_SHORT_ID` |
| `curves_short` | `YOUR_INTRO_CURVES_SHORT_ID` |
| `radiate` | `YOUR_INTRO_RADIATE_ID` |
| `radiate_blur` | `YOUR_INTRO_RADIATE_BLUR_ID` |
| `grow` | `YOUR_INTRO_GROW_ID` |

**Long Intros (~8s)** - Use when explicitly requested:
| Name | Google Drive ID |
|------|-----------------|
| `grow_blur` | `YOUR_INTRO_GROW_BLUR_ID` |
| `smoke_waves` | `YOUR_INTRO_SMOKE_WAVES_ID` |
| `curves` | `YOUR_INTRO_CURVES_ID` |
| `silk` | `YOUR_INTRO_SILK_ID` |

**Outros (~8s)**:
| Name | Google Drive ID |
|------|-----------------|
| `curves_v2` (DEFAULT) | `YOUR_OUTRO_CURVES_V2_ID` |
| `converging_circles` | `YOUR_OUTRO_CONVERGING_ID` |
| `converging_v2` | `YOUR_OUTRO_CONVERGING_V2_ID` |
| `curves_receding` | `YOUR_OUTRO_CURVES_RECEDING_ID` |
| `pulse_fade` | `YOUR_OUTRO_PULSE_FADE_ID` |

### SFX (assets/sfx/)
| Name | Duration | Best For |
|------|----------|----------|
| `whoosh_fast_transition` | 1.33s | **DEFAULT** - standard B-roll |
| `swoosh_flying` | 0.57s | Quick transitions, energetic moments |
| `sweep_small_fast` | 0.85s | General variety |
| `whoosh_arrow` | 1.10s | Sharp comparisons, contrasts |
| `whoosh_air` | 2.32s | Soft, medical/scientific content |
| `whoosh_swirling` | 2.52s | Circular frameworks, processes |
| `tech_slide` | 2.26s | Tech/data/research visuals |

### SFX Variety Guidelines
**Always vary SFX across B-rolls** - using the same sound repeatedly is noticeable and monotonous.

Match SFX to content type:
| Content Type | Recommended SFX |
|--------------|-----------------|
| Data/charts/research | `tech_slide` |
| Medical/anatomical | `whoosh_air` |
| Frameworks (circular) | `whoosh_swirling` |
| Comparisons (A vs B) | `whoosh_arrow` |
| Quick/energetic | `swoosh_flying` |
| Standard/neutral | `whoosh_fast_transition` |

Specify per-edit in EDL:
```json
{
  "type": "insert_broll",
  "at": "01:30.000",
  "transition_sfx": "whoosh_swirling",
  "sfx_volume": 0.10
}
```

### SFX Settings
- `sfx_volume`: 0.10 (subtle, doesn't overpower speech)
- `sfx_offset`: -0.15 (starts 150ms before visual appears)

## Spacing Guidelines

These are defaults; override with `--min-broll`, `--max-broll`, `--min-spacing`, `--target-spacing`.

| Video Length | B-Roll Count | Spacing |
|--------------|--------------|---------|
| 2-3 min | 2-3 | ~60s apart |
| 5-7 min | 4-6 | ~60-90s apart |
| 10-15 min | 8-12 | ~60-90s apart |

**Minimum gap**: `min_spacing` (default 20s) between B-rolls

### Calculating B-Roll Count

When planning, respect the configured bounds:
```
video_minutes = duration / 60
suggested_count = round(video_minutes * 1.5)  # ~1.5 B-rolls per minute
final_count = clamp(suggested_count, min_broll, max_broll)
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `transcribe_video.py` | Whisper transcription to JSON |
| `execute_moviepy.py` | Execute EDL, generate B-roll, render video |
| `generate_broll_video.py` | Generate Veo video B-roll (PRIMARY) |
| `generate_broll_image.py` | Generate static image B-roll (fallback for diagrams) |
| `generate_music.py` | Generate AI background music via kie.ai Suno API |

## Important Notes

1. **Diorama is DEFAULT** - Use miniature diorama style B-roll by default. **MUST read `.claude/skills/broll-diorama-style/SKILL.md`** for prompt format.
2. **AI Music is DEFAULT** - Generate background music via Suno API. Use `--no-music` to disable.
3. **Agent writes prompts** - Agent creates visual prompts based on context analysis + diorama style guide.
4. **Human approval required** - Always present plan and wait for approval before generating.
5. **Only talking-head segments** - Never insert B-roll over screen sharing or demos.
6. **Diorama elements** - Every B-roll needs: shoebox container, craft materials, tiny workers, **red game-piece foreman**, warm lighting, tilt-shift.
7. **Veo takes 2-5 minutes** - Each B-roll generation is slower than images but produces motion video.

---

## Text Overlays

Add on-screen text overlays for titles, lower thirds, bullet lists, and key quotes.

### Text Overlay Configuration

| Parameter | Default | Options | Description |
|-----------|---------|---------|-------------|
| `text_overlays` | false | true/false | Enable text overlay planning |

### Override Examples

```
# Add text overlays for key points
/edit-video video.mp4 "Add text overlays"

# B-roll + text overlays together
/edit-video video.mp4 "Add B-roll and text overlays"

# Text overlays only (no B-roll)
/edit-video video.mp4 --no-broll "Add text overlays for key points"
```

### Text Overlay Planning

**MANDATORY**: Read these before planning text overlays:
- **`.claude/skills/text-overlay-style/SKILL.md`** - Technical options, all styles/animations/positions
- Download **`Prompts/Brand_Text_Overlay_Style_Profile.md`** (ID: `YOUR_FILE_ID_HERE`) - Brand preferences

```bash
python3 .claude/scripts/google/google_drive.py download YOUR_FILE_ID_HERE /tmp/text_overlay_style.md
```

### Text Overlay Plan Format

Present a table to the user:

```
Here's my text overlay plan for review:

| # | Time | Text | Style | Position | Animation |
|---|------|------|-------|----------|-----------|
| 1 | 0:02 | "NOW HIRING" | blur | top | pop |
| 2 | 0:02 | "AI Video Editor" | outline | center | slide_up |
| 3 | 0:10 | "Example Creator | Title" | lower_third | lower_third | slide_left |
| 4 | 0:25 | "KEY POINTS\n- Item 1\n- Item 2" | box | left | slide_left |

Approve these, or suggest changes?
```

### EDL Format for Text Overlays

```json
{
  "type": "insert_text",
  "at": "00:02.000",
  "duration": 5.0,
  "text": "NOW HIRING",
  "font_size": 90,
  "font_color": "#ff4444",
  "font": "/path/to/.claude/skills/edit-video/assets/fonts/DMSans-Bold.ttf",
  "position": "top",
  "style": "blur",
  "blur_amount": 20.0,
  "darken": 0.3,
  "animation": "pop",
  "stroke_width": 0,
  "text_align": "center",
  "accent_color": "#ff4444"
}
```

### Available Styles

| Style | Description | Best For |
|-------|-------------|----------|
| `blur` | Blurred/darkened background | Hero headlines, emphasis |
| `box` | Semi-transparent box | Lists, bullet points |
| `gradient` | Radial gradient | Text over busy backgrounds |
| `lower_third` | News-style bar | Speaker names, titles |
| `outline` | Text only with stroke | Minimal annotations |

### Available Animations

| Animation | Description | Best For |
|-----------|-------------|----------|
| `fade` | Smooth fade | Default, professional |
| `pop` | Scale with overshoot | Headlines, emphasis |
| `scale` | Grow/shrink | Dramatic reveals |
| `slide_up` | From below | Lists, reveals |
| `slide_left` | From left | Lower thirds, left text |
| `slide_right` | From right | Right-positioned text |
| `none` | Instant | Quick info |

### Available Positions

| Position | Location | Width |
|----------|----------|-------|
| `center` | Middle | 90% |
| `top` | Top center | 90% |
| `bottom` | Bottom center | 90% |
| `left` | Left side | 45% |
| `right` | Right side | 45% |
| `lower_third` | News position | 60% |
| `upper_third` | 20% from top | 90% |
| `bottom_left` | Lower left | 45% |
| `bottom_right` | Lower right | 45% |

### Font Assets

| Font | Path | Use For |
|------|------|---------|
| DM Sans Bold | `assets/fonts/DMSans-Bold.ttf` | Headlines, emphasis |
| DM Sans Regular | `assets/fonts/DMSans-Regular.ttf` | Body, lists |

### Brand Colors

| Element | Color | Usage |
|---------|-------|-------|
| Brand Red | `#ff4444` | Headlines, CTA |
| White | `white` | Body text |
| Cyan (legacy) | `#00ffff` | Accents (optional) |

### Text Overlay Timing Rules

- First overlay: After 2-3 seconds (not immediate)
- Minimum gap: 10 seconds between overlays
- No overlap with B-roll: 2+ seconds gap
- Duration: 4-7 seconds depending on content
- Last overlay: End 5+ seconds before video ends

### When to Use Text Overlays

**Good candidates:**
- Video intro (hero headline)
- Speaker introduction (lower third)
- Key thesis statements (centered blur)
- Lists of points (side panel box)
- Section transitions (section header)
- Call to action (hero with accent)

**Skip when:**
- Speaker showing something on screen
- Fast-paced dialogue
- Emotional/personal stories
- Already have B-roll playing
- Within 3 seconds of another overlay

---

## Reference Files

- **`.claude/skills/broll-diorama-style/SKILL.md`** - **MUST READ** for diorama prompts (default style)
- **`.claude/skills/text-overlay-style/SKILL.md`** - **MUST READ** for text overlay options
- `broll_placement_guide.md` - When/what B-roll to insert
- `moviepy_reference.md` - MoviePy API documentation
- `.claude/resources/nano_banana_best_practices.md` - Image generation prompts (for `--broll-source image`)
- Download `Prompts/Brand_Text_Overlay_Style_Profile.md` for brand preferences

## Completion Checklist

- [ ] Source video accessible and valid
- [ ] Transcript generated via Whisper
- [ ] Style guides read (diorama, text overlay)
- [ ] Music library checked for existing tracks
- [ ] B-roll plan proposed with timestamps
- [ ] [APPROVAL GATE] User approved B-roll plan
- [ ] Text overlay plan proposed (if requested)
- [ ] [APPROVAL GATE] User approved text overlays
- [ ] EDL file created with all edits
- [ ] B-roll assets generated (Veo or Nano Banana)
- [ ] AI music generated (unless --no-music or existing track used)
- [ ] Intro/outro downloaded from Google Drive
- [ ] Video rendered successfully
- [ ] Output file verified (plays, correct duration)
- [ ] New music added to catalog.json (if generated and good)

## Error Recovery

If skill fails mid-execution:

1. **Check partial outputs:**
   ```bash
   ls -la /tmp/edl.json /tmp/transcript.json
   ls -la /tmp/broll_*.mp4 2>/dev/null
   ```

2. **Common issues:**
   - Veo timeout: Retry individual B-roll generation
   - Music generation failed: Use existing track from catalog
   - Render failed: Check disk space, reduce quality

3. **Recovery:**
   - If B-roll generated but render failed: Re-run execute_moviepy.py with existing EDL
   - If transcript exists: Skip transcription, proceed to planning
   - If EDL exists: Resume from Step 4 (generate and execute)
