# Playbook Architecture

Ruby's skills follow a **playbook pattern** - structured, transactional processes with explicit state management.

## Core Concepts

### Playbook = Skill

Same thing, different perspective:
- **Skill**: Claude Code term (SKILL.md file)
- **Playbook**: Business term ("run the content playbook")

### Automation Levels

| Level | Keyword | Runs When | Human Role |
|-------|---------|-----------|------------|
| **Autonomous** | `autonomous` | On schedule | None |
| **Gated** | `gated` | Schedule/trigger, pauses at gates | Approve at checkpoints |
| **Manual** | `manual` | Only when invoked | Full control |

### Playbook Hierarchy

```
ORCHESTRATOR PLAYBOOKS (top-level processes)
├── Call worker playbooks in sequence
├── Define approval gates
├── Track overall progress
└── Run on schedule or manually

WORKER PLAYBOOKS (atomic operations)
├── Do one thing well
├── Called by orchestrators
├── No scheduling, no gates
└── Return success/failure
```

---

## State Management

Every playbook behaves like a database transaction:

```
READ STATE → PROCESS → WRITE STATE
```

### State Dependencies Table (Required)

Every playbook must declare what it reads and writes:

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Library | `content_library.yaml` | ✓ | ✓ | Content tracking |
| Schedule | `schedule.json` | ✓ | ✓ | Post scheduling |
| Drafts | `Articles/drafts/` | | ✓ | New articles |

### Rules

1. **Read fresh at start** - never rely on stale context
2. **Write explicitly at end** - document every state change
3. **Document recovery** - what to do if playbook fails mid-run

---

## Playbook Structure

```yaml
---
name: playbook-name
description: When to use (triggers Claude's skill loading)
automation: gated                    # autonomous | gated | manual
schedule: "0 9 * * 1"                # cron (optional)
calls: [child-skill-1, child-skill-2]  # dependencies
allowed-tools: [Read, Write, Bash]
---

# Playbook Name

## Purpose
One sentence describing the outcome.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|

## Process

### Step 1: Read Current State
[Always first - read all state dependencies fresh]

### Step 2-N: [Actions]
[APPROVAL GATE] markers where human input needed

### Step N: Write Updated State
[Always last - save all changes]

## Completion Checklist
- [ ] State read fresh
- [ ] [Task-specific items]
- [ ] State written
- [ ] Changes committed (if applicable)
```

---

## Hierarchies

### Content Production

```
/weekly-content-cycle          [ORCHESTRATOR - scheduled]
│
├─→ /content-library           [worker] check status
│
├─→ /create-article            [GATED]
│   ├─→ /knowledge-base-query       [worker]
│   └─→ /tone-of-voice         [worker]
│
├─→ /repurpose                 [GATED]
│   └─→ /content-pillar-tagger [worker]
│
└─→ /schedule-week             [GATED]
    └─→ /schedule-post         [worker]
```

### Video Production

```
/create-video                  [GATED - needs scene approval]
├─→ /create-veo-video          [worker]
├─→ /edit-video                [GATED - needs edit approval]
│   ├─→ /analyze-video         [worker]
│   └─→ /insert-broll          [worker]
└─→ /upload-media              [worker]
```

### Twitter Engagement

```
/daily-twitter-cycle           [ORCHESTRATOR - scheduled]
├─→ /find-viral-replies        [worker]
├─→ /reply-to-mentions         [worker]
└─→ /post-queued-replies       [GATED - needs reply approval]
```

---

## Approval Gates

Use `[APPROVAL GATE]` markers in gated playbooks:

```markdown
### Step 3: Review Generated Content

[APPROVAL GATE] - Review article before proceeding

Present to user:
- Article title
- Key points
- Word count

Wait for: Approve / Request changes / Abort
```

**Gate placement:**
- Before irreversible actions (publish, send, delete)
- After AI generation, before use
- At major phase transitions

---

## Scheduling

Playbooks can declare schedules in frontmatter:

```yaml
schedule: "0 9 * * 1"    # Every Monday 9am
```

**Common patterns:**
- `0 9 * * *` - Daily 9am
- `0 9 * * 1` - Weekly Monday 9am
- `0 9 1 * *` - Monthly 1st at 9am
- `*/30 * * * *` - Every 30 minutes

Trinity reads these and runs accordingly. Locally, run manually.

---

## Central State Files

| File | Purpose | Updated By |
|------|---------|------------|
| `content_library.yaml` | Article/video workflow | `/content-library` |
| `schedule.json` | Social post scheduling | `/schedule-tracker` |
| `twitter_replies.txt` | Reply queue | `/find-viral-replies` |
| `reply_queue.json` | Pending replies | `/post-queued-replies` |

---

## Converting Existing Skills

To convert a skill to playbook pattern:

1. Add `automation:` to frontmatter
2. Add `## State Dependencies` table
3. Add "Read Current State" as Step 1
4. Add "Write Updated State" as final step
5. Add `## Completion Checklist`
6. Mark `[APPROVAL GATE]` where needed
7. Add `calls:` for child skills
