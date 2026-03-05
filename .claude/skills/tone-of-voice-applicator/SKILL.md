---
name: tone-of-voice-applicator
description: Apply the creator's brand voice profiles to content. Use when writing social posts, videos, newsletters, or any public content. Ensures consistent brand voice across platforms.
allowed-tools: Bash, Read, Write
---

# Tone of Voice Applicator

Apply the creator's brand voice profiles to ensure consistent messaging across all platforms.

## Quick Start

**Download and read a tone profile:**
```bash
bash ~/.claude/skills/tone-of-voice-applicator/scripts/get_profile.sh twitter
```

**Available profiles:**
- `twitter` - Concise, punchy, thread-friendly
- `linkedin` - Professional but opinionated, longer-form
- `heygen` - Conversational video scripts (30-sec max)
- `text_post` - General social media text
- `newsletter` - Weekly newsletter style
- `community` - Slack/Discord community posts
- `carousel` - LinkedIn/Instagram carousel slides
- `longform` - YouTube descriptions, blog posts

## Profile IDs (Google Drive)

| Profile | File ID |
|---------|---------|
| Twitter | `YOUR_TWITTER_TOV_ID` |
| LinkedIn | `YOUR_LINKEDIN_TOV_ID` |
| HeyGen Video | `YOUR_HEYGEN_TOV_ID` |
| Text Post | `YOUR_TEXT_POST_TOV_ID` |
| Newsletter | `YOUR_NEWSLETTER_TOV_ID` |
| LongForm | `YOUR_LONGFORM_TOV_ID` |
| Community Post | `YOUR_COMMUNITY_TOV_ID` |
| Carousel | `YOUR_CAROUSEL_TOV_ID` |

## Usage Pattern

1. **Get the profile** for your target platform
2. **Read the guidelines** in the downloaded file
3. **Apply the voice** to your content
4. **Verify compliance** with brand standards

## Core Brand Elements

### Tone Characteristics
- **Direct** - No hedging, no "I think maybe"
- **Opinionated** - Strong takes backed by experience
- **Technical but accessible** - Deep knowledge, clear explanations
- **Anti-hype** - Call out shallow trends, advocate for substance

### Style Rules
- Use hyphens (-) not em-dashes (-)
- No excessive emojis (1-2 max per post)
- Lead with insight, not promotion
- First-person voice ("I built..." not "We built...")

### Platform-Specific Adaptations

**Twitter:**
- 280 char limit awareness
- Thread-friendly (1/7, 2/7 format)
- Hook in first tweet
- Call-to-action in last tweet

**LinkedIn:**
- Longer paragraphs OK
- Professional context
- Can reference company/role
- More explanatory tone

**Video (HeyGen):**
- 30 seconds max
- Conversational, like talking to a friend
- One clear point per video
- End with curiosity hook

For detailed guidelines, see [profiles/](profiles/) after downloading.
