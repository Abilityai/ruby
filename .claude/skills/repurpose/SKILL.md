---
name: repurpose
description: Repurpose Video Content
automation: gated
allowed-tools: Bash, Read, Write
calls:
  - knowledge-base-query
  - tone-of-voice-applicator
  - content-pillar-tagger
  - nano-banana-image-generator
metadata:
  version: "2.1"
  updated: 2026-03-03
  changelog:
    - "2.1: Subfolder output structure with meaningful names, title images for long-form content"
    - "2.0: Initial playbook structure"
---

# Repurpose Video Content

Repurpose a video transcript into multi-platform social media content using the native Ruby Content Engine.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Transcript | `[folder]/transcript.md` | ✓ | | Source video transcript |
| TOV Profiles | `Prompts/*.md` (Google Drive) | ✓ | | Platform voice profiles |
| B-roll Style | `.claude/skills/broll-cinematic-lifestyle/SKILL.md` | ✓ | | Title image style guide |
| Nano Banana | `.claude/skills/nano-banana-image-generator/best_practices.md` | ✓ | | Image generation guide |
| Generated Content | `[folder]/Generated Content_*/` | | ✓ | Output folder with all content |
| Manifest | `[folder]/Generated Content_*/_manifest.json` | | ✓ | Job tracking and status |
| Content Library | `.claude/memory/content_library.yaml` | ✓ | ✓ | Track video repurposing stats |
| **Google Drive** | `Content/[month]/[topic]/Generated Content_*/` | | ✓ | **Persist outputs to Drive** |

## Quick Start

```bash
# Run full pipeline on a folder
python3 .claude/scripts/repurpose/repurpose.py /path/to/folder

# Test with sample transcript
python3 .claude/scripts/repurpose/repurpose.py --test

# Check configuration
python3 .claude/scripts/repurpose/repurpose.py --config
```

## Usage

```
/repurpose [folder_path | --test | --status FOLDER | --extract FOLDER | --generate FOLDER]
```

**Commands:**
- **folder path**: Run full pipeline on folder containing `transcript.md`
- **--test**: Run with test transcript (`resources/temp/Test/`)
- **--status FOLDER**: Show manifest status for a folder
- **--extract FOLDER**: Extract insights only (stage 1)
- **--generate FOLDER**: Generate content only (requires existing insights)
- **--config**: Show current configuration
- **--list**: List available folders

**Options:**
- `--mode solo|podcast`: Content mode (default: `solo`)
- `--feedback, -f "text"`: User feedback/direction for content extraction and generation
- `--types TYPE1,TYPE2`: Specify content types to generate
- `--no-knowledge_base`: Disable the knowledge base agent enrichment
- `--quiet, -q`: Quiet mode

## Feedback Flag

The `--feedback` (or `-f`) flag allows you to provide direction that influences both extraction and generation stages.

### Usage Examples

```bash
# Full pipeline with feedback
python3 .claude/scripts/repurpose/repurpose.py /path/to/folder -f "Focus on practical implementation"

# Extract with specific direction
python3 .claude/scripts/repurpose/repurpose.py --extract /path -f "Prioritize contrarian insights about ROI"

# Generate with tone direction
python3 .claude/scripts/repurpose/repurpose.py --generate /path -f "More provocative for Twitter, technical for LinkedIn"

# Multiple directions combined
python3 .claude/scripts/repurpose/repurpose.py /path --feedback "Emphasize cost considerations, add more data points, challenge conventional thinking"
```

### How Feedback Works

**For Extraction (Stage 1):**
- Influences which insights are extracted and prioritized
- Boosts scores for insights matching your direction
- Guides quotable moment selection toward feedback themes

**For Generation (Stage 3):**
- Guides tone and style across all content types
- Can specify platform-specific adjustments
- Emphasizes or de-emphasizes certain angles

**Feedback is processed** through the `feedback_processing.md` template, which:
- Converts vague feedback ("make it better") into specific instructions
- Handles platform-specific requests
- Detects "no feedback" patterns and skips processing

**Feedback is stored** in the `_manifest.json` for reference. When running `--generate` separately after `--extract`, if no new feedback is provided, the stored feedback from extraction will be used automatically.

## Podcast Mode

For podcasts/interviews with guests, use `--mode podcast`:

```bash
/repurpose /path/to/folder --mode podcast
```

### Required: guests.md

Create `guests.md` in the video folder with guest information:

