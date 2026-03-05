---
name: create-instagram-post
description: Generate Instagram carousel posts (5-10 square slides) from any source material. Mixes three visual styles - dark brand, warm infographic, and photo-overlay - for maximum feed impact.
automation: gated
calls:
  - nano-banana-image-generator
  - create-explanatory-image
  - tone-of-voice-applicator
allowed-tools: Bash, Read, Write, Glob, AskUserQuestion, Task
user-invocable: true
metadata:
  version: "1.0"
  created: 2026-03-03
  author: Ruby
---

# Create Instagram Post

## Purpose

Generate a complete Instagram carousel post (5-10 square 1:1 images) from any source material - article, transcript, random text, talking points. Produces a hook slide that stops the scroll, explanatory/concept slides in the middle, and a CTA slide at the end. Mixes three visual styles for variety.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Best practices | `.claude/skills/nano-banana-image-generator/best_practices.md` | yes | | Image constraints |
| Carousel styleguide | `Prompts/Brand_carousel_styleguide.md` (Drive) | yes | | Brand design tokens |
| Explanatory image skill | `.claude/skills/create-explanatory-image/SKILL.md` | yes | | Self-critique patterns |
| Output folder | Google Drive `Content/[MM.YYYY]/Instagram/[slug]/` | | yes | Final carousel images |

## Prerequisites

- `GOOGLE_API_KEY` or `GEMINI_API_KEY` set in `.env`
- Nano Banana image generator scripts available

## Inputs

- **Source material**: Article text, transcript, talking points, URL, or topic description (required)
- **Slide count** (optional): 5-10. Default: 7
- **Style mix** (optional): Which styles to use. Default: all three

Output is always saved to Google Drive at `Content/[MM.YYYY]/Instagram/[slug]/`.

```bash
/create-instagram-post "paste your article or text here"
/create-instagram-post /path/to/article.md
/create-instagram-post "Topic: why agents need more constraints, not fewer"
```

---

## Three Visual Styles

Each carousel mixes styles across slides for visual variety. Never use the same style for all slides.

### Style 1: Dark Brand (Hook + CTA slides)

Best for: Bold statements, hooks, calls to action. High contrast, punchy.

```
Black background (#000000), white text (#ffffff), DM Sans font,
bold 800 weight titles occupying 60-80% of frame. Clean minimal.
Accent: #22c55e (green checks), #ef4444 (red X). No illustrations.
Text-dominant. Maximum impact.
```

**Use for**: Slide 1 (hook), final slide (CTA), bold quote slides.

### Style 2: Warm Infographic (Concept/explanation slides)

Best for: Diagrams, frameworks, processes. Educational and approachable.

```
Warm charcoal background (#2D2926), soft cream text (#FAF8F5),
illustrated flat design with soft shadows, DM Sans font style,
dusty rose (#D4A5A5), coral (#E8B4A0), muted teal (#7BA3A3),
soft gold (#D4C4A0) accents. Rounded rectangles with subtle
drop shadows. Clean minimal design with generous spacing.
```

**Use for**: Framework diagrams, before/after comparisons, process flows, concept explanations.

### Style 3: Photo-Overlay (Attention/variety slides)

Best for: Cinematic scenes with bold text overlay. Stops the scroll.

```
AI-generated cinematic photograph as full background - warm tones,
film-inspired color grading, shallow depth of field. Bold white text
overlay with subtle dark shadow/gradient for readability. DM Sans
font, 700 weight. Text occupies 40-60% of frame. The image supports
the message emotionally, not literally.
```

**Use for**: Emotional hooks, provocative statements, metaphorical visuals, transition slides.

---

## Process

### Step 1: Read Current State

