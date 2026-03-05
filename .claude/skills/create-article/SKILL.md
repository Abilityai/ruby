---
name: create-article
description: Generate full article from knowledge base via knowledge base agent. Use when creating long-form content for LinkedIn, Medium, Substack, X Articles, or blog.
automation: gated
calls:
  - knowledge-base-query
  - tone-of-voice-applicator
  - nano-banana-image-generator
  - content-library
allowed-tools: Bash, Read, Write, Task
metadata:
  version: "2.2"
  updated: 2026-02-11
  changelog:
    - "2.2: Added illustration QA step - review for text errors and clarity, regenerate failures"
    - "2.1: Added concept-based illustrations (5 options per concept) with organized folder structure"
    - "2.0: Initial playbook structure"
---

# Create Article

Generate a complete, long-form article from the creator's knowledge base via knowledge base agent, with auto-generated images.

## Purpose

Create publication-ready articles with images, tracked in content library, ready for human review.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Content Library | `.claude/memory/content_library.yaml` | ✓ | ✓ | Track new article |
| Drafts Folder | `Articles/drafts/` (Google Drive) | | ✓ | Store article files |
| Tone Profile | `Prompts/Brand_LongForm_Tone_of_Voice_Profile.md` | ✓ | | Voice consistency |
| B-roll Style | `.claude/skills/broll-cinematic-lifestyle/SKILL.md` | ✓ | | Title image style |
| Nano Banana Guide | `.claude/skills/nano-banana-image-generator/best_practices.md` | ✓ | | Illustration style |

## Inputs

- **topic**: Article subject or angle (required)
- **platform**: linkedin, medium, substack, x-article, blog (optional, default: linkedin)
- **--title-style**: B-roll style for title images (default: cinematic-lifestyle)
- **--explainer-style**: Style for diagrams (default: infographic)

```bash
/create-article "Why smart companies resist AI adoption" linkedin
/create-article "Trinity: Deploy departments not agents" x-article --title-style=diorama
```

---

## Process

### Step 1: Read Current State

**Read fresh state before starting.**

1. Read content library:
   ```bash
   cat .claude/memory/content_library.yaml
   ```
   - Note existing articles to avoid duplicates
   - Check for similar topics in progress

2. Read tone profile:
   ```bash
   python3 .claude/scripts/google/google_drive.py download YOUR_LONGFORM_TOV_ID /tmp/longform_tone.md
   cat /tmp/longform_tone.md
   ```

3. Read B-roll style guide:
   ```bash
   cat .claude/skills/broll-cinematic-lifestyle/SKILL.md
   ```

### Step 2: Generate Article ID

Create kebab-case ID from topic:
- "Why smart companies resist AI" → `why-smart-companies-resist-ai`
- Max 50 characters
- Lowercase, hyphens only

### Step 3: Topic Confirmation

[APPROVAL GATE] - Confirm topic and platform before generation

Present to user:
- **Topic**: [topic]
- **Platform**: [platform]
- **Target Words**: [word count based on platform]
- **Article ID**: [generated-id]

| Platform | Target Words |
|----------|-------------|
| LinkedIn | 800-1200 |
| Medium | 1500-2500 |
| Substack | 1000-2000 |
| X Article | 2000-5000 |
| Blog | 1200-2000 |

Wait for approval before generating.

### Step 4: Generate Article Content

Query the knowledge base for perspective and content:

```bash
cd ${KNOWLEDGE_BASE_AGENT_PATH} && \
claude -p "Create a [WORD_COUNT]-word article about [TOPIC] for [PLATFORM].

Use the creator's unique perspectives, frameworks, and experiences from the knowledge base.

Structure:
1. Hook (50-100 words) - Attention-grabbing opening
2. Context (150-300 words) - Background, why this matters now
3. Main Insight (400-800 words) - Unique perspective, frameworks
4. Implications (150-300 words) - What this means, how to apply
5. Call to Action (50-100 words) - Next steps, engagement prompt

Apply the creator's voice: conversational, contrarian, specific examples over abstractions." \
--output-format json
```

Parse response and save to `/tmp/article_draft.md`.

### Step 5: Apply Tone of Voice

Run `/tone-of-voice-applicator` on draft:
- Platform: [platform]
- Profile: LongForm
- Input: `/tmp/article_draft.md`

### Step 6: Generate Title Images (10 options)

Read B-roll style guide and generate 10 title image variations:

