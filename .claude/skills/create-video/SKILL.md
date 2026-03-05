---
name: create-video
description: Generate complete explanatory videos from scratch using AI video generation. Creates scene-by-scene content with Veo 3.1, stitches clips together with transitions, music, and intros/outros. Perfect for explainers, tutorials, concept visualizations.
automation: gated
calls:
  - create-explanatory-image
  - nano-banana-image-generator
allowed-tools: Bash, Read, Write, Glob, Grep, Task
---

# /create-video

Generate complete explanatory videos from AI-generated scenes. No source footage needed - the entire video is created from prompts.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Diorama Style | `.claude/skills/broll-diorama-style/SKILL.md` | ✓ | | B-roll prompt guide (default style) |
| Nano Banana | `.claude/resources/nano_banana_best_practices.md` | ✓ | | Image generation guide (explain/diagram scenes) |
| Series Assets | `.claude/skills/create-video/assets/` | ✓ | | Series-specific intros/outros |
| Music Library | `assets/music/catalog.json` | ✓ | ✓ | Existing tracks before generating |
| VDL | `/tmp/vdl.json` | | ✓ | Video definition list |
| Output Video | User-specified path | | ✓ | Final assembled video |

**Video Generation**: Uses Google Veo 3.1 with configurable styles (diorama, cinematic, abstract, etc.). AI background music via Suno API is **enabled by default**. ElevenLabs voiceover is **generated per-scene**.

## Series Support

### Explained AI Series
Use for educational AI explainer videos. Diorama-style intro/outro matches B-roll aesthetic.

```json
"structure": {
  "intro": "explained_ai_diorama",
  "outro": "explained_ai_diorama"
}
```

**Intro**: Victorian theater diorama with curtains parting, lights illuminating
**Outro**: Workshop diorama winding down, workers finishing, lights dimming

Assets location: `.claude/skills/create-video/assets/`

## Per-Scene Voiceover (ElevenLabs)

**IMPORTANT**: Each scene can have a `narration` field. Voiceover is generated and mixed into each scene individually BEFORE assembly. This ensures perfect sync.

**Narration Rules**:
- **Target 15-25 words per scene** (allows proper explanation with analogies)
- Use analogies to explain complex concepts: "Think of it like...", "Imagine a...", "It's similar to..."
- Each scene should explain ONE concept clearly - don't rush
- Voice: Default (ID: `${ELEVENLABS_VOICE_ID}`)
- Model: `eleven_multilingual_v2`
- Mixed at 250% volume, scene audio at 20%

Example scene with narration:
```json
{
  "id": "scene_01",
  "description": "Hook - The memory problem",
  "visual_prompt": "Miniature diorama of...",
  "narration": "Every second, billions of operations happen inside your computer. Think of it like a tiny city that never sleeps."
}
```

## Scene Types

Videos can mix two scene types for optimal explanation:

| Type | Visual | Best For |
|------|--------|----------|
| `visualize` | Veo 3.1 animated B-roll (DEFAULT) | Mood, transitions, abstract concepts |
| `explain` | Static image with Ken Burns effect | Simple labels, mood images, quick visuals |
| `diagram` | Self-critiqued explanatory image with Ken Burns | Framework diagrams, process flows, architecture |

### Explain Scenes (Static Images)

For concepts that benefit from a diagram or infographic:

```json
{
  "id": "scene_02",
  "type": "explain",
  "description": "Three-layer architecture diagram",
  "image_prompt": "Warm toned infographic showing three stacked layers labeled Orchestrator, Workers, Memory...",
  "narration": "Think of it like a three-layer cake. The orchestrator plans at the top, workers execute in the middle, and memory keeps everyone in sync.",
  "duration": 10.0
}
```

- Uses Nano Banana (Gemini 2.5 Flash) for image generation
- Applies slow Ken Burns (zoom/pan) for movement
- Ideal for: architecture diagrams, step-by-step flows, comparisons, data visualizations

### Visualize Scenes (Animated B-roll)

Default scene type using Veo 3.1:

```json
{
  "id": "scene_01",
  "type": "visualize",
  "description": "Hook - The overwhelm problem",
  "visual_prompt": "Miniature diorama of tiny office workers drowning in paper...",
  "narration": "Every day, your team processes hundreds of tasks. But what if you could deploy an entire department that never sleeps?",
  "duration": 8.0
}
```

**Best practice**: Use `diagram` for concepts that need accurate text and logical structure, `explain` for quick visual overlays, `visualize` for mood/atmosphere.

### Diagram Scenes (Self-Critiqued Explanatory Images)

For concepts where text accuracy and logical correctness matter (frameworks, architectures, processes):

```json
{
  "id": "scene_03",
  "type": "diagram",
  "description": "Four-layer agent architecture",
  "diagram_spec": {
    "concept": "Four layers of reliable agent systems",
    "layout": "framework",
    "elements": ["Trinity", "Agents", "Playbooks", "Brain"],
    "style": "warm"
  },
  "narration": "Think of it as four layers stacked on top of each other. Infrastructure at the base, agents above it, playbooks encoding the processes, and a shared brain at the top.",
  "duration": 10.0
}
```

