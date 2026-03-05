---
name: create-presentation
description: Generate a visual presentation from a concept description. Decomposes into slides, generates each as an explanatory image using /create-explanatory-image, and assembles into a cohesive slide deck folder.
automation: gated
calls:
  - create-explanatory-image
  - nano-banana-image-generator
allowed-tools: Bash, Read, Write, Glob, AskUserQuestion, Task
user-invocable: true
metadata:
  version: "1.2"
  created: 2026-03-03
  updated: 2026-03-03
  author: Ruby
  changelog:
    - "1.2: Save output to Google Drive Content/[MM.YYYY]/Presentations/[slug]/"
    - "1.1: Parallel slide generation via Task sub-agents for faster execution"
    - "1.0: Initial version (sequential generation)"
---

# Create Presentation

## Purpose

Take a presentation description or outline, decompose it into individual slide definitions, generate each slide as an explanatory image (delegating to `/create-explanatory-image` pattern), and assemble the results into a numbered slide deck folder.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Explanatory image skill | `.claude/skills/create-explanatory-image/SKILL.md` | yes | | Generation process and learned patterns |
| Best practices | `.claude/skills/nano-banana-image-generator/best_practices.md` | yes | | Image constraints and style guide |
| Generate script | `.claude/skills/nano-banana-image-generator/scripts/generate_image.py` | yes | | Image generation API |
| Output folder | Google Drive `Content/[MM.YYYY]/Presentations/[slug]/` | | yes | Final slide deck |

## Prerequisites

- `GOOGLE_API_KEY` or `GEMINI_API_KEY` set in `.env`
- Nano Banana image generator scripts available
- `/create-explanatory-image` skill available at `.claude/skills/create-explanatory-image/`

## Inputs

- **Presentation description**: Full description of the presentation (topic, audience, slide ideas, or detailed outline)
- **Style** (optional): `dark` or `warm`. Default: `warm` (applied consistently across all slides)
- **Aspect ratio** (optional): Default: `16:9`

Output is saved to Google Drive at `Content/[MM.YYYY]/Presentations/[slug]/`.

---

## Process

### Step 1: Read Current State

1. Read `.claude/skills/create-explanatory-image/SKILL.md`:
   - Review the self-critique checklist and learned patterns
   - Note any new failure patterns to avoid

2. Read `.claude/skills/nano-banana-image-generator/best_practices.md`:
   - Confirm constraints: 10 boxes, 10 labels, 3 hierarchy levels per slide

3. Create Drive output folder:
   - Month folder: `Content/[MM.YYYY]` (look up ID from google_drive_folders.md)
   - Create Presentations subfolder if needed:
     ```bash
     python3 .claude/scripts/google/google_drive.py mkdir "Presentations" [month-folder-id]
     ```
   - Create slug folder:
     ```bash
     python3 .claude/scripts/google/google_drive.py mkdir "[slug]" [presentations-folder-id]
     ```
   - Note the final folder ID for uploads later

4. Use `/tmp/pres_[slug]/` as local working directory:
   ```bash
   mkdir -p /tmp/pres_[slug]
   ```

### Step 2: Decompose into Slide Definitions

Analyze the presentation description and break it into individual slides.

**For each slide, define:**

```
Slide [N]: [Title]
- Purpose: What single concept this slide communicates
- Layout type: framework / comparison / flow / loop / metaphor / timeline / cross-section
- Key visual elements: [list]
- Key text labels: [list, max 10]
- Relationship to previous slide: [how it builds on or contrasts with the prior slide]
```

**Slide decomposition principles:**