```bash
for i in {01..10}; do
  python3 .claude/skills/nano-banana-image-generator/scripts/generate_image.py \
    "[PROMPT FROM BROLL STYLE GUIDE - vary subject, emotion, environment]" \
    "/tmp/article_images/title_$i.png" \
    --aspect-ratio 16:9
done
```

**Vary each image by:**
- Human subject (founder, team, user)
- Emotional state (curious, focused, determined)
- Environment (office, home, cafe)
- Lighting (morning, afternoon, golden hour)

### Step 7: Extract Key Concepts for Illustration

Analyze the article content and identify 3-5 key concepts that would benefit from visual explanation:

| Concept Type | Description | Example |
|--------------|-------------|---------|
| **Framework** | Main mental model or structure | "Four Pillars of Agent Infrastructure" |
| **Process** | Sequential steps or flow | "Credential rotation workflow" |
| **Comparison** | Before/after or versus | "Shadow AI vs Sovereign AI" |
| **Architecture** | System components and relationships | "Multi-agent orchestration layers" |
| **Metaphor** | Abstract concept made concrete | "Context rot as memory decay" |

For each concept, note:
- **Concept name**: Clear, concise label (use for folder name as snake_case)
- **Key elements**: 3-5 main components (max 10)
- **Relationships**: How elements connect
- **Emotion**: What the reader should feel

### Step 8: Create Visual Spec for Illustrations

Before generating any illustrations, create a visual spec that locks down style decisions for consistency across all concept diagrams. Write to `/tmp/article_images/visual_spec.md`:

```markdown
# Visual Spec: [Article Title] Illustrations

## Prompt Prefix
Every illustration prompt MUST begin with this exact string:

"A warm charcoal background (#2D2926) infographic with soft cream text (#FAF8F5),
illustrated flat design with soft shadows, DM Sans font style, using dusty rose
(#D4A5A5), coral (#E8B4A0), muted teal (#7BA3A3), and soft gold (#D4C4A0) accents.
Rounded rectangles with subtle drop shadows. Clean minimal design with generous spacing."

## Rules
- Element shape: rounded rectangles with soft shadow (same across ALL illustrations)
- Title: bold uppercase, centered at top
- Labels: sentence case, outside elements when possible
- Max 10 boxes, 10 labels, 3 hierarchy levels per diagram

## Concepts
[List each concept with its elements, labels, and layout type]
```

This spec is the single source of truth for all illustration generation below.

### Step 9: Generate Illustrations (5 options per concept)

For each identified concept, generate 5 visual variations using Nano Banana. **Start every prompt with the exact prompt prefix from the visual spec.**

**Use "Warm Infographic" style** (see `best_practices.md` for full reference):

```
CONSTRAINTS:
- Maximum 10 visual elements
- Maximum 10 text labels
- Maximum 3 hierarchy levels
- One core concept per diagram

MUST INCLUDE:
- Clear title at top
- Visual explanation (not just decoration)
- Labels that teach something
- Aspect ratio: 16:9 horizontal
```

**Generate illustrations:**

```bash
# Create illustration subdirectories
mkdir -p /tmp/article_images/illustrations

# For each concept, generate 5 variations
for concept in "concept_1" "concept_2" "concept_3"; do
  mkdir -p "/tmp/article_images/illustrations/${concept}"

  for i in {1..5}; do
    python3 .claude/skills/nano-banana-image-generator/scripts/generate_image.py \
      "[CONCEPT-SPECIFIC PROMPT with warm infographic style]" \
      "/tmp/article_images/illustrations/${concept}/option_${i}.png" \
      --aspect-ratio 16:9
  done
done
```

**Variation strategies for each concept:**
1. **Diagram type**: Framework, before/after, flow, metaphor, comparison
2. **Layout**: Centered vs columns vs horizontal flow vs circular
3. **Emphasis**: Different focal element highlighted
4. **Density**: Minimal (3-5 elements) vs moderate (6-8 elements)
5. **Metaphor**: Different visual analogies for same concept

**Example prompt (Warm Infographic style):**
```
Create a warm, illustrated infographic showing "The Four Pillars of Agent Infrastructure".

STYLE:
- Warm charcoal background (#2D2926)
- Soft cream text (#FAF8F5)
- Illustrated flat design with soft shadows
- Each pillar uses a different warm accent color

CONTENT:
- Four illustrated pillars as the central visual
- Each pillar has an icon and label:
  1. Shield icon - "SOVEREIGNTY" (dusty rose)
  2. Network icon - "ORCHESTRATION" (coral)
  3. Lock icon - "GOVERNANCE" (teal)
  4. Eye icon - "OBSERVABILITY" (gold)
- Pillars support a roof labeled "PRODUCTION SUCCESS"

LAYOUT:
- Title "FOUR PILLARS" large at top
- Architectural pillar diagram centered
- Maximum 10 text labels

Aspect ratio: 16:9 horizontal
```

