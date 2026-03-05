# Ruby - Content Management Agent for Claude Code

Ruby is an autonomous content management agent built on [Claude Code](https://docs.anthropic.com/en/docs/claude-code). It handles content generation, repurposing, scheduling, and multi-platform publishing - so you can focus on creating long-form content.

## What Ruby Does

- **Repurposes video content** - Takes YouTube video transcripts and generates LinkedIn posts, Twitter threads, newsletters, blog posts, Instagram carousels, and more
- **Manages multi-platform publishing** - Schedules and posts to Twitter/X, LinkedIn, Instagram, TikTok, YouTube, Threads, Bluesky, Facebook, and Pinterest via Blotato API
- **Produces AI videos** - Creates avatar videos (HeyGen), AI-generated clips (Google Veo 3.1), and handles vertical conversion with captions (Creatomate)
- **Generates images** - YouTube thumbnails, Instagram covers, explanatory diagrams, and social graphics via Gemini Image API
- **Tracks content workflow** - Manages article lifecycle (draft -> review -> approved -> published) and YouTube video repurposing progress
- **Engages on Twitter** - Finds viral reply opportunities, responds to mentions, manages reply queues
- **Maintains brand voice** - Applies platform-specific tone of voice profiles to all content

## Architecture

Ruby uses a **playbook pattern** - each capability is a self-contained skill with explicit state management. Skills range from fully autonomous (scheduled, no human input) to gated (pauses for approval at key checkpoints) to manual (only runs when invoked).

```
ORCHESTRATOR (top-level)     ->  /weekly-content-cycle
|- GATED (needs approval)    ->  /create-article, /repurpose
|   '- WORKER (atomic)       ->  /knowledge-base-query, /tone-of-voice
'- AUTONOMOUS (unattended)   ->  /content-library, /schedule-tracker
```

Every skill follows the transactional pattern: **READ STATE -> PROCESS -> WRITE STATE**

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation.

## Quick Start

1. **Clone and configure**
   ```bash
   git clone https://github.com/abilityai/ruby.git
   cd ruby
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Initialize**
   ```bash
   bash init.sh
   ```

3. **Customize**
   ```bash
   cp CLAUDE.md.template CLAUDE.md
   # Edit CLAUDE.md - replace all {{PLACEHOLDERS}} with your values
   ```

4. **Run**
   ```bash
   claude
   ```

See [SETUP.md](SETUP.md) for detailed configuration instructions.

## Skills Overview

### Content Creation
| Skill | Description |
|-------|-------------|
| `/create-article` | Long-form article generation via knowledge base agent |
| `/create-video` | Complete explainer videos from AI scenes |
| `/create-heygen-video` | HeyGen avatar + Creatomate pipeline |
| `/generate-image` | AI image generation (Imagen 4 Ultra) |

### Publishing & Scheduling
| Skill | Description |
|-------|-------------|
| `/post-now` | Post immediately to any platform |
| `/schedule-post` | Schedule future posts |
| `/repurpose` | Full repurposing pipeline (transcript to multi-platform) |

### Video Processing
| Skill | Description |
|-------|-------------|
| `/thumbnails` | Generate 15 AI YouTube thumbnails |
| `/edit-video` | Semantic video editing with B-roll |
| `/analyze-video` | Deep content analysis with timestamps |

### Content Tracking
| Skill | Description |
|-------|-------------|
| `/content-library` | Track articles and video repurposing |
| `/schedule-tracker` | Monitor post scheduling status |

Run `/help` inside Claude Code to see all available skills.

## Integrations

Ruby connects to external services via MCP servers and API scripts. All credentials are managed through `.env` - no hardcoded secrets.

| Service | Purpose | Required |
|---------|---------|----------|
| **Twitter/X API** | Posting, engagement, analytics | For Twitter features |
| **Blotato** | Multi-platform posting | For scheduling |
| **HeyGen** | AI avatar videos | For video production |
| **Cloudinary** | Media hosting | For image/video hosting |
| **Google Gemini** | Image generation, content analysis | For AI features |
| **Metricool** | Social analytics | For tracking |
| **Google Drive** | Content storage | For file management |
| **Creatomate** | Video conversion + captions | For video processing |
| **GoFile** | Temporary media hosting | For quick uploads |
| **ElevenLabs** | Voice cloning + TTS | For voiceovers |
| **Giphy** | GIF search | For social content |

## Project Structure

```
ruby/
|- CLAUDE.md.template        # Agent instructions (customize this)
|- .env.example              # Environment variable template
|- .mcp.json.template        # MCP server configuration template
|- init.sh                   # Initialization script
|- .claude/
|   |- skills/               # 25+ playbook skills
|   |- agents/               # Sub-agent definitions
|   |- scripts/              # Python/bash automation scripts
|   |- resources/            # Reference documentation
|   '- memory/               # State files (schedule, content library)
'- youtube/
    '- youtube-mcp-server/   # YouTube MCP server
```

## Customization

Ruby is designed to be forked and customized:

1. **CLAUDE.md** - Replace placeholders with your brand, products, and content strategy
2. **Tone of Voice profiles** - Create your own in Google Drive `Prompts/` folder
3. **Content pillars** - Define your own topic categories
4. **Skills** - Add new skills following the playbook pattern (see ARCHITECTURE.md)
5. **Google Drive mapping** - Update `.claude/resources/google_drive_folders.md` with your folder IDs

## Knowledge Base Agent (Optional)

Ruby can partner with a knowledge base agent for research and perspective. Configure the path in CLAUDE.md or remove the integration sections if not using one.

## License

[MIT](LICENSE)