1. Read `.claude/skills/nano-banana-image-generator/best_practices.md`
2. Read `.claude/skills/create-explanatory-image/SKILL.md` - note learned patterns
3. Determine Drive output path:
   - Month folder: `Content/[MM.YYYY]` (look up ID from google_drive_folders.md)
   - Create Instagram subfolder if needed:
     ```bash
     python3 .claude/scripts/google/google_drive.py mkdir "Instagram" [month-folder-id]
     ```
   - Create slug folder:
     ```bash
     python3 .claude/scripts/google/google_drive.py mkdir "[slug]" [instagram-folder-id]
     ```
   - Note the final folder ID for uploads later
4. Use `/tmp/ig_[slug]/` as local working directory:
   ```bash
   mkdir -p /tmp/ig_[slug]
   ```

### Step 2: Extract Key Messages

Analyze the source material and extract:

1. **Core topic**: One sentence summary
2. **Hook angle**: What stops the scroll? Use 3S+2F framework:
   - Scary (fear), Strange (curiosity), Sexy (desire), Free Value (gratitude), Familiar (trust)
3. **Key insights**: 3-7 distinct points that can each be a slide
4. **Quotable lines**: Short, punchy statements from the material
5. **CTA**: What should the viewer do? (follow, comment, save, share, link in bio)

### Step 3: Plan the Carousel

Design each slide with a specific role and style assignment.

**Carousel structure rules:**
- **Slide 1**: ALWAYS a hook. Style: Dark Brand or Photo-Overlay. Bold text, provocative statement or question.
- **Slides 2-N-1**: Content slides. Mix of Warm Infographic (for concepts) and Photo-Overlay (for variety). No more than 2 consecutive slides in the same style.
- **Final slide**: ALWAYS a CTA. Style: Dark Brand. Clear action: "Follow for more", "Save this post", etc.

**For each slide, define:**

```
Slide [N]: [Working title]
- Role: hook / concept / quote / comparison / process / CTA
- Style: dark-brand / warm-infographic / photo-overlay
- Text: [exact text that appears on the image]
- Visual: [what the image shows beyond text]
- Labels: [count] / 8 max
```

**Constraints per slide:**
- Maximum 8 text labels (fewer than 16:9 because square is smaller)
- Maximum 8 visual elements
- One concept per slide
- Text must be readable at phone size (Instagram feeds are small)
- All text in simple words (no 4+ syllable words)

### Step 4: Review Carousel Plan

[APPROVAL GATE] - Present the carousel plan before generating

```
## Instagram Carousel: [Topic]
## [N] Slides

Slide 1 (HOOK): [title]
  Style: [dark-brand/photo-overlay]
  Text: "[exact hook text]"

Slide 2: [title]
  Style: [style]
  Concept: [one sentence]

...

Slide N (CTA): [title]
  Style: dark-brand
  Text: "[CTA text]"

Style mix: [count] dark-brand / [count] warm-infographic / [count] photo-overlay
Estimated cost: ~$[0.039 * slides * ~4 attempts]
```

### Step 5: Create Visual Spec

Write `/tmp/ig_[slug]/visual_spec.md` locking down all visual decisions:

```markdown
# Visual Spec: [Carousel Topic]

## Format
- Aspect ratio: 1:1 (1024x1024)
- Platform: Instagram carousel

## Style Prompt Prefixes

### Dark Brand
"A square 1:1 Instagram post with pure black background (#000000).
Bold white text (#ffffff) in DM Sans font, 800 weight, occupying
60-80% of the frame. Clean minimal design. No illustrations, no
decorations - text only with maximum visual impact. Mobile-optimized
for Instagram feed viewing."

### Warm Infographic
"A square 1:1 Instagram post with warm charcoal background (#2D2926),
soft cream text (#FAF8F5), illustrated flat design with soft shadows,
DM Sans font style, using dusty rose (#D4A5A5), coral (#E8B4A0),
muted teal (#7BA3A3), and soft gold (#D4C4A0) accents. Rounded
rectangles with subtle drop shadows. Clean minimal design with
generous spacing. Optimized for mobile Instagram feed viewing."

### Photo-Overlay
"A square 1:1 Instagram post. Full-bleed cinematic photograph as
background - warm color grading, film-inspired tones, shallow depth
of field, [SCENE DESCRIPTION]. Bold white text overlay in DM Sans
font, 700 weight, with subtle dark gradient behind text for
readability. Text occupies 40-60% of frame. Cinematic and emotional."

## Slide Definitions
[Each slide with role, style, text, visual spec]

## Constraints
- Max 8 text labels per slide (square format is smaller than 16:9)
- Max 8 visual elements per slide
- Simple words only - replace 4+ syllable words
- Labels outside shapes when possible

## Learned Patterns
[From create-explanatory-image]
```