```markdown
# Podcast Guests

## Mrinal Wadhwa
- slug: mrinal
- twitter: @mrinalwadhwa
- linkedin: linkedin.com/in/mrinalwadhwa
- company: Autonomy
- role: Founder
- photos: guest_photos/mrinal_*.jpg

## [Additional Guest]
- slug: guest2
- twitter: @handle
- photos: guest_photos/guest2_*.jpg
```

### [APPROVAL GATE] Guest Verification

Before generating content, the skill displays loaded guest info:

```
## Guest Profiles Loaded

### Guest 1: Mrinal Wadhwa
- Twitter: @mrinalwadhwa
- LinkedIn: linkedin.com/in/mrinalwadhwa
- Company: Autonomy
- Photos: 3 found

Is this information correct?
1. Yes, proceed
2. Edit guests.md first
3. Abort
```

**User must confirm** guest information is accurate before any content uses guest handles for tagging.

### Podcast Mode Content Types

In addition to standard content types, podcast mode generates:

| Type | Output | Description |
|------|--------|-------------|
| `instagram_post` | `instagram_post_001.md` | Caption with guest tags, uses approved thumbnails |
| `quote_card` | `quote_card_001.png` | Visual quote with guest reference photos |
| `guest_promo` | `guest_promo_001.md` | Cross-promotion content tagging guest |

### Podcast Mode Differences

| Aspect | Solo Mode | Podcast Mode |
|--------|-----------|--------------|
| Attribution | Creator only | Creator + all guests |
| Carousels | Midjourney backgrounds | Approved thumbnails + Midjourney |
| Instagram | Not generated | Generated with guest tags |
| Clips | Not checked | Uses `clips/` folder if exists (Riverside) |

### Folder Structure for Podcasts

```
[podcast_folder]/
├── transcript.md              # Required
├── guests.md                  # Required for podcast mode
├── guest_photos/              # Guest reference images
├── clips/                     # Riverside exports (optional)
├── Thumbnails_Final/          # Approved thumbnails (optional)
│   └── chosen_001.png
└── Generated Content_*/       # Output
```

## Prerequisites

**Required:** Target folder must contain `transcript.md`

**Environment Variables (in `.env`):**
- `GEMINI_API_KEY`: Required for AI generation
- `APITEMPLATE_API_KEY`: Required for carousels
- `CLOUDCONVERT_API_KEY`: Required for carousel images
- `LEGNEXT_API_KEY`: Optional for Midjourney backgrounds
- `KNOWLEDGE_BASE_AGENT_PATH`: Path to the knowledge base agent agent (for enrichment)

## Pipeline Stages

### Stage 1: Insight Extraction
Extracts 3-5 actionable insights from the transcript using Gemini AI.

```bash
python3 .claude/scripts/repurpose/repurpose.py --extract /path/to/folder
```

### Stage 2: the knowledge base agent Enrichment (Optional)
By default, enriches insights with the creator's authentic perspective. Use `--no-knowledge_base` flag to skip enrichment.

### Stage 3: Content Generation
Generates up to 7 content types for each insight. Each content piece is saved to its own **meaningfully-named subfolder** derived from the insight topic (e.g., `why-agents-need-memory-linkedin-post/`).

**Long-form types** (linkedin_post, blog_post, newsletter) also generate 3 cinematic-lifestyle title images per post using Nano Banana.

Content types:
- **linkedin_post**: 1,200-1,800 character posts + 3 title images
- **twitter_thread**: 5-10 tweet threads
- **newsletter**: 300-500 word email sections + 3 title images
- **community_post**: 200-400 character community posts
- **text_post**: 300-500 character platform-agnostic posts
- **linkedin_carousel**: 6-10 slide carousels (light PDF + dark PDF + images + post text)
- **blog_post**: SEO-optimized blog articles (AI decides which insights are blog-worthy) + 3 title images

```bash
# Generate specific types only
python3 .claude/scripts/repurpose/repurpose.py --generate /path --types linkedin_post,twitter_thread
```

### Title Image Generation (Long-Form Types)

For linkedin_post, blog_post, and newsletter content, 3 title images are automatically generated using the cinematic-lifestyle B-roll style (same approach as `/create-article`).

**Style**: Kodak Portra 400, 85mm f/1.4, warm pastel tones, muted low saturation, lifted shadows, shallow DOF.

**Variations** across the 3 images:
- Subject: tech founder, focused developer, collaborating team
- Emotion: curious, determined, energized
- Environment: modern office, home workspace, coworking space
- Lighting: morning golden hour, warm afternoon, natural diffused

**Cost**: ~$0.12 per long-form post (3 images x $0.039/image)

### Stage 4: Google Drive Persistence