**How `diagram` differs from `explain`:**
- Generates 3 variants using Nano Banana via `/create-explanatory-image` pattern
- Self-critiques each: checks spelling, label accuracy, element count, logical structure
- Iterates up to 3 rounds on fixable issues
- Selects the best version
- Applies Ken Burns effect (same as `explain`)

**Processing**: Diagram scenes are generated via a Task sub-agent (`subagent_type: "gemini-agent"`) that follows the `/create-explanatory-image` process:
1. Read best practices from `.claude/skills/nano-banana-image-generator/best_practices.md`
2. Simplify concept to constraints (max 10 boxes, 10 labels, 3 hierarchy levels)
3. Replace 4+ syllable words with simpler alternatives
4. Generate 3 variants, self-critique each, select best
5. Output final image to `/tmp/` for assembly

**When to use each:**

| Need | Use |
|------|-----|
| Accurate framework/architecture diagram | `diagram` |
| Quick text overlay on a nice background | `explain` |
| Animated cinematic B-roll | `visualize` |

## Configuration Defaults

### Video Style Settings (Veo)
| Parameter | Default | Options | Description |
|-----------|---------|---------|-------------|
| `style` | `diorama` | see below | Visual style for all scenes |
| `fast` | false | true/false | Use faster Veo model (lower quality, 1-2 min vs 2-5 min) |
| `aspect` | `16:9` | `16:9`, `9:16`, `1:1` | Video aspect ratio |

**Available Styles:**
| Style | Description | Best For |
|-------|-------------|----------|
| `diorama` | Miniature handcrafted worlds in shoeboxes | **DEFAULT** - educational explainers, processes, architecture |
| `cinematic` | Dark, dramatic, documentary-style | Tech content, professional feel |
| `abstract` | Flowing particles, neural networks, data viz | AI concepts, abstract ideas |
| `tech` | Clean technology, modern gadgets, screens | Software, product content |
| `minimal` | Single subject, lots of negative space | Simple concepts, quotes |

**MANDATORY for Diorama Style**: Read `.claude/skills/broll-diorama-style/SKILL.md` before writing scene prompts.

### Audio Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| `music_generate` | true | Generate AI background music |
| `music_volume` | 0.05 | Background music volume (5%) |
| `scene_video_volume` | 0.20 | Scene audio when voiceover present (20%) |
| `voiceover_volume` | 2.50 | Voiceover volume (250%) |
| `voice_id` | Default | ElevenLabs voice ID |
| `sfx_between_scenes` | `sweep_small_fast` | Subtle transition SFX |
| `sfx_volume` | 0.06 | SFX volume (6% - subtle) |

### Structure Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| `intro` | `none` | No intro by default. Options: `explained_ai_diorama`, generic intros |
| `outro` | `none` | No outro by default. Options: `explained_ai_diorama`, generic outros |

## Workflow Overview

```
User: /create-video "Explain how AI agents use memory systems"

1. Agent analyzes concept and identifies key scenes
2. Agent proposes scene plan with descriptions, visual prompts, AND narration
3. User reviews and approves/modifies
4. Agent generates each scene with Veo 3.1 + voiceover
5. Agent assembles video with transitions, music, intro/outro
```

## Step 2: Plan Scenes with Narration

Present a table to the user including type and narration:

```
Here's my scene plan for "How Multi-Agent Systems Work":

| # | Type | Description | Narration (15-25 words) |
|---|------|-------------|-------------------------|
| 1 | visualize | Hook - The overwhelm problem | Every day, your team processes hundreds of tasks manually. But what if you could deploy an entire department that never sleeps? |
| 2 | explain | Architecture diagram - Three layers | Think of it like a three-layer cake. The orchestrator plans at the top, workers execute in the middle, and shared memory keeps everyone in sync. |
| 3 | visualize | Workers in action | Each worker specializes in one thing - reading emails, writing reports, scheduling meetings. They work in parallel, not sequentially. |

**Style**: diorama | **Music**: AI-generated ambient | **Intro/Outro**: none

Use 'diagram' for accurate framework/architecture visuals. Use 'explain' for quick overlays. Use 'visualize' for mood/atmosphere.
Approve these scenes, or suggest changes?
```

## VDL Format with Hybrid Scenes