[APPROVAL GATE] - Present visual spec for review.

### Step 6: Generate All Slides (Parallel)

Spawn one **Task sub-agent per slide**, all in parallel, each `subagent_type: "gemini-agent"`.

Each agent's prompt must include:

```
1. Read the visual spec file at [output_folder]/visual_spec.md
2. Read best practices at .claude/skills/nano-banana-image-generator/best_practices.md
3. Generate slide [N]: "[title]"
   - Use the EXACT prompt prefix for this slide's style from the visual spec
   - Follow the slide definition (role, text, visual elements)
   - Output to /tmp/ig_slide[NN]_[slug].png
   - IMPORTANT: Aspect ratio is 1:1 (square)

PROCESS:
a. Read visual_spec.md and best_practices.md
b. Craft prompt starting with the exact style prefix, then add slide-specific content
c. Generate 3 variants:
   python3 .claude/skills/nano-banana-image-generator/scripts/generate_image.py \
     "[prompt]" /tmp/ig_slide[NN]_v[N].png --aspect-ratio 1:1
   Wait 2 seconds between API calls.
d. Self-critique each variant:
   - View the image
   - Check: text spelling, readability at small size, style compliance,
     element count, visual impact
   - For hook slides: Would this stop the scroll? Is the text bold enough?
   - For concept slides: Is the explanation clear in 3 seconds?
   - For CTA slides: Is the action obvious?
   - Classify: Good / Fixable / Redo
   - Fix if needed - max 3 iteration rounds per variant
e. Select best version and save as: /tmp/ig_slide[NN]_[slug].png
f. Report: version selected, iterations, imperfections, style compliance
```

**All agents launch in parallel.**

### Step 7: Review Complete Carousel

[APPROVAL GATE] - Present all slides in order

Display each slide image showing:
- Slide number and role (hook/concept/CTA)
- Style used
- Any remaining imperfections

**Check carousel flow:**
- [ ] Hook slide grabs attention immediately
- [ ] Each slide builds on the previous one
- [ ] No two consecutive slides use the same style
- [ ] Concept slides are clear and educational
- [ ] CTA slide has a clear action
- [ ] Text is readable at Instagram feed size (small!)

**User options:**
1. **Approve all** - finalize
2. **Redo specific slides** - which ones and what to change
3. **Reorder** - change slide sequence
4. **Change style** - swap a slide's visual style

### Step 8: Upload to Google Drive and Cleanup

1. Rename final slides with consistent naming in `/tmp/ig_[slug]/`:
   ```
   /tmp/ig_[slug]/
     slide_01_hook.png
     slide_02_[concept].png
     ...
     slide_[NN]_cta.png
   ```

2. Upload all final slides to Google Drive:
   ```bash
   for file in /tmp/ig_[slug]/slide_*.png; do
     python3 .claude/scripts/google/google_drive.py upload "$file" "$(basename $file)" [drive-folder-id]
   done
   ```

3. Delete all local intermediate and final files:
   ```bash
   rm -rf /tmp/ig_[slug] /tmp/ig_slide[0-9][0-9]_*.png
   ```

### Step 9: Generate Caption

Write an Instagram caption to accompany the carousel:

1. **Opening line**: Hook that matches slide 1 (first line visible in feed)
2. **Body**: 2-3 short paragraphs expanding on the carousel content
3. **Hashtags**: 5-10 relevant hashtags (mix of broad and niche)
4. **CTA**: Matches the final slide

