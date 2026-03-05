# B-Roll Placement Guide for Business & Technology Videos

Guidelines for creating effective B-roll in mid-pace talking-head videos about business, technology, and AI.

---

## When to Insert B-Roll

### High-Priority Moments (Always Consider)

| Trigger | Why | Example |
|---------|-----|---------|
| **Definitions** | Abstract terms need visual anchoring | "AGI is a self-improving system..." |
| **Lists/Frameworks** | Multi-part concepts overwhelm audio-only | "There are four types of memory..." |
| **Comparisons** | Visual contrast clarifies differences | "Unlike a calculator, an AGI has opinions..." |
| **Key Thesis Statements** | Signal importance, aid retention | "My thesis is that AGI isn't a single model..." |
| **Counter-intuitive Claims** | Visual support builds credibility | "The bottleneck isn't capabilities, it's architecture" |

### Medium-Priority Moments

| Trigger | Why |
|---------|-----|
| **Metaphors/Analogies** | Literal visualization strengthens metaphor |
| **Section Transitions** | Visual break signals topic change |
| **Data/Statistics** | Numbers benefit from visual representation |
| **Process Explanations** | Step-by-step flows need visual guide |

### Skip B-Roll When

- Speaker is showing screen/demo (the screen IS the visual)
- Personal stories or emotional moments (maintain eye contact)
- Quick asides or parenthetical comments
- Content already has natural visual interest

---

## B-Roll Duration Guidelines

| Content Type | Duration | Reasoning |
|--------------|----------|-----------|
| Simple concept | 2.5-3.0s | Quick visual anchor |
| Definition/framework | 3.5-4.0s | Time to read/absorb |
| Complex diagram | 4.0-5.0s | Multiple elements to process |
| Comparison (2-panel) | 4.0-4.5s | Time to scan both sides |

**Rule of Thumb**: Match duration to cognitive load. Simple = shorter, complex = longer.

---

## Visual Types by Content

### Schematic Diagrams (Primary for Tech/Business)

Best for: Frameworks, architectures, hierarchies, processes

