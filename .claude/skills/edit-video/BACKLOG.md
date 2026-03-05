# edit-video Skill Backlog

## Completed

### ~~Agent-Driven B-Roll Planning (Human-in-Loop)~~ ✓
**Implemented January 2026**

The workflow now follows the correct pattern:
1. Agent transcribes video
2. Agent reads transcript + guidelines (broll_placement_guide.md, nano_banana_best_practices.md)
3. Agent proposes B-roll plan with table: Time | Context | Visual Prompt
4. User reviews, corrects, approves
5. Agent generates B-roll using approved prompts and assembles video

**Changes made**:
- SKILL.md rewritten with human-in-loop workflow
- EDL format updated with `visual_prompt` field (agent-written, not auto-generated)
- `execute_moviepy.py` updated to use `visual_prompt` from EDL
- `generate_broll_image.py` already supported `--visual` parameter
- Added color correction: B-roll brightness/warmth matched to main video at insertion point
- Added mandatory prompt template following Nano Banana best practices and B-roll Style Guide

### ~~Intro Screen~~ ✓
- `--intro grow_blur` prepends intro template
- Works correctly (tested)

### ~~SFX Integration~~ ✓
- Whoosh sounds at B-roll transitions
- 3 rotating sounds, 0.15 volume, -0.15s offset

### ~~MoviePy Pipeline~~ ✓
- Single-pass encoding
- Proper audio sync
- Intro concatenation

### ~~Color Correction~~ ✓
- Analyzes main video brightness/warmth at B-roll insertion point
- Applies correction to B-roll to match main video
- Subtle adjustment to blend AI-generated visuals with talking-head footage

### ~~Background Music~~ ✓
**Implemented January 2026**

- Music now plays correctly with fade-in after intro
- Fixed MoviePy API: use `afx.AudioFadeIn/Out` effects instead of deprecated methods
- Music loops automatically if shorter than video
- EDL supports: `background_music`, `music_volume`, `music_fade_in`, `music_fade_out`
- Music starts after intro ends (proper timing)
- First track added: `GottaFeel.mp3` in `assets/music/`

---

## Open Items

None currently.

---

## Medium Priority

### B-Roll Effects in MoviePy
- FadeIn/FadeOut on B-roll clips
- Ken Burns via MoviePy (not FFmpeg)

### Audio Ducking
- Reduce main audio during B-roll (0.85-0.9x)

---

## Correct /edit-video Flow

```
User: /edit-video video.mp4 "Add B-roll for key concepts"

1. Agent transcribes video
2. Agent reads transcript + guidelines
3. Agent proposes B-roll plan:

   "Here's my B-roll plan for review:

   | Time | Context | Visual Prompt |
   |------|---------|---------------|
   | 0:26 | 'AI tools reduce critical thinking' | Schematic: brain with dimming neural pathways... |
   | 1:08 | 'hippocampus shrinkage' | Anatomical brain cross-section... |

   Approve, or suggest changes?"

4. User: "Change #2 to be more abstract"

5. Agent updates plan, confirms

6. User: "Approved"

7. Agent generates B-rolls and assembles video
```

---
*Updated: January 2026*