Save caption locally to `/tmp/ig_[slug]/caption.md`, then upload to Drive:
```bash
python3 .claude/scripts/google/google_drive.py upload /tmp/ig_[slug]/caption.md "caption.md" [drive-folder-id]
```

**Caption guidelines:**
- First line is most important (visible before "...more")
- Use line breaks for readability
- No more than 2200 characters
- Hashtags at the end or in first comment

### Step 10: Write Completion Summary

```
## Instagram Carousel Generated

**Topic**: [topic]
**Slides**: [count]
**Output**: Google Drive `Content/[MM.YYYY]/Instagram/[slug]/`
**Style mix**: [X] dark-brand / [Y] warm-infographic / [Z] photo-overlay

### Slides:
1. slide_01_hook.png - HOOK - [style] - "[text preview]"
2. slide_02_[name].png - CONCEPT - [style] - "[text preview]"
...

### Caption:
[first line preview]

**Total images generated**: [count] (including iterations)
**Estimated cost**: ~$[0.039 * total_images]

### Ready to post:
/post-now instagram [output_folder]
```

---

## Outputs

- Complete carousel as numbered 1:1 PNG files on Google Drive at `Content/[MM.YYYY]/Instagram/[slug]/`
- `caption.md` with Instagram caption (also on Drive)
- All local intermediate files cleaned up

## Error Recovery

| Error | Recovery | Notify |
|-------|----------|--------|
| API rate limit | Wait 3 seconds, retry | No |
| API quota exceeded | Wait 60 seconds, retry once | Yes |
| Photo-overlay text unreadable | Switch to dark-brand style for that slide | No |
| All slides same style feel | Verify style assignments, regenerate outliers | No |
| Hook slide not impactful | Try Photo-Overlay instead of Dark Brand (or vice versa) | No |
| Text too small for square | Reduce to 4-5 labels max, increase text size in prompt | No |

## Completion Checklist

- [ ] Best practices and learned patterns read fresh
- [ ] Source material analyzed and key messages extracted
- [ ] Carousel plan approved (roles, styles, text)
- [ ] Visual spec created with locked style prefixes
- [ ] All slides generated in parallel with self-critique
- [ ] Carousel reviewed as complete sequence
- [ ] No two consecutive slides use the same style
- [ ] Caption generated
- [ ] User approved final carousel
- [ ] Files named consistently
- [ ] All slides uploaded to Google Drive
- [ ] Caption uploaded to Google Drive
- [ ] Local intermediate files deleted

## Instagram Best Practices

- **Carousel engagement**: Average 1.4x more reach than single images
- **Optimal slide count**: 7-10 slides (more slides = more time on post = more reach)
- **Hook is everything**: 80% of carousel success is slide 1
- **Swipe motivation**: Each slide must make the viewer want to see the next one
- **Text size**: Larger than you think - Instagram feed is small on phones
- **Consistency**: Same visual language across the carousel, but enough variety to not feel monotonous
- **Save-worthy**: Educational carousels get saved, which boosts algorithmic reach
- **Caption synergy**: Caption should complement, not repeat, the carousel content

## Self-Improvement

After completing this skill's primary task, consider tactical improvements:

- [ ] **Review execution**: Were there friction points, unclear steps, or inefficiencies?
- [ ] **Style effectiveness**: Which of the three styles produced the best results? Update defaults.
- [ ] **Hook quality**: Did the hook slide actually look scroll-stopping? What made it work or fail?
- [ ] **Square format issues**: Did 1:1 ratio cause any text/layout problems not seen in 16:9?
- [ ] **Apply improvement** (if identified):
  - [ ] Edit this SKILL.md with the specific improvement
  - [ ] Keep changes minimal and focused
- [ ] **Version control** (if in a git repository):
  - [ ] Stage: `git add .claude/skills/create-instagram-post/SKILL.md`
  - [ ] Commit: `git commit -m "refactor(create-instagram-post): <brief improvement description>"`

### Learned Patterns

<!-- Add patterns discovered through self-improvement here -->
