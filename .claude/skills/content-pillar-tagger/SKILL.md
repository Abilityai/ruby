---
name: content-pillar-tagger
description: Tag content with the creator's 5 content pillars and 3S+2F hook types. Use when categorizing, scheduling, or analyzing content for consistent taxonomy.
allowed-tools: Read, Write
---

# Content Pillar Tagger

Categorize content using the creator's content strategy framework.

## Quick Reference

**Tag any content piece with:**
1. One primary **Content Pillar**
2. One **Hook Type** (3S+2F framework)

## Content Pillars

### 1. Deep Agent Architecture (PRIMARY)
The Four Pillars of autonomous AI agents:
- **Planning** - How agents break down and sequence tasks
- **Delegation** - Multi-agent orchestration patterns
- **Memory** - Persistent context, learning from experience
- **Context Engineering** - Feeding the right information to models

**Keywords:** agents, architecture, context, memory, planning, orchestration, autonomous

### 2. AI Adoption Psychology
Why organizations struggle to adopt AI:
- Enterprise barriers and resistance
- The "identity gap" - who am I if AI does my job?
- Change management for AI transformation
- Individual vs. organizational adoption

**Keywords:** adoption, psychology, enterprise, resistance, identity, transformation

### 3. Shallow vs Deep
Calling out hype, defining real capabilities:
- Demo-ware vs production-ready
- Benchmarks vs real-world performance
- Marketing claims vs technical reality
- Taxonomy of agent capabilities

**Keywords:** shallow, deep, hype, reality, production, demo, benchmarks

### 4. Production Patterns
Technical implementation patterns:
- LATS (Language Agent Tree Search)
- Orchestrator-worker architectures
- Sentinel agents for monitoring
- Error recovery and self-healing

**Keywords:** patterns, LATS, orchestrator, worker, sentinel, production, implementation

### 5. Founder Lessons
Building companies with Deep Agents:
- Lessons from Trinity development
- Scaling agent infrastructure
- Team structures for AI-native companies
- Product decisions and tradeoffs

**Keywords:** founder, startup, Trinity, building, lessons, scaling

## Hook Types (3S+2F Framework)

### Scary (Fear)
Triggers loss aversion and urgency.
- "Your AI agent is lying to you"
- "Why 75% of AI projects fail"
- "The hidden cost of shallow agents"

### Strange (Curiosity)
Unexpected or counterintuitive takes.
- "I let my agent fire itself"
- "Why I stopped using frameworks"
- "The problem with being too smart"

### Sexy (Desire)
Aspirational outcomes and benefits.
- "How I 10x'd my output with one pattern"
- "The architecture behind my viral video"
- "Building agents that improve themselves"

### Free Value (Gratitude)
Actionable insights given freely.
- "The 4 components every agent needs"
- "My complete context engineering checklist"
- "How to debug hallucinating agents"

### Familiar (Trust)
Relatable experiences and shared struggles.
- "Remember when we thought prompts were enough?"
- "Every developer's first agent fails the same way"
- "The moment I realized frameworks weren't the answer"

## Tagging Format

When tagging content, use this structure:

```json
{
  "content_pillar": "Deep Agent Architecture",
  "hook_type": "strange",
  "pillar_keywords": ["context", "memory", "planning"],
  "secondary_pillar": "Production Patterns"  // optional
}
```

## Examples

| Content | Pillar | Hook |
|---------|--------|------|
| "Why your agent hallucinates" | Deep Agent Architecture | scary |
| "I built Trinity in 6 months" | Founder Lessons | familiar |
| "The LATS pattern explained" | Production Patterns | free_value |
| "Enterprise AI is failing" | AI Adoption Psychology | scary |
| "Demos lie, production doesn't" | Shallow vs Deep | strange |

## Usage in schedule.json

Every scheduled post MUST include:
```json
{
  "content_pillar": "Deep Agent Architecture",
  "hook_type": "strange",
  // ... other fields
}
```

## Analytics Correlation

Track which combinations perform best:
- **Pillar + Hook** → Engagement rate
- **Platform + Pillar** → Best fit analysis
- **Hook type** → Click-through rates

Use Metricool MCP to correlate tags with performance data.