### Step 10: QA Review - Fix Text Errors and Clarity Issues

**CRITICAL STEP**: AI image generators often produce text errors. Review every illustration.

**Download and visually inspect each generated image:**

```bash
# Open folder to review all images
open /tmp/article_images/illustrations/
```

**Check each image for:**

| Issue Type | What to Look For | Action |
|------------|-----------------|--------|
| **Misspelled words** | Garbled text, wrong letters, nonsense words | Regenerate |
| **Missing text** | Labels cut off, text too small to read | Regenerate |
| **Wrong text** | Labels don't match concept, incorrect terms | Regenerate |
| **Unclear diagram** | Can't understand concept in 3 seconds | Regenerate with simpler prompt |
| **Too cluttered** | More than 10 elements, hard to read | Regenerate with fewer elements |
| **Wrong style** | Photorealistic instead of illustrated | Regenerate with explicit style |

**For each failed image, regenerate with adjusted prompt:**

```bash
# Example: Regenerate option_03 with corrected spelling emphasis
python3 .claude/skills/nano-banana-image-generator/scripts/generate_image.py \
  "[SAME PROMPT but add: 'Ensure all text is spelled correctly: SOVEREIGNTY, ORCHESTRATION, GOVERNANCE, OBSERVABILITY']" \
  "/tmp/article_images/illustrations/[concept]/option_03.png" \
  --aspect-ratio 16:9
```

**Tips for fixing common issues:**
- **Spelling errors**: Explicitly list correct spellings in prompt
- **Cluttered**: Reduce elements, use "maximum 6 text labels"
- **Unclear**: Simplify to one visual metaphor, fewer components
- **Wrong style**: Add "illustrated flat design, NOT photorealistic"

**Learned patterns from image generation:**
- Words with 4+ syllables frequently misspell - replace with simpler alternatives (SOVEREIGNTY -> OWN SPACE, ORCHESTRATION -> COORDINATE, INFRASTRUCTURE -> FOUNDATION, OBSERVABILITY -> MONITOR)
- Labels OUTSIDE circles/nodes render more reliably than labels inside
- Circular diagrams with 6+ nodes duplicate labels - stick to 3-4 nodes max for loops
- Use numbered lists (1. STEP ONE, 2. STEP TWO) to force correct vertical stacking
- Explicitly state "exactly N nodes, not more, not fewer" when count precision matters
- Always use the Python `generate_image.py` script (not bash) - handles JSON escaping

**Repeat until all images pass QA checklist:**
- [ ] All text readable and correctly spelled
- [ ] Concept explained visually (not just decorated)
- [ ] Warm infographic style (charcoal bg, illustrated)
- [ ] Maximum 10 elements, clear hierarchy
- [ ] Would make sense to reader without article context

### Step 11: Content Review

[APPROVAL GATE] - Review generated content before saving

Present to user:
- **Title options** (3 suggestions)
- **Word count**
- **Key insights**
- **Title image thumbnails** (10 options)
- **Concept illustrations** (grouped by concept):
  - [Concept 1 name]: 5 options (show thumbnails)
  - [Concept 2 name]: 5 options (show thumbnails)
  - [Concept 3 name]: 5 options (show thumbnails)

Wait for:
- Approval to proceed
- Request changes to content
- Request new images for specific concept
- Abort

### Step 12: Create Google Drive Folder