**CRITICAL**: All generated content MUST be persisted to Google Drive. Local/temp folders are for working only.

After content generation completes:

```bash
# Upload Generated Content folder to Drive
python3 .claude/scripts/google/google_drive.py upload-folder \
  "/path/to/Generated Content_2026-02-11_14:30" \
  <parent_folder_id> \
  --recursive
```

| Scenario | Action |
|----------|--------|
| Source is local (e.g., `/tmp/...`) | Upload to appropriate `Content/MM.YYYY/[topic]/` folder |
| Source is on Drive | Already persisted via path - verify folder exists |
| Test mode (`--test`) | Skip upload (test data only) |

**Output**: Drive folder ID and link are printed. Record in manifest if needed.

## Output Structure

Every content piece lives in its own **meaningfully-named subfolder**. The top level contains only `_manifest.json`.

Folder names follow the pattern: `[topic-slug]-[content-type]` (e.g., `why-agents-need-memory-linkedin-post`).

Long-form types (linkedin_post, blog_post, newsletter) include an `images/` subfolder with 3 cinematic-lifestyle title images.

```
[Folder]/
├── transcript.md                                      # Source (READ-ONLY)
└── Generated Content_2026-02-04_09:25:13/             # Timestamped output folder
    ├── _manifest.json                                 # Job tracking (only top-level file)
    ├── why-agents-need-memory-linkedin-post/           # Long-form: post + images
    │   ├── post.md
    │   └── images/
    │       ├── title_01.png
    │       ├── title_02.png
    │       └── title_03.png
    ├── context-rot-kills-performance-linkedin-post/
    │   ├── post.md
    │   └── images/
    │       ├── title_01.png
    │       ├── title_02.png
    │       └── title_03.png
    ├── sovereign-ai-infrastructure-twitter-thread/     # Short-form: content only
    │   └── thread.md
    ├── deploy-departments-newsletter/                  # Long-form: post + images
    │   ├── post.md
    │   └── images/
    │       ├── title_01.png
    │       ├── title_02.png
    │       └── title_03.png
    ├── agent-memory-patterns-community-post/           # Short-form
    │   └── post.md
    ├── trinity-sovereignty-text-post/                  # Short-form
    │   └── post.md
    ├── four-pillars-infrastructure-linkedin-carousel/  # Carousel: PDFs + images + text
    │   ├── post.md
    │   ├── carousel.pdf
    │   ├── carousel_dark.pdf
    │   ├── carousel_images/
    │   │   └── slide_*.jpg
    │   └── carousel_images_dark/
    │       └── slide_*.jpg
    └── context-window-degradation-blog-post/           # Long-form: JSON + images
        ├── post.json
        └── images/
            ├── title_01.png
            ├── title_02.png
            └── title_03.png
```

## Manifest Schema

The `_manifest.json` file tracks:
- Source info (transcript path, word count, processed timestamp)
- Extracted insights with scores
- Generated content file links
- Pipeline status history
- Statistics (content counts by type)
- Metadata (the knowledge base agent usage, TOV profiles used)

## Testing

```bash
# Run test with sample transcript
python3 .claude/scripts/repurpose/repurpose.py --test

# Check test output
ls -la test_output/Generated\ Content/
```

## Configuration

Check current config:
```bash
python3 .claude/scripts/repurpose/repurpose.py --config
```

## the knowledge base agent Integration

By default, the pipeline attempts to enrich content with the knowledge base agent perspectives. Use `--no-knowledge_base` flag to skip enrichment for a single run.

## Module Structure