**Characteristics:**
- Pure black background (#000000)
- White/cyan icons and lines
- Geometric shapes (hexagons, circles, rectangles)
- Connecting lines showing relationships
- NO text labels in image (or minimal)

**When to Use:**
- Explaining system architecture
- Defining multi-component concepts
- Showing relationships between ideas

### Comparison Diagrams

Best for: Before/after, old vs new, wrong vs right

**Layout:**
- Split screen (left = old/wrong, right = new/right)
- Dim/gray for deprecated approach
- Bright cyan for preferred approach
- Visual weight favors the "right" side

**When to Use:**
- Challenging conventional wisdom
- Presenting your thesis vs alternatives
- Showing evolution of thinking

### Flow Diagrams

Best for: Processes, loops, sequences

**Characteristics:**
- Circular for iterative processes
- Linear/horizontal for sequences
- Arrows showing direction
- 3-5 stages maximum

**When to Use:**
- Explaining how something works
- Self-improvement loops
- Decision trees (simplified)

### Hierarchy Diagrams

Best for: Taxonomies, priority stacks, belief systems

**Characteristics:**
- Pyramid (stable base, narrow top)
- Concentric circles (core to periphery)
- Layered bars (most to least)
- Color gradient showing intensity/stability

**When to Use:**
- Values/principles frameworks
- Priority systems
- Conceptual depth layers

### Node/Network Diagrams

Best for: Ecosystems, distributed systems, connections

**Characteristics:**
- Central orchestrator node (brighter)
- Satellite nodes of varying sizes
- Connecting lines with glow effects
- Suggests coordination without rigid hierarchy

**When to Use:**
- Agent ecosystems
- Brain/neural metaphors
- Collaborative systems

---

## Prompt Construction for Nano Banana

### Template Structure

```
Create a [DIAGRAM TYPE] for a tech video B-roll.

CONCEPT: [What the speaker is explaining]

VISUAL STRUCTURE:
- [Layout description]
- [Key elements - max 10]
- [Relationships between elements]

STYLE REQUIREMENTS:
- Pure black background (#000000)
- White (#ffffff) and cyan (#00ffff) only
- No text labels (or minimal - 2-3 words max)
- Clean geometric shapes
- High contrast for video overlay
- 16:9 aspect ratio

The image should explain the concept at a glance without needing to read anything.
```

### Example Prompts

**For a Definition (6-component concept):**
```
Create a schematic diagram for a tech video B-roll.

CONCEPT: AGI definition with 6 components - self-improving, opinionated, memory, goal-oriented, improving, scalable.

VISUAL STRUCTURE:
- 6 hexagonal nodes arranged in a circle
- Each node contains a simple icon (brain, lightbulb, database, target, arrow-up, expand)
- Thin cyan lines connecting all nodes
- Central empty circle (the unified AGI)

STYLE: Pure black background, white/cyan colors, no text, geometric, high contrast.
```

**For a Comparison:**
```
Create a comparison diagram for a tech video B-roll.

CONCEPT: Neutral tool (mirror) vs opinionated system (brain processing)

VISUAL STRUCTURE:
- Split vertically in half
- LEFT: Gray mirror icon, input arrow → output arrow (same direction)
- RIGHT: Glowing cyan brain, input arrow → internal processing → output arrow (transformed)

STYLE: Pure black background, left side dim gray, right side bright cyan, no text.
```

**For a Hierarchy:**
```
Create a pyramid diagram for a tech video B-roll.

CONCEPT: Belief hierarchy - core values (stable) to hypotheses (fluid)

VISUAL STRUCTURE:
- 4-layer pyramid
- Bottom (widest): Solid, stable, white
- Second: Slightly lighter
- Third: Cyan, medium
- Top (narrowest): Bright cyan with small question marks

STYLE: Pure black background, gradient from white (stable) to cyan (fluid), minimal labels.
```

---

## Animation Effects by Content Type

| Content Type | Recommended Effect | Why |
|--------------|-------------------|-----|
| Definitions | `ken_burns_in` | Draws focus inward to concept |
| Processes/Loops | `drift` | Suggests motion/flow |
| Comparisons | `ken_burns_pan` | Guides eye across both sides |
| Hierarchies | `ken_burns_out` | Reveals full structure |
| Networks | `pulse` | Suggests activity/life |
| Scaling concepts | `ken_burns_out` | Emphasizes expansion |

---

## Transition Sound Effects (Whoosh)

Adding a subtle whoosh sound when B-roll appears creates more dynamic, professional transitions.

### Default SFX (Use These)

| SFX Name | Duration | Character | Best For |
|----------|----------|-----------|----------|
| `swoosh_flying` | 0.57s | Quick flying swoosh | Frequent B-rolls, subtle transitions |
| `whoosh_arrow` | 1.10s | Sharp, quick | Definitions, quick points |
| `whoosh_fast_transition` | 1.33s | Classic whoosh | **DEFAULT** - standard B-roll |
| `tech_slide` | 2.26s | Modern UI sound | Tech/software content |
| `whoosh_air` | 2.32s | Soft wind | Natural, gentle transitions |
| `whoosh_swirling` | 2.52s | Circular motion | Process explanations |

### Dramatic SFX (Only When Instructed)

| SFX Name | Duration | Character | Best For |
|----------|----------|-----------|----------|
| `whoosh_epic_trailer` | 3.53s | Cinematic whoosh | Key thesis statements |
| `whoosh_ghostly` | 3.76s | Eerie/mysterious | Dark/cautionary content |
| `impact_epic_trailer` | 4.87s | Epic hit | Major reveals, conclusions |

### When to Use Each

| Content Type | Recommended SFX | Why |
|--------------|-----------------|-----|
| Definitions | `swoosh_flying` | Quick, don't distract |
| Lists/Frameworks | `whoosh_fast_transition` | Standard emphasis |
| Comparisons | `whoosh_arrow` | Sharp contrast |
| Process Explanations | `whoosh_swirling` | Suggests flow |
| Tech/Software | `tech_slide` | Modern feel |
| Section Transitions | `whoosh_air` | Soft break |
| Frequent B-rolls (<20s apart) | `swoosh_flying` | Avoid fatigue |

**Only use dramatic SFX when explicitly requested** for key thesis statements or major impact moments.

### SFX Settings

```json
{
  "transition_sfx": "whoosh_fast_transition",
  "sfx_volume": 0.15,
  "sfx_offset": -0.15
}
```

- **sfx_volume**: 0.0-1.0, default 0.15 (subtle, doesn't overpower speech)
- **sfx_offset**: Seconds before B-roll appears. Default -0.15 (starts 150ms before visual)
- **Variety**: Rotate through `whoosh_fast_transition`, `swoosh_flying`, `sweep_small_fast` for variety

### Consistency Guidelines

- **Within a video**: Use same SFX for similar content types
- **Default choice**: `whoosh_fast_transition` unless there's a reason to vary
- **Density**: If B-rolls are <20s apart, use `swoosh_flying` (shortest)
- **Skip SFX**: For emotional moments or personal stories, no whoosh keeps intimacy

---

## Spacing and Pacing

### Minimum Gap Between B-Rolls

- **15-20 seconds minimum** between B-roll insertions
- Allows viewer to re-engage with speaker
- Prevents visual fatigue

### B-Roll Density by Video Length

| Video Length | B-Roll Count | Average Spacing |
|--------------|--------------|-----------------|
| 2-3 min | 2-3 | ~60s apart |
| 5-7 min | 4-6 | ~60-90s apart |
| 10-15 min | 8-12 | ~60-90s apart |
| 20+ min | 12-18 | ~90-120s apart |

### Clustering

- Group B-roll around conceptual peaks
- Leave breathing room in transitions
- Front-load B-roll in definition-heavy intros

---

## Quality Checklist

Before generating each B-roll:

- [ ] **Relevant moment?** Is this explaining something abstract?
- [ ] **Not over demo?** Speaker is in talking-head mode, not screen sharing?
- [ ] **Clear concept?** Can I describe what this visualizes in one sentence?
- [ ] **Simple composition?** Max 10 visual elements?
- [ ] **No text dependency?** Image works without reading anything?
- [ ] **Brand aligned?** Black background, cyan/white colors?
- [ ] **Appropriate duration?** Matches cognitive complexity?
- [ ] **Good spacing?** At least 15s from previous B-roll?

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Too many B-rolls | Identify top 60% most important moments |
| B-roll over screen demo | Only use during talking-head segments |
| Complex diagrams | Simplify to ONE concept, max 10 elements |
| Text-heavy visuals | Use icons/shapes instead of labels |
| Same animation every time | Vary effects based on content type |
| Literal interpretations | Abstract/schematic > photorealistic |
| Off-brand colors | Stick to black/white/cyan palette |

---

## Reference

- **Nano Banana Best Practices**: `.claude/resources/nano_banana_best_practices.md`
- **Brand Style Guide**: `Prompts/Brand_carousel_styleguide.md`
- **B-Roll Generation Script**: `.claude/scripts/video/generate_broll_image.py`
- **Video Editor Agent**: `.claude/agents/video-editor.md`

---

*Created: January 2026*
*For mid-pace business/technology talking-head videos*
