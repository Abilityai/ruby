---
name: analyze-video
description: Transcribe and analyze video content - returns timestamps, segments, topics, and keyword matches. Use for understanding video structure before editing.
allowed-tools: Bash, Read, Write
---

# /analyze-video

Transcribe and analyze video content - returns timestamps, segments, topics.

**Self-sufficient**: Transcribes videos directly using Whisper.

## Usage

```
/analyze-video [video_path] [optional: specific query]
```

**Examples:**
```
/analyze-video /path/to/video.mp4
/analyze-video /path/to/video.mp4 "Find moments about AI agents"
```

## Workflow

### Step 1: Transcribe

```bash
python3 .claude/scripts/video/transcribe_video.py "$VIDEO_PATH" -m base -o /tmp/transcript.json
```

### Step 2: Display Results

```bash
python3 -c "
import json
data = json.load(open('/tmp/transcript.json'))
print(f'Duration: {data[\"duration_formatted\"]}')
print(f'Segments: {data[\"segment_count\"]}')
print(f'Topics: {\", \".join(data[\"topics\"][:10])}')
print()
print('=== Transcript ===')
for seg in data['segments']:
    print(f'[{seg[\"start_formatted\"]}] {seg[\"text\"]}')"
```

### Step 3: Keyword Search (if query provided)

```bash
python3 .claude/scripts/video/parse_transcript.py /tmp/transcript.json -k "keyword1" "keyword2"
```

Returns `keyword_matches` with timestamps where each keyword appears.

### Step 4: Visual Analysis (optional, for complex queries)

```bash
python3 .claude/scripts/video/analyze_video_gemini.py "$VIDEO_PATH" "$QUERY" -o /tmp/analysis.json
```

Use Gemini when you need:
- Scene detection (visual changes)
- Non-verbal content analysis
- Complex semantic queries

## Output Format

**Transcription output:**
```json
{
  "segments": [
    {
      "start": 5.0,
      "end": 12.0,
      "text": "Let's talk about AI agents",
      "start_formatted": "00:05.000",
      "end_formatted": "00:12.000"
    }
  ],
  "topics": ["AI", "agents", "technology"],
  "duration_seconds": 172.5,
  "duration_formatted": "02:52.500",
  "segment_count": 16
}
```

**With keyword search:**
```json
{
  "keyword_matches": [
    {
      "keyword": "ai",
      "timestamp": "00:05.000",
      "start_seconds": 5.0,
      "context": "Let's talk about AI agents"
    }
  ]
}
```

## Transcription Models

| Model | Speed | Accuracy |
|-------|-------|----------|
| `tiny` | ~10x realtime | Basic |
| `base` | ~1x realtime | Good (default) |
| `medium` | ~0.5x realtime | Better |
| `large` | ~0.25x realtime | Best |

## Notes

- Whisper required: `pip install openai-whisper`
- Transcription runs locally
- Output is JSON for further processing
- Use `--format transcript` for human-readable output