```bash
# Ensure drafts folder exists
python3 .claude/scripts/google/google_drive.py ensure-path "Articles/drafts"

# Create article folder
python3 .claude/scripts/google/google_drive.py mkdir "[article-id]" YOUR_ARTICLES_DRAFTS_FOLDER_ID
# Note the new folder ID

# Upload article.md
python3 .claude/scripts/google/google_drive.py upload /tmp/article_draft.md "article.md" [article-folder-id]

# Create images folder structure
python3 .claude/scripts/google/google_drive.py mkdir "images" [article-folder-id]
# Note images folder ID

python3 .claude/scripts/google/google_drive.py mkdir "titles" [images-folder-id]
python3 .claude/scripts/google/google_drive.py mkdir "illustrations" [images-folder-id]
# Note titles and illustrations folder IDs

# Upload title images to images/titles/
for file in /tmp/article_images/title_*.png; do
  python3 .claude/scripts/google/google_drive.py upload "$file" "$(basename $file)" [titles-folder-id]
done

# Upload illustrations by concept to images/illustrations/
for concept_dir in /tmp/article_images/illustrations/*/; do
  concept=$(basename "$concept_dir")
  python3 .claude/scripts/google/google_drive.py mkdir "$concept" [illustrations-folder-id]
  # Note concept folder ID
  for file in "$concept_dir"/*.png; do
    python3 .claude/scripts/google/google_drive.py upload "$file" "$(basename $file)" [concept-folder-id]
  done
done
```

### Step 13: Write Updated State

**Explicitly save all state changes.**

1. Add entry to content_library.yaml:
   ```yaml
   - id: [article-id]
     title: "[Article Title]"
     status: draft
     drive_path: Articles/drafts/[article-id]
     created: [today]
     pillars: [detected pillars]
     target_platforms: [[platform]]
     published: {}
     notes: "Generated via /create-article"
   ```

2. Save content_library.yaml:
   ```bash
   # Write updated yaml
   ```

3. Create manifest in article folder:
   ```json
   {
     "title": "Article Title",
     "topic": "Original topic",
     "platform": "x-article",
     "status": "draft",
     "created_at": "2026-02-10T12:00:00Z",
     "word_count": 2500,
     "styles": {
       "title_style": "cinematic-lifestyle",
       "explainer_style": "infographic"
     }
   }
   ```

---

## Outputs

- Article folder at `Articles/drafts/[article-id]/`
  - `article.md` - Main content
  - `images/`
    - `titles/title_01-10.png` - Hero/title image options (10)
    - `illustrations/`
      - `[concept_1]/option_1-5.png` - 5 options for first concept
      - `[concept_2]/option_1-5.png` - 5 options for second concept
      - `[concept_3]/option_1-5.png` - 5 options for third concept
  - `_manifest.json` - Tracking metadata with concept list
- Entry in `content_library.yaml` with status: `draft`

## State Changes Summary

| Source | Change |
|--------|--------|
| `content_library.yaml` | New article entry added |
| `Articles/drafts/` | New folder with content |

## Error Recovery

If this playbook fails mid-execution:

1. **Check partial state:**
   ```bash
   # Check content library
   grep -A 10 "[article-id]" .claude/memory/content_library.yaml

   # Check Drive folder
   python3 .claude/scripts/google/google_drive.py find "[article-id]"
   ```

2. **Common issues:**
   - the knowledge base agent timeout: Re-run from Step 4
   - Image generation failed: Re-run from Step 6
   - Drive upload failed: Re-run from Step 9

3. **Recovery:**
   - If entry exists in yaml but no folder: delete entry, re-run
   - If folder exists but no yaml entry: add entry manually or delete folder
   - If both exist: verify status is correct, continue

## Completion Checklist

- [ ] Content library read fresh at start
- [ ] Topic approved by user
- [ ] Article generated and tone applied
- [ ] 10 title images generated (16:9)
- [ ] 3-5 concepts identified for illustration
- [ ] 5 illustration options generated per concept (16:9)
- [ ] Illustrations organized by concept folder
- [ ] Content reviewed and approved
- [ ] Google Drive folder created with proper structure
- [ ] All files uploaded (titles/, illustrations/[concept]/)
- [ ] content_library.yaml updated
- [ ] User notified of folder location

## Next Steps After Completion

1. The user reviews in Google Drive
2. When ready: `/content-library update [id] review`
3. User approves
4. Manual publish to platform
5. `/content-library publish [id] [platform] [url]`

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `/knowledge-base-query` | Called for knowledge base |
| `/tone-of-voice-applicator` | Called for voice consistency |
| `/nano-banana-image-generator` | Called for images |
| `/content-library` | Called to update tracking |
| `/broll-cinematic-lifestyle` | Referenced for title style |
| `/broll-diorama-style` | Alternative title style |

## Cost Tracking

- Article generation: ~$0.50-2.00 (the knowledge base agent)
- 10 title images: ~$0.39 (Nano Banana)
- 15-25 concept illustrations: ~$0.58-0.98 (3-5 concepts x 5 options each)
- **Total per article: ~$1.50-3.50**
