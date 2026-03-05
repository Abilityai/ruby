# Setup Guide

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and configured
- Python 3.10+
- Node.js 18+ (for MCP servers)
- `ffmpeg` (for video processing)
- `jq` (for JSON processing in scripts)
- `envsubst` (part of `gettext` - for template generation)

## Step 1: Clone and Configure Environment

```bash
git clone https://github.com/abilityai/ruby.git
cd ruby
cp .env.example .env
```

Edit `.env` and add your API keys. See the API key sections below for where to get each one.

## Step 2: Initialize

```bash
bash init.sh
```

This script:
1. Validates your `.env` credentials
2. Generates `.mcp.json` from the template (substitutes your env vars)
3. Generates agent-level MCP configs

## Step 3: Customize CLAUDE.md

```bash
cp CLAUDE.md.template CLAUDE.md
```

Open `CLAUDE.md` and replace all `{{PLACEHOLDER}}` values. Required fields:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{USER_NAME}}` | Your name | `Jane Smith` |
| `{{AGENT_LOCATION}}` | Absolute path to this repo | `/home/jane/agents/ruby` |
| `{{YOUTUBE_CHANNEL_NAME}}` | Your channel name | `Jane Smith (@janesmith)` |
| `{{YOUTUBE_CHANNEL_ID}}` | Channel ID (starts with UC) | `UCxxxxxxxxxxxxxxxxxxxxxxx` |
| `{{CURRENT_SUBSCRIBERS}}` | Current sub count | `5K` |
| `{{SUBSCRIBER_GOAL}}` | Target sub count | `10K` |
| `{{HEYGEN_AVATAR_ID}}` | HeyGen avatar ID | Get from HeyGen dashboard |
| `{{HEYGEN_VOICE_ID}}` | HeyGen voice ID | Get from HeyGen dashboard |
| `{{ELEVENLABS_VOICE_ID}}` | ElevenLabs voice ID | Get from ElevenLabs dashboard |
| `{{METRICOOL_BLOG_ID}}` | Metricool brand ID | Get from Metricool settings |
| `{{PRIMARY_PRODUCT}}` | Your product name | `MyApp` |
| `{{PRIMARY_PRODUCT_URL}}` | Product URL | `https://myapp.com` |
| `{{PRIMARY_PRODUCT_TAGLINE}}` | One-line description | `The best app for X` |

## Step 4: Set Up Google Drive (Optional)

If you use Google Drive for content storage:

1. Create a Google Cloud project and enable the Drive API
2. Create a service account and download the credentials JSON
3. Place it at `.claude/scripts/google/credentials.json`
4. Share your Google Drive folders with the service account email
5. Update `.claude/resources/google_drive_folders.md` with your folder IDs

## Step 5: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Step 6: Set Up YouTube MCP Server (Optional)

```bash
cd youtube/youtube-mcp-server
cp credentials.yml.example credentials.yml
# Edit credentials.yml with your YouTube API key
pip install -r requirements.txt
cd ../..
```

## Step 7: Run

```bash
claude
```

Ruby will read `CLAUDE.md` and be ready to work. Try:
- `/content-library` - See content status
- `/schedule-tracker` - Check post schedule
- `/repurpose /path/to/video/folder` - Repurpose a video

---

## API Key Guide

### Twitter/X API (for posting and engagement)
1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Create a project with Read and Write permissions
3. Generate API Key, API Secret, Access Token, and Access Token Secret
4. Add to `.env` as `TWITTER_API_KEY`, `TWITTER_API_SECRET_KEY`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`

### HeyGen (for AI avatar videos)
1. Sign up at [heygen.com](https://heygen.com)
2. Go to Settings -> API -> Generate API Key
3. Note your avatar ID and voice ID from the Avatars page
4. Add to `.env` as `HEYGEN_API_KEY`

### Cloudinary (for media hosting)
1. Sign up at [cloudinary.com](https://cloudinary.com)
2. Go to Dashboard -> copy Cloud Name, API Key, API Secret
3. Add to `.env` as `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`

### Google Gemini (for image generation and AI)
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Get an API key
3. Add to `.env` as `GEMINI_API_KEY`

### Blotato (for multi-platform posting)
1. Sign up at [blotato.com](https://blotato.com)
2. Connect your social accounts
3. Get API key from Settings
4. Note account IDs for each connected platform
5. Add to `.env` as `BLOTATO_API_KEY` and `BLOTATO_*_ID` values

### Metricool (for analytics)
1. Sign up at [metricool.com](https://metricool.com)
2. Go to Settings -> API
3. Add to `.env` as `METRICOOL_USER_TOKEN` and `METRICOOL_USER_ID`

### GoFile (for temporary media hosting)
1. Sign up at [gofile.io](https://gofile.io)
2. Go to Account -> API Token
3. Create a root folder for Ruby
4. Add to `.env` as `GOFILE_API_TOKEN`, `GOFILE_ACCOUNT_ID`, `GOFILE_ROOT_FOLDER`

### Giphy (for GIF search)
1. Go to [developers.giphy.com](https://developers.giphy.com)
2. Create an app and get API key
3. Add to `.env` as `GIPHY_API_KEY`

### ElevenLabs (for voiceovers)
1. Sign up at [elevenlabs.io](https://elevenlabs.io)
2. Clone your voice or use a preset
3. Get API key from Profile -> API Key
4. Add to `.env` as `ELEVENLABS_API_KEY`

### Creatomate (for video processing)
1. Sign up at [creatomate.com](https://creatomate.com)
2. Get API key from Account Settings
3. Add to `.env` as `CREATOMATE_API_KEY`

---

## Optional Integrations

### Knowledge Base Agent
If you have a separate knowledge base agent (like the knowledge base agent), set `{{KNOWLEDGE_BASE_AGENT_PATH}}` in CLAUDE.md to its location. Ruby will call it for research and perspective generation.

### Tone of Voice Profiles
Create tone of voice profile documents in your Google Drive `Prompts/` folder. Ruby uses these to match your brand voice per platform. Templates:
- `Twitter_Tone_of_Voice_Profile.md`
- `LinkedIn_Tone_of_Voice_Profile.md`
- `HeyGen_Video_Tone_of_Voice_Profile.md`
- `Newsletter_Tone_of_Voice_Profile.md`
- `LongForm_Tone_of_Voice_Profile.md`

### Branded Video Assets
Place intro/outro video files in Google Drive `Intro_Templates/` folder and update the path mapping in `.claude/resources/google_drive_folders.md`.