```
.claude/scripts/repurpose/
├── repurpose.py          # Main entry point
├── config.py             # Configuration management
├── manifest.py           # File-based job tracking
├── extraction.py         # Insight extraction via Gemini
├── generators/           # Content generators
│   ├── __init__.py       # Generator registry
│   ├── base.py           # Shared utilities
│   ├── linkedin_post.py
│   ├── twitter_thread.py
│   ├── newsletter.py
│   ├── community_post.py
│   ├── text_post.py
│   ├── carousel.py
│   └── blog_post.py
└── utils/                # Utility modules
    ├── __init__.py
    ├── feedback.py       # Feedback processing
    ├── tov.py            # TOV profile loading
    ├── knowledge_base.py      # the knowledge base agent integration
    ├── apitemplate.py    # Carousel PDF generation
    ├── cloudconvert.py   # PDF to image conversion
    └── midjourney.py     # Background image generation
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "transcript.md not found" | Missing source file | Add transcript to folder |
| "GEMINI_API_KEY not set" | Missing API key | Add key to .env |
| "Extraction failed" | AI API error | Check API quota/key |
| "No insights extracted" | Poor transcript | Check transcript quality |
| "SKIP: Failed to generate Midjourney image" | LegNext API error | Check LEGNEXT_API_KEY |
| "SKIP: Failed to generate light/dark PDF" | APITemplate error | Check APITEMPLATE_API_KEY |
| "Warning: Failed to convert PDF to images" | CloudConvert error | Check CLOUDCONVERT_API_KEY (carousel continues without images) |

## Carousel Pipeline

The carousel generator has a multi-step pipeline that requires external services:

1. **Generate image prompt** - Gemini generates a Midjourney prompt from the insight
2. **Generate Midjourney image** - LegNext API generates 4 images, selects index #1
3. **Generate carousel JSON** - Gemini creates slide content
4. **Generate light theme PDF** - APITemplate.io renders PDF with template `c8877b23e275116a`
5. **Generate dark theme PDF** - APITemplate.io renders PDF with template `d1677b23e271267e`
6. **Convert light PDF to images** - CloudConvert converts PDF to individual JPG slides
7. **Convert dark PDF to images** - CloudConvert converts PDF to individual JPG slides
8. **Save post text** - Pure accompanying text saved to markdown

**Retry Logic:** Image generation and PDF generation retry up to 3 times with 15-second cooldown between attempts.

**Timeouts:** Image generation: 5 min, PDF generation: 2 min, PDF-to-image conversion: 5 min, Total pipeline: 20 min.

**Failure Behavior:**
- If PDF generation fails, the entire carousel is skipped (no partial output)
- If PDF-to-image conversion fails, the carousel continues with PDFs only (images are optional)

## Blog Post Generator

The blog post generator creates SEO-optimized articles for your website. Unlike other generators, it decides which insights are blog-worthy.

**Output:** Single JSON file per blog post (`blog_post_001.json`)

**JSON Structure:**
```json
{
  "slug": "context-window-degradation",
  "title": "Why your AI gets dumber over time",
  "pageTitle": "Why your AI gets dumber over time | Ability AI",
  "category": "AI Implementation",
  "introduction": "150-160 char meta description",
  "fullContent": "Markdown content (800+ words)",
  "featuredImage": {
    "description": "Catchy 2-4 word thumbnail headline"
  }
}
```

**Categories:** AI Strategy, AI Implementation, Case Study, How-To, Industry Insights, AI Governance, Automation, E-commerce, HR & Recruiting, Customer Support, Marketing, Company News

**Content Depth:**
- Standard: 800-1000 words
- Pillar: 1200+ words (AI decides based on insight depth)

**Skip Behavior:** If an insight is not blog-worthy (e.g., too short, better for social media), the generator skips it and no file is created for that insight.

## Architecture

Native Python pipeline (replaced N8N-based CEO Content Engine):
- File-based tracking (`_manifest.json`) instead of Supabase
- TOV profiles from Google Drive with 24h local caching
- the knowledge base agent integration enabled by default (use `--no-knowledge_base` to skip)
- Pure Python implementation (no external workflow dependency)

## Best Practices

1. **Always verify transcript.md exists** before running
2. **Use --test mode** for development
3. **Check --config** to verify API keys are set
4. **Review _manifest.json** to track pipeline status
5. **Use --extract then --generate** for staged processing

## Completion Checklist

- [ ] Transcript.md exists and is readable
- [ ] Configuration verified (API keys set)
- [ ] Insights extracted (3-5 actionable insights)
- [ ] the knowledge base agent enrichment applied (unless --no-knowledge_base)
- [ ] Content generated for all requested types
- [ ] All content in meaningfully-named subfolders
- [ ] 3 title images generated per long-form post (linkedin_post, blog_post, newsletter)
- [ ] _manifest.json updated with status and subfolder references
- [ ] Top-level Generated Content folder contains only _manifest.json and subfolders
- [ ] **Generated Content uploaded to Google Drive** (unless --test)
- [ ] **Drive folder link provided to user**
- [ ] Content library updated with repurposing stats (if video tracked)

## Error Recovery

If pipeline fails mid-execution:

1. **Check manifest status:**
   ```bash
   cat "[folder]/Generated Content_*/_manifest.json" | jq '.status'
   ```

2. **Resume from last stage:**
   - If extraction failed: Re-run `--extract`
   - If generation failed: Re-run `--generate` (uses existing insights)

3. **Common issues:**
   - API quota exceeded: Wait and retry
   - Carousel PDF failed: Content continues without carousel
   - the knowledge base agent timeout: Re-run with `--no-knowledge_base` or retry