```json
{
  "version": "1.0",
  "title": "How Multi-Agent Systems Work",
  "style": "diorama",
  "aspect_ratio": "16:9",
  "fast": false,

  "scenes": [
    {
      "id": "scene_01",
      "type": "visualize",
      "description": "Hook - The overwhelm problem",
      "visual_prompt": "Miniature diorama of tiny office workers drowning in stacks of paper, overwhelmed expressions, warm lighting through dusty windows...",
      "narration": "Every day, your team processes hundreds of tasks manually. But what if you could deploy an entire department that never sleeps?",
      "duration": 8.0
    },
    {
      "id": "scene_02",
      "type": "explain",
      "description": "Architecture diagram - Three layers",
      "image_prompt": "Warm toned infographic on cream paper showing three horizontal layers: 'Orchestrator' at top with brain icon, 'Workers' in middle with gear icons, 'Memory' at bottom with database icon. Soft shadows, hand-drawn style labels.",
      "narration": "Think of it like a three-layer cake. The orchestrator plans at the top, workers execute tasks in the middle, and shared memory keeps everyone in sync.",
      "duration": 10.0
    },
    {
      "id": "scene_03",
      "type": "visualize",
      "description": "Workers in action",
      "visual_prompt": "Miniature diorama of a tiny factory floor with specialized robots each doing different tasks - one reading documents, one typing, one filing...",
      "narration": "Each worker specializes in one thing. One reads emails, another writes reports, a third schedules meetings. They work in parallel, not sequentially.",
      "duration": 8.0
    }
  ],

  "transitions": {
    "type": "crossfade",
    "duration": 0.5
  },

  "audio": {
    "music_generate": true,
    "music_style": "Ambient, Electronic",
    "music_mood": "educational, wonder",
    "music_volume": 0.05,
    "voice_id": "${ELEVENLABS_VOICE_ID}",
    "scene_video_volume": 0.2,
    "voiceover_volume": 2.5,
    "sfx_between_scenes": "sweep_small_fast",
    "sfx_volume": 0.06
  },

  "structure": {
    "intro": "none",
    "outro": "none"
  },

  "output": {
    "path": "
  }
}
```

## Available Assets

### Series Intros/Outros (in skill assets/)
| Series | Intro | Outro | Duration | Style |
|--------|-------|-------|----------|-------|
| `explained_ai_diorama` | 8s | 8s | Diorama theater/workshop scenes | **DEFAULT** - matches B-roll style |
| `explained_ai` | 4s | 5s | Minimal text animation on black | Legacy - use for non-diorama styles |

### Generic Intros (from edit-video/)
**Short (~2s)**: `grow_blur_short`, `smoke_waves_short`, `curves_short`, `radiate`, `radiate_blur`, `grow`
**Long (~8s)**: `grow_blur`, `smoke_waves`, `curves`, `silk`
**Outros (~8s)**: `curves_v2`, `converging_circles`, `converging_v2`, `curves_receding`, `pulse_fade`

### SFX
| Name | Duration | Best For |
|------|----------|----------|
| `whoosh_fast_transition` | 1.33s | **DEFAULT** - scene transitions |
| `swoosh_flying` | 0.57s | Quick transitions |
| `tech_slide` | 2.26s | Tech content |

## Timing and Pacing

| Scene Count | Approx Duration | Generation Time |
|-------------|-----------------|-----------------|
| 3 scenes | ~35s | 10-20 min |
| 5 scenes | ~50s | 15-30 min |
| 8 scenes | ~75s | 25-45 min |

**Note**: Each scene takes 2-5 min (Veo) + ~5s (ElevenLabs voiceover).

## Important Notes

1. **Narration 15-25 words** - Allow proper explanation with analogies. Longer than before.
2. **Use analogies** - "Think of it like...", "Imagine a...", "It's similar to..." for complex concepts.
3. **Scene types** - Use `explain` for diagrams/infographics, `visualize` for Veo B-roll. Mix them.
4. **No intro/outro by default** - Start immediately. Only add if specifically requested.
5. **Per-scene voiceover** - Each scene gets its own TTS, mixed before assembly.
6. **Diorama is DEFAULT for visualize** - Read `.claude/skills/broll-diorama-style/SKILL.md` for prompt format.
7. **Human approval required** - Always present scene plan with type and narration, wait for approval.
8. **NO MUSIC/VOICES in Veo prompts** - Visual prompts are automatically appended with "No music, no voices, no speech, silent video."

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `generate_video.py` | Main orchestrator - generates scenes with voiceover, assembles |
| `../generate_voiceover.py` | Standalone ElevenLabs TTS generation |

## Completion Checklist

- [ ] Concept analyzed and scenes identified
- [ ] Style guides read (diorama, nano banana as needed)
- [ ] Music library checked for existing tracks
- [ ] Scene plan proposed with types, prompts, and narration
- [ ] [APPROVAL GATE] User approved scene plan
- [ ] All scenes generated (Veo for visualize, Nano Banana for explain/diagram)
- [ ] Voiceover generated per-scene via ElevenLabs
- [ ] AI music generated (unless disabled or existing track used)
- [ ] Video assembled with transitions and audio mixing
- [ ] Intro/outro added (if configured)
- [ ] Output file verified (plays, correct duration)
- [ ] New music added to catalog.json (if generated and good)

## Related Skills

- `/edit-video` - Edit existing videos with B-roll insertions
- `/create-heygen-video` - Generate talking-head avatar videos
- `/create-veo-video` - Generate single Veo clips
- `/broll-diorama-style` - Diorama style guide reference
- `/create-explanatory-image` - Self-critiqued diagram generation (used by `diagram` scene type)
