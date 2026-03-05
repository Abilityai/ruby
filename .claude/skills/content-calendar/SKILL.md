---
name: content-calendar
description: Manages content production pipeline and publishing schedule. Use when user asks to "plan content", "schedule posts", "check calendar", "what's scheduled", or needs content pipeline management.
---

# Content Calendar Skill

Manages the content production pipeline and publishing schedule.

## Content Types

| Type | Platform | Frequency | Lead Time |
|------|----------|-----------|-----------|
| Tweet | Twitter | 1-2/day | Same day |
| Thread | Twitter | 1-2/week | 2 days |
| Video | Twitter/LinkedIn | 1/week | 5 days |
| Blog | Website | 1/month | 1 week |
| Reply | Twitter | 5-10/day | Real-time |

## Content Angles

1. **org-chart** - Visual org chart for agents
2. **persistence** - Agents remember everything
3. **scalability** - Deploy departments, not agents
4. **permissions** - Role-based access control
5. **cloud** - Sovereign cloud infrastructure
6. **pricing** - Cost efficiency vs competitors
7. **security** - Enterprise-grade security
8. **audit** - Full audit trails
9. **governance** - Approval gates and workflows
10. **multi-agent** - Orchestration capabilities

## Optimal Schedule

### By Day (EST)
| Day | Best Time | Quality |
|-----|-----------|---------|
| Monday | 10 AM | Good |
| Tuesday | 9 AM | Strong |
| Wednesday | 9 AM | Best |
| Thursday | 9 AM | Strong |
| Friday | 10 AM | Good |
| Weekend | 11 AM | Low priority |

### First 30 Minutes Rule
Early engagement determines viral potential. For important content:
- Creator available to engage
- Team notified to boost
- Monitor and respond quickly

## Pipeline Stages

```
Ideas → Draft → Review → Approved → Scheduled → Published → Analyzed
```

### Stage Definitions
- **Ideas**: Raw content concepts
- **Draft**: Written, needs polish
- **Review**: Ready for approval
- **Approved**: Cleared for posting
- **Scheduled**: Queued with time
- **Published**: Live
- **Analyzed**: Performance reviewed

## Calendar File Format

```yaml
# outputs/schedules/week-2026-02-03.yaml
week_of: "2026-02-03"
content:
  - date: "2026-02-03"
    time: "10:00"
    timezone: "EST"
    account: "trinity"
    type: "tweet"
    angle: "persistence"
    content: "Your AI agents forget everything..."
    media: null
    status: "scheduled"
```

## Metrics

- `content_published`: Total posts this period
- `content_queued`: Posts waiting to publish
- `content_gap`: Days without planned content
- `angle_coverage`: % of angles used this week