1. **One concept per slide** - if a slide has two distinct ideas, split it
2. **Visual variety** - alternate layout types across slides (don't do 5 flow diagrams in a row)
3. **Narrative arc** - slides should tell a story in sequence:
   - Slide 1: Set up the problem or context
   - Middle slides: Build the explanation
   - Final slide: Resolution, key takeaway, or call to action
4. **Consistent style** - all slides share the same color palette, font style, and background
5. **Max 8 slides** - if the outline exceeds 8, consolidate. Fewer slides = stronger presentation.

### Step 3: Review Slide Plan

[APPROVAL GATE] - Present the slide plan before generating

**Present to user:**

```
## Presentation: [Title]
## [N] Slides

Slide 1: [Title]
  Concept: [one sentence]
  Layout: [type]
  Elements: [count] / Labels: [count]

Slide 2: [Title]
  Concept: [one sentence]
  Layout: [type]
  Elements: [count] / Labels: [count]

...

Style: [warm/dark]
Aspect ratio: [ratio]
Estimated cost: ~$[0.039 * slides * ~5 attempts each]
```

**User options:**
1. **Approve** - proceed to generation
2. **Adjust slides** - reorder, add, remove, or modify slide definitions
3. **Abort** - cancel

If adjustments requested, revise and re-present.

### Step 4: Create Visual Spec

Before any generation happens, create a detailed **visual consistency spec** file that locks down every visual decision. This is the single source of truth that all parallel agents read.

Write `/tmp/pres_[slug]/visual_spec.md` with the following structure:

```markdown
# Visual Spec: [Presentation Title]

## Color Palette
- Background: [exact hex, e.g. #2D2926]
- Primary text: [exact hex, e.g. #FAF8F5]
- Accent 1 (primary): [hex + name, e.g. #D4A5A5 dusty rose]
- Accent 2: [hex + name]
- Accent 3: [hex + name]
- Accent 4: [hex + name]

## Typography
- Title style: [e.g. "bold uppercase, DM Sans, centered at top"]
- Title approximate size: [e.g. "largest text, ~8% of image height"]
- Label style: [e.g. "sentence case, medium weight, DM Sans"]
- Footer/subtitle: [e.g. "small italic, bottom-right corner"]

## Layout Rules
- Element shape: [e.g. "rounded rectangles with soft shadow" - same shape on ALL slides]
- Connector style: [e.g. "curved arrows with arrowheads" or "dotted lines"]
- Spacing: [e.g. "generous, at least 20% whitespace margins"]
- Labels placement: [e.g. "outside elements, not inside"]

## Prompt Prefix
Every slide prompt MUST begin with this exact string:

"[Full style sentence, e.g.: A warm charcoal background (#2D2926) infographic
with soft cream text (#FAF8F5), illustrated flat design with soft shadows,
DM Sans font style, using dusty rose (#D4A5A5), coral (#E8B4A0), muted teal
(#7BA3A3), and soft gold (#D4C4A0) accents. Rounded rectangles with subtle
drop shadows. Clean minimal design with generous spacing.]"

## Slide Definitions

### Slide 01: [Title]
- Purpose: [one sentence]
- Layout: [type]
- Elements: [list with count]
- Labels: [list with count]
- Output: /tmp/slide01_[slug].png

### Slide 02: [Title]
...

## Constraints (from best practices)
- Max 10 boxes, 10 labels, 3 hierarchy levels per slide
- Words to avoid: [list of 4+ syllable words replaced with alternatives]

## Learned Patterns
[Paste relevant patterns from /create-explanatory-image]
```

**Key decisions to make in this step:**
1. Pick ONE element shape and stick with it across all slides
2. Pick ONE title placement and size
3. Write the prompt prefix once - this is the visual glue
4. Simplify all slide definitions against constraints (count elements/labels, replace complex words)

[APPROVAL GATE] - Present the visual spec to the user for review before generation. This is the contract that all slides will follow.

### Step 5: Generate All Slides (Parallel)

Spawn one **Task sub-agent per slide**, all in parallel. Each agent reads the visual spec file for its context.

#### 5a. Spawn Parallel Agents

Send a **single message** with N Task tool calls (one per slide), all `subagent_type: "gemini-agent"`:

```
For each slide, the Task prompt must include:

1. Read the visual spec file at [output_folder]/visual_spec.md
2. Read the best practices at .claude/skills/nano-banana-image-generator/best_practices.md
3. Generate slide [N]: "[slide title]"
   - Use the EXACT prompt prefix from the visual spec
   - Follow the slide definition from the visual spec (layout, elements, labels)
   - Output to the path specified in the visual spec

PROCESS:
a. Read visual_spec.md and best_practices.md
b. Craft a prompt that starts with the exact prompt prefix, then adds
   this slide's specific layout and elements
c. Generate 3 variants using:
   python3 .claude/skills/nano-banana-image-generator/scripts/generate_image.py \
     "[prompt]" [output_path_vN] --aspect-ratio [ratio]
   Wait 2 seconds between API calls.
d. Self-critique each variant:
   - View the image
   - Check: title spelling, label accuracy, element count, logical structure,
     missing/duplicate elements, readability
   - Check visual spec compliance: correct background color, element shape,
     title placement, accent colors
   - Classify: Good / Fixable / Redo
   - Fix if needed - max 3 iteration rounds per variant
e. Select the best version and save as: /tmp/slide[NN]_[slug].png
f. Report back: which version was selected, iterations count, any imperfections,
   and whether it visually matches the spec
```

**All agents launch in parallel** - do NOT wait for one to finish before starting the next.

#### 5b. Collect Results

After all agents complete:

1. **Read each agent's response** for status and visual spec compliance
2. **Verify all output files exist**:
   ```bash
   ls -la /tmp/slide*_*.png
   ```
3. **Copy to local working directory**:
   ```bash
   cp /tmp/slide[NN]_[slug].png /tmp/pres_[slug]/slide_[NN]_[slug].png
   ```

If any agent failed, retry that specific slide as a single new Task agent pointing to the same visual spec.

#### Rate Limit Note

With parallel agents, API calls happen concurrently. If rate limits are hit, individual agents handle their own retries (wait 3 seconds). If quota is exhausted, agents will report the error and those slides can be retried sequentially after a 60-second cooldown.

### Step 6: Review Complete Deck

[APPROVAL GATE] - Present all slides together

Display all generated slides in order, showing:
- Each slide image
- What it communicates
- Any remaining minor imperfections

**User options:**
1. **Approve all** - finalize the deck
2. **Redo specific slides** - identify which slides need regeneration and what to change
3. **Adjust and regenerate** - modify a slide's concept and regenerate
4. **Reorder** - change slide sequence

If changes requested:
- Regenerate only the affected slides
- Re-run self-critique on regenerated slides
- Return to this gate

### Step 7: Upload to Google Drive and Cleanup

1. **Ensure all final slides** have consistent naming in `/tmp/pres_[slug]/`:
   ```
   /tmp/pres_[slug]/
     slide_01_[title].png
     slide_02_[title].png
     ...
     slide_[NN]_[title].png
   ```

2. **Upload all final slides to Google Drive**:
   ```bash
   for file in /tmp/pres_[slug]/slide_*.png; do
     python3 .claude/scripts/google/google_drive.py upload "$file" "$(basename $file)" [drive-folder-id]
   done
   ```

3. **Upload visual spec** for reference:
   ```bash
   python3 .claude/scripts/google/google_drive.py upload /tmp/pres_[slug]/visual_spec.md "visual_spec.md" [drive-folder-id]
   ```

4. **Delete all local files**:
   ```bash
   rm -rf /tmp/pres_[slug] /tmp/slide[0-9][0-9]_*.png
   ```

### Step 8: Write Completion Summary

```
## Presentation Generated

**Title**: [presentation title]
**Slides**: [count]
**Output**: Google Drive `Content/[MM.YYYY]/Presentations/[slug]/`
**Style**: [warm/dark]

### Slides:
1. slide_01_[title].png - [concept]
2. slide_02_[title].png - [concept]
...

**Total images generated**: [count] (including iterations)
**Estimated cost**: ~$[0.039 * total_images]
```

---

## Outputs

- Complete slide deck as numbered PNG files on Google Drive at `Content/[MM.YYYY]/Presentations/[slug]/`
- `visual_spec.md` uploaded to Drive for reference
- All local intermediate files cleaned up

## Error Recovery

| Error | Recovery | Notify |
|-------|----------|--------|
| API rate limit | Wait 3 seconds, retry | No |
| API quota exceeded | Wait 60 seconds, retry once. If persistent, save progress and pause. | Yes |
| Single slide fails after 3 rounds | Skip and flag for manual attention | Yes |
| All slides same layout | Review Step 2 decomposition, vary layout types | No |
| Inconsistent style across slides | Check visual_spec.md compliance, regenerate outliers with same prompt prefix | No |

## Completion Checklist

- [ ] Best practices and learned patterns read fresh
- [ ] Presentation decomposed into slides with clear concepts
- [ ] Slide plan approved by user
- [ ] Visual spec created with locked colors, typography, element shapes, and prompt prefix
- [ ] Visual spec approved by user
- [ ] All slides generated in parallel with self-critique loops
- [ ] All slides reviewed as a complete deck
- [ ] User approved final deck
- [ ] Files named consistently with zero-padded numbering
- [ ] All slides uploaded to Google Drive
- [ ] Visual spec uploaded to Google Drive
- [ ] Local intermediate files deleted

## Visual Consistency Checklist

Apply across all slides to maintain cohesion:

- [ ] Same background color on every slide
- [ ] Same accent color palette (dusty rose, coral, teal, gold for warm; brand colors for dark)
- [ ] Same text color and approximate font weight
- [ ] Consistent element style (all circles, or all rounded rectangles - not mixed)
- [ ] Title placement consistent (always top center, same approximate size)

## Self-Improvement

After completing this skill's primary task, consider tactical improvements:

- [ ] **Review execution**: Were there friction points, unclear steps, or inefficiencies?
- [ ] **Slide decomposition quality**: Did the initial slide plan need heavy revision? Could the decomposition heuristics be better?
- [ ] **Cross-slide consistency**: Were there visual consistency issues? Add to the consistency checklist.
- [ ] **Generation efficiency**: Could fewer variants or iterations have achieved the same quality?
- [ ] **Apply improvement** (if identified):
  - [ ] Edit this SKILL.md with the specific improvement
  - [ ] Keep changes minimal and focused
- [ ] **Version control** (if in a git repository):
  - [ ] Stage: `git add .claude/skills/create-presentation/SKILL.md`
  - [ ] Commit: `git commit -m "refactor(create-presentation): <brief improvement description>"`

### Learned Patterns

<!-- Add patterns discovered through self-improvement here -->
- Warm charcoal style produces more consistent results across multiple slides than dark brand style
- Slides with the same layout type in sequence feel repetitive - alternate between flow, loop, cross-section, comparison
- Establishing the title style on slide 1 and referencing it in subsequent prompts helps consistency
- Parallel generation via Task sub-agents is faster but requires giving each agent the full style prompt prefix and best practices for visual cohesion
- Each sub-agent must receive the complete style reference, best practices, and learned patterns - never assume shared context
