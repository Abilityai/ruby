---
name: heygen-script-writer
description: Write 30-second avatar video scripts using the creator's voice profile. Use when creating HeyGen videos, AI shorts, or talking-head content.
allowed-tools: Bash, Read, Write
---

# HeyGen Script Writer

Create engaging 30-second video scripts for the creator's HeyGen avatar.

## Quick Start

**Generate a script from a topic:**
```bash
python3 ~/.claude/skills/heygen-script-writer/scripts/generate_script.py "Why context engineering matters more than prompt engineering"
```

## Constraints

| Parameter | Value |
|-----------|-------|
| **Max duration** | 30 seconds |
| **Word count** | 75-85 words |
| **Avatar ID** | `${HEYGEN_AVATAR_ID}` |
| **Voice ID** | `${HEYGEN_VOICE_ID}` |
| **Style** | Casual, conversational |

## Script Structure

```
[HOOK - 5 sec, ~15 words]
Surprising statement or question that stops the scroll.

[CONTEXT - 8 sec, ~25 words]
Set up the problem or misconception.

[INSIGHT - 12 sec, ~35 words]
Deliver the key insight or contrarian take.

[CURIOSITY HOOK - 5 sec, ~10 words]
End with intrigue, not a hard CTA.
```

## Voice Guidelines

### DO:
- Start mid-thought ("Here's the thing about...")
- Use conversational contractions ("don't", "won't", "I've")
- Include one specific example or number
- End with curiosity, not commands

### DON'T:
- Start with "Hey everyone" or greetings
- Use corporate speak ("leverage", "synergize")
- Include calls-to-action ("subscribe", "follow")
- Exceed 85 words (will feel rushed)

## Example Scripts

**Topic: AI Agents**
```
Here's what nobody tells you about AI agents.

The frameworks don't matter. LangChain, CrewAI, AutoGen -
they're all just scaffolding.

What actually matters? Context architecture. How you feed
information to the model. Get that wrong, and your agent
hallucinates. Get it right, and suddenly you have something
that actually works.

I've been building these for two years. The pattern is
always the same.
```
(78 words, ~28 seconds)

**Topic: Deep vs Shallow Agents**
```
Most AI agents are shallow. They look impressive in demos
but fail in production.

Deep agents are different. They have memory that persists.
They improve from feedback. They know when to ask for help
instead of guessing.

The difference isn't the model - GPT-4 powers both. It's
the architecture around it. Four components separate the
two.

I call them the Four Pillars.
```
(68 words, ~25 seconds)

## Content Pillars for Scripts

Match scripts to the creator's content pillars:

1. **Deep Agent Architecture** - Four Pillars, memory, context
2. **AI Adoption Psychology** - Why teams resist AI
3. **Shallow vs Deep** - Call out hype, define real agents
4. **Production Patterns** - LATS, orchestrator-worker
5. **Founder Lessons** - Building with Deep Agents

## Hook Types (3S+2F)

- **Scary** - "Your AI agent is lying to you"
- **Strange** - "I let my agent fire itself"
- **Sexy** - "This one pattern 10x'd my output"
- **Free Value** - "The 4 components every agent needs"
- **Familiar** - "Remember when we thought prompts were enough?"

## Output Format

Scripts should be saved with metadata:
```
---
topic: [topic]
pillar: [content pillar]
hook_type: [scary|strange|sexy|free_value|familiar]
word_count: [count]
estimated_duration: [seconds]
---

[Script text here]
```
