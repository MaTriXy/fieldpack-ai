# FieldPack AI — Video Script

> Production bible for the 3-minute demo video. Every frame, every word, every second.
> All downstream work (demo backend, Playwright, left-panel app, narration) flows from this document.

---

## Format

- **Duration**: 3:00 (180 seconds)
- **Resolution**: 1920x1080 (16:9)
- **Layout**: Split screen — left panel (story context) + right panel (phone app mockup)
- **Narration**: AI-generated voice (ElevenLabs or Google TTS)
- **Music**: Subtle ambient/cinematic underscore throughout
- **Style**: Professional, emotional, grounded — not a tech demo, a human story told through technology

---

## Layout System

### Split Screen (default)
```
┌────────────────────────────┬───────────────┐
│                            │  ┌─────────┐  │
│     LEFT PANEL             │  │  Phone   │  │
│     (Story Context App)    │  │  Mockup  │  │
│     ~60% width             │  │  ~40%    │  │
│     1152 x 1080            │  │  width   │  │
│                            │  └─────────┘  │
│                            │               │
└────────────────────────────┴───────────────┘
```

### Full Screen App (hero moments)
```
┌────────────────────────────────────────────┐
│              ┌─────────┐                   │
│              │  Phone   │                  │
│              │  Mockup  │                  │
│              │  Large   │                  │
│              │  Center  │                  │
│              └─────────┘                   │
│         Dark/branded background            │
└────────────────────────────────────────────┘
```

### Full Screen Story (opening/closing)
```
┌────────────────────────────────────────────┐
│                                            │
│          Text / Image / Title              │
│          Full 1920x1080                    │
│                                            │
└────────────────────────────────────────────┘
```

---

## Scene-by-Scene Script

### SCENE 1: Cold Open — The Leaf (0:00–0:05)

**Layout**: Full Screen Story

**Left Panel App**: N/A (full screen)

**Visual**: Close-up photograph of a diseased cassava leaf — curled, yellowing, mosaic pattern visible. Image fills the screen with slight Ken Burns zoom-in. Location text fades in at bottom.

**Text Overlay**:
```
CASAMANCE, SENEGAL
```

**Narration**: None. Ambient sound only — wind, distant birds.

**Music**: Begins — low, atmospheric, single sustained note.

**Purpose**: Establish place. Create curiosity. "What am I looking at?"

---

### SCENE 2: The Answer (0:05–0:12)

**Layout**: Full Screen App

**Visual**: Phone mockup centered on dark background. The Field Chat screen is visible. A plant photo has just been sent. The diagnosis is streaming in.

**Right Panel (Phone)**:
- Field Chat page
- Plant photo visible in chat as user message
- Thinking bubble briefly visible: "Analyzing..."
- Assistant response streaming in:
  ```
  This appears to be Cassava Mosaic Disease (CMD).
  Severity: Moderate.

  Immediate action: Remove and burn this plant and
  any plants within 2 meters showing similar symptoms.

  For replanting: Use CMD-resistant variety TME 419,
  available through the extension service in Ziguinchor.

  Prevention: Apply neem oil as a natural whitefly
  deterrent — neem trees are abundant in this region.
  ```
- Sources indicator appears at bottom

**Narration**: None for first 3 seconds (let the diagnosis stream). Then at 0:08:

> "This diagnosis just happened without internet."

**Music**: Subtle build — a second layer enters.

**Purpose**: The "wow" moment. Judges see the payoff before they understand how it works.

---

### SCENE 3: Title Card (0:12–0:18)

**Layout**: Full Screen Story

**Visual**: Clean dark background (#1B2B1F — very dark forest green). Text fades in centered.

**Text**:
```
              FIELDPACK AI

  Offline expert knowledge for the field
```

**Narration**:

> "Without cloud. Without a single byte of data leaving this device."

**Music**: Brief pause/dip, then the main theme begins.

**Purpose**: Brand moment. Let the title breathe. The narration finishes the thought from Scene 2.

---

### SCENE 4: Amina's Profile (0:18–0:28)

**Layout**: Split Screen

**Left Panel App** — `PersonaFrame`:
```
Dark background. A persona card fades in, element by element:

┌─────────────────────────────────────┐
│                                     │
│   ┌─────┐                          │
│   │ 👤  │  AMINA DIALLO            │
│   │icon │  Agronomist              │
│   └─────┘                          │
│                                     │
│   Organization                     │
│   Action Against Hunger            │
│                                     │
│   Mission                          │
│   3-week field deployment          │
│   Casamance, Senegal               │
│                                     │
│   Focus                            │
│   Cassava & rice disease response  │
│   Drought-season survival strategy │
│                                     │
│   Challenge                        │
│   No reliable internet access      │
│                                     │
└─────────────────────────────────────┘

Elements fade in top-to-bottom over 3 seconds,
then hold for remaining 7 seconds.
```

**Right Panel (Phone)**: App home screen — pack loaded ("Casamance Agriculture"), model status showing Gemma 4 E2B ready. Static, establishing the app.

**Narration**:

> "Meet Amina. She's an agronomist with Action Against Hunger, deploying to Senegal's Casamance region for three weeks. Her mission: help smallholder farmers survive a drought season complicated by cassava mosaic virus outbreaks."

**Music**: Warm, grounded. Human theme.

**Purpose**: THE most important scene. This is who we built for. Judges must remember Amina.

---

### SCENE 5: The Map (0:28–0:35)

**Layout**: Split Screen

**Left Panel App** — `MapFrame`:
```
┌─────────────────────────────────────┐
│                                     │
│   ┌─────────────────────────────┐   │
│   │                             │   │
│   │     [Map of Senegal]        │   │
│   │                             │   │
│   │     • Dakar                 │   │
│   │       ╲                     │   │
│   │        ╲  ← 450 km         │   │
│   │         ╲                   │   │
│   │     ┌────────────┐         │   │
│   │     │ CASAMANCE  │         │   │
│   │     │ (glowing)  │         │   │
│   │     └────────────┘         │   │
│   │                             │   │
│   └─────────────────────────────┘   │
│                                     │
│      ⚠ No reliable internet        │
│      ⚠ Limited infrastructure      │
│                                     │
└─────────────────────────────────────┘

The Casamance region pulses/glows with amber.
Warning labels fade in after 3 seconds.
```

**Right Panel (Phone)**: Same home screen (static).

**Narration**:

> "Casamance is 450 kilometers from Dakar. Once she's there — no reliable internet. No cloud AI. No expert database to fall back on."

**Music**: Continues building subtly.

**Purpose**: Make the geography real. Judges picture the isolation.

---

### SCENE 6: Impact Stats (0:35–0:45)

**Layout**: Split Screen

**Left Panel App** — `StatsFrame`:
```
Three stats appear one at a time, each dominating the frame
for ~3 seconds before the next fades in below:

┌─────────────────────────────────────┐
│                                     │
│                                     │
│       800M                          │
│       people depend on cassava      │
│       ─────────────────────         │
│                                     │
│       50%                           │
│       crop yield lost to disease    │
│       in Sub-Saharan Africa         │
│       ─────────────────────         │
│                                     │
│       3.7B                          │
│       people without reliable       │
│       internet access               │
│                                     │
│                                     │
└─────────────────────────────────────┘

Numbers are HUGE (120pt+). Labels are small (18pt).
Each number does a quick count-up animation
(0 → 800M in 0.5 seconds).
Amber gold color for numbers. Cream for labels.
```

**Right Panel (Phone)**: Same home screen (static).

**Narration**:

> "Cassava feeds 800 million people. In Sub-Saharan Africa, mosaic virus alone destroys up to half the harvest. And 3.7 billion people worldwide lack the internet access that could bring AI to help."

**Music**: Emotional swell on "3.7 billion."

**Purpose**: Anchor the impact in real numbers. These aren't abstract — they're why this project exists.

---

### SCENE 7: The Insight (0:45–0:55)

**Layout**: Split Screen

**Left Panel App** — `ArchitectureFrame`:
```
Simple vertical flow diagram. Each element appears
as narration mentions it:

┌─────────────────────────────────────┐
│                                     │
│   PHASE 1 · ONLINE                  │
│   ┌─────────────────────────────┐   │
│   │  ☁ Cloud AI Agents          │   │
│   │  Gemma 4 31B + 26B          │   │
│   │  Research · Compile · Verify │   │
│   └──────────────┬──────────────┘   │
│                  │                   │
│                  ▼                   │
│   ┌─────────────────────────────┐   │
│   │  📦 Knowledge Pack           │   │
│   │  Portable · 200 MB          │   │
│   │  Domain-specific · Verified  │   │
│   └──────────────┬──────────────┘   │
│                  │                   │
│                  ▼                   │
│   PHASE 2 · OFFLINE                 │
│   ┌─────────────────────────────┐   │
│   │  📱 Edge AI Agent            │   │
│   │  Gemma 4 E2B on Ollama      │   │
│   │  Search · Diagnose · Advise  │   │
│   └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘

Each box fades in from top to bottom.
Arrows animate downward.
Clean, minimal. Not a complex diagram.
```

**Right Panel (Phone)**: App home screen showing the two CTA cards — "Create Knowledge Pack" (labeled Online) and "Start Field Session" (labeled No Internet). This mirrors the architecture diagram on the left.

**Narration**:

> "What if AI could prepare before she loses connectivity? Powerful cloud models research her specific mission, compile a portable Knowledge Pack, and hand it to an edge AI that works completely offline."

**Music**: Transitional — shifts from emotional to purposeful.

**Purpose**: The "aha" moment. The architecture explained in 10 seconds, visually.

---

### SCENE 8: Online Phase — Mission Chat (0:55–1:10)

**Layout**: Split Screen

**Left Panel App** — `OnlinePhaseFrame`:
```
┌─────────────────────────────────────┐
│                                     │
│   PHASE 1 · MISSION BRIEFING        │
│   ─────────────────────────         │
│                                     │
│   Location: Dakar, Senegal          │
│   Status:   Before deployment       │
│                                     │
│   ┌─ AI Research Agents ─────────┐  │
│   │                              │  │
│   │  🔍 Disease Identification   │  │
│   │     Cassava mosaic, streak   │  │
│   │                              │  │
│   │  💊 Treatment Protocols      │  │
│   │     Local materials focus    │  │
│   │                              │  │
│   │  🌱 Resistant Varieties      │  │
│   │     Regional availability    │  │
│   │                              │  │
│   │  🌤 Climate & Drought        │  │
│   │     Casamance 2026 season    │  │
│   │                              │  │
│   │  📚 Local Practices          │  │
│   │     Extension service data   │  │
│   │                              │  │
│   └──────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘

Agent rows light up one by one (amber glow)
as the mission chat progresses on the right.
```

**Right Panel (Phone)**:
- Mission Chat page
- Amina types: "I'm deploying to the Casamance region of Senegal. Smallholder farmers are facing cassava mosaic disease and drought. I need to help them identify diseases, recommend treatments with local materials, and advise on drought-resistant planting."
- LLM responds, building a Mission Card (region, crops, season, focus areas)
- "Dispatch Agents" button appears

**Narration**:

> "Before leaving Dakar, Amina describes her mission. The AI understands what she needs — disease identification, treatment protocols, resistant crop varieties, climate data — all specific to Casamance."

**Music**: Purposeful, building energy.

**Purpose**: Show the online phase is real and intelligent, not just a file download.

---

### SCENE 9: Online Phase — Agent Progress (1:10–1:30)

**Layout**: Split Screen

**Left Panel App** — `ProgressFrame`:
```
┌─────────────────────────────────────┐
│                                     │
│   COMPILING KNOWLEDGE PACK          │
│   ═══════════════════════           │
│                                     │
│   Sources Gathered                  │
│   ████████████████████░░░  47       │
│                                     │
│   Knowledge Entries                 │
│   █████████████████████░░  156      │
│                                     │
│   Reference Images                  │
│   ████████████░░░░░░░░░░░  23       │
│                                     │
│   ─────────────────────────────     │
│                                     │
│   Estimated Pack Size   ~200 MB     │
│   Processing Time       ~8 min      │
│                                     │
│   ┌──────────────────────────────┐  │
│   │  ✓ Source Gathering          │  │
│   │  ✓ Knowledge Extraction      │  │
│   │  ● Compilation...            │  │
│   │  ○ Chunk Generation          │  │
│   │  ○ Image Download            │  │
│   └──────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘

Progress bars animate. Numbers count up.
Checklist items tick off one by one.
```

**Right Panel (Phone)**:
- Agent Progress page
- 6-phase timeline ticking through
- Stats cards climbing (findings, chunks, images)
- Progress bar filling
- Completion state → "Knowledge Pack Ready"
- Pack stats displayed

**Narration**:

> "A team of AI agents fans out — gathering data from crop disease databases, agricultural extension services, climate records. In minutes, they compile everything into a single portable Knowledge Pack. 200 megabytes of expert knowledge she can carry in her pocket."

**Music**: Energy peaks as "Pack Ready" appears.

**Purpose**: Show the pipeline is real. The progress visualization is satisfying — judges see work happening.

---

### SCENE 10: The Transition (1:30–1:40)

**Layout**: Split Screen

**Left Panel App** — `TransitionFrame`:
```
┌─────────────────────────────────────┐
│                                     │
│   ┌─────────────────────────────┐   │
│   │                             │   │
│   │     [Map animation:         │   │
│   │      Dakar pin              │   │
│   │      → dotted line →        │   │
│   │      Casamance pin]         │   │
│   │                             │   │
│   └─────────────────────────────┘   │
│                                     │
│                                     │
│   NO  WIFI.                         │
│                                     │
│   NO  DATA.                         │
│                                     │
│   NO  CLOUD.                        │
│                                     │
│                                     │
│   ─────────────────────────────     │
│   Just her and her Knowledge Pack.  │
│                                     │
└─────────────────────────────────────┘

Lines appear one at a time. 1 second apart.
Bold, large type. Stark.
Final line in italic, smaller, warmer.
```

**Right Panel (Phone)**:
- Home screen or settings
- Airplane mode toggled ON
- WiFi icon disappears from status bar
- "Offline" badge appears on app

**Narration**:

> "Amina flies to Ziguinchor. No WiFi. No data. No cloud."
>
> *[1 second pause]*
>
> "Just her and her Knowledge Pack."

**Music**: Drops to near-silence. Single sustained note. This is the emotional pivot.

**Purpose**: THE most cinematic moment. The silence says everything. Judges feel the isolation.

---

### SCENE 11: First Offline Interaction (1:40–1:55)

**Layout**: Split Screen → Full Screen App

**Left Panel App** — `FieldSessionFrame`:
```
┌─────────────────────────────────────┐
│                                     │
│   FIELD SESSION                     │
│   Day 3 · Casamance                 │
│   ─────────────────────────         │
│                                     │
│   ┌──────────────────────────────┐  │
│   │  ⚡ OFFLINE MODE              │  │
│   │                              │  │
│   │  Active Pack:                │  │
│   │  Casamance Agriculture       │  │
│   │                              │  │
│   │  156 knowledge entries       │  │
│   │  23 reference images         │  │
│   │  47 verified sources         │  │
│   │                              │  │
│   │  Model: Gemma 4 E2B          │  │
│   │  via Ollama (local)          │  │
│   └──────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

**Right Panel (Phone)**:
- Field Chat page
- Amina types: "When should I plant cassava in Casamance this season considering the drought?"
- Thinking bubble shows steps: Classifying → Searching → Generating
- Response streams in with specific local advice
- Source citations visible at bottom

**At 1:50**: Left panel fades out. Phone mockup grows and centers. **Full Screen App** for the streaming response.

**Narration**:

> "Day three in the field. A farmer asks about planting schedules. Amina asks her Knowledge Pack."
>
> *[Response streams on screen]*
>
> "Locally relevant. Source-cited. Immediate. No internet required."

**Music**: Gently rebuilds. Warm, confident.

**Purpose**: First proof that offline works. Transition to full screen builds excitement for the hero shot.

---

### SCENE 12: The Hero Shot (1:55–2:20)

**Layout**: Full Screen App (entire 25 seconds)

**Visual**: Phone mockup centered, LARGER than previous scenes. Dark branded background. This gets maximum visual real estate.

**Right Panel (Phone)** — Step by step:

**1:55–2:00**: Camera icon tapped. Plant photo appears in chat (the same diseased cassava leaf from the cold open — callback).

**2:00–2:05**: Thinking bubble animates: "Classifying... Searching knowledge base... Analyzing image... Generating diagnosis..."

**2:05–2:12**: Diagnosis streams in:
```
This appears to be Cassava Mosaic Disease (CMD),
likely caused by African cassava mosaic virus.
Severity: Moderate — mosaic pattern covers ~40% of leaf area.

Immediate action: Remove and burn this plant and any
plants within 2 meters to prevent whitefly transmission.

For replanting: Use CMD-resistant varieties TME 419
or IITA-TMS-IBA30572, available through the Senegalese
agricultural extension service in Ziguinchor.

Prevention: Intercrop with maize to reduce whitefly
density. Apply neem oil extract as natural deterrent —
neem trees are abundant in this region.
```

**2:12–2:16**: Screen transitions to Diagnosis Card page — confidence arc animates to 87%, severity badge "Moderate" in amber, treatment section visible.

**2:16–2:20**: Sources panel at bottom — 3-4 source entries visible with relevance scores.

**Narration**:

> "A farmer shows her a plant with curled, yellowing leaves. She photographs it."
>
> *[Diagnosis streams — let the text speak for itself for 3 seconds]*
>
> "Cassava Mosaic Disease. Moderate severity. Remove infected plants. Replant with CMD-resistant TME 419 — available right here in Ziguinchor. Use neem oil against whiteflies — neem trees grow everywhere in Casamance."
>
> "Every answer traced back to verified sources. Not hallucination. Curated knowledge."

**Music**: Confident, warm. The emotional payoff.

**Purpose**: THIS IS THE MOMENT. The hero shot. The whole video builds to this. If judges remember one thing, it's this: plant photo → specific, local, actionable diagnosis — offline.

---

### SCENE 13: Follow-up + Grounded AI (2:20–2:35)

**Layout**: Split Screen

**Left Panel App** — `GroundedFrame`:
```
┌─────────────────────────────────────┐
│                                     │
│   GROUNDED AI                       │
│   ═══════════════                   │
│                                     │
│   Every answer traces to a          │
│   verified source:                  │
│                                     │
│   ┌──────────────────────────────┐  │
│   │  📄 PlantVillage Database    │  │
│   │     Disease identification   │  │
│   │                              │  │
│   │  📄 FAO Treatment Protocols  │  │
│   │     Recommended practices    │  │
│   │                              │  │
│   │  📄 IITA Variety Catalog     │  │
│   │     Resistant cultivars      │  │
│   │                              │  │
│   │  📄 Senegal Extension        │  │
│   │     Service Records          │  │
│   │     Local availability       │  │
│   └──────────────────────────────┘  │
│                                     │
│   No hallucination.                 │
│   No guessing.                      │
│   Verified, curated knowledge.      │
│                                     │
└─────────────────────────────────────┘

Source entries fade in one by one.
```

**Right Panel (Phone)**:
- Field Chat continues
- Amina types a follow-up: "What about the rest of the field? How do I prevent this from spreading?"
- Response streams with prevention strategy
- Sources panel expanded — source entries with relevance scores visible

**Narration**:

> "She asks follow-ups. Gets prevention strategies, intercropping advice, biological control methods — all from verified agricultural databases. No hallucination. No guessing. Curated, mission-specific knowledge."

**Music**: Steady, confident.

**Purpose**: Build trust. "Grounded AI" is a key phrase for AI competitions. Show judges this isn't making things up.

---

### SCENE 14: Platform Vision (2:35–2:50)

**Layout**: Split Screen

**Left Panel App** — `PlatformFrame`:
```
┌─────────────────────────────────────┐
│                                     │
│   ONE ARCHITECTURE.                 │
│   ANY MISSION.                      │
│   ═══════════════                   │
│                                     │
│   ┌───────────┐  ┌───────────┐     │
│   │  🌾       │  │  🏥       │     │
│   │           │  │           │     │
│   │Agriculture│  │ Medical   │     │
│   │           │  │ Triage    │     │
│   └───────────┘  └───────────┘     │
│                                     │
│   ┌───────────┐  ┌───────────┐     │
│   │  📚       │  │  🦁       │     │
│   │           │  │           │     │
│   │ Education │  │ Wildlife  │     │
│   │           │  │ Conserv.  │     │
│   └───────────┘  └───────────┘     │
│                                     │
│   ┌───────────┐                     │
│   │  🏗       │                     │
│   │           │                     │
│   │ Infra     │                     │
│   │ Assess.   │                     │
│   └───────────┘                     │
│                                     │
└─────────────────────────────────────┘

Cards appear one by one with subtle pop animation.
Agriculture card has a green glow (the one we built).
Others are slightly dimmed (the vision).
```

**Right Panel (Phone)**:
- Pack List page showing the Casamance Agriculture pack
- Optionally: placeholder cards for other packs (dimmed/coming soon style)

**Narration**:

> "Agriculture is just the first Knowledge Pack. The same architecture serves any expert going where internet doesn't. Disaster medical triage. Rural education. Wildlife conservation. Infrastructure assessment. Same system. Different pack. Any mission. Anywhere. Offline."

**Music**: Broadening, expansive. The vision swells.

**Purpose**: Transform from "a hackathon project" to "a platform." This is the "this could be a company" moment.

---

### SCENE 15: Closing (2:50–3:00)

**Layout**: Full Screen Story

**Visual**: Dark background (#1B2B1F). Clean typography. Elements fade in sequentially.

**Text**:
```
                FIELDPACK AI

     "The people who need AI most
      are the ones furthest from the cloud."

     ──────────────────────────────────

     Built with Gemma 4 on Ollama

     [Gemma 4 logo]     [Ollama logo]

     github.com/[repo]
```

**Narration**:

> "FieldPack AI. Built with Gemma 4 on Ollama. Because the people who need AI most are the ones furthest from the cloud."

**Music**: Resolves. Final note. Clean ending.

**Purpose**: Memorable closing line. Brand logos. The Ollama mention is explicit for the special technology prize. End with emotional resonance, not technical specs.

---

## Left Panel App — Frame Summary

The left-panel app is a simple React app that displays one frame at a time, controlled by URL hash or a timer. Each frame is a React component with CSS animations.

| # | Frame ID | Component | Key Animation | Duration |
|---|----------|-----------|---------------|----------|
| 1 | `location` | LocationFrame | Ken Burns zoom on photo | 5s |
| 2 | `title` | TitleFrame | Fade-in text | 6s |
| 3 | `persona` | PersonaFrame | Card elements fade in top-to-bottom | 10s |
| 4 | `map` | MapFrame | Region pulse/glow, labels fade in | 7s |
| 5 | `stats` | StatsFrame | Numbers count up, sequential reveal | 10s |
| 6 | `architecture` | ArchitectureFrame | Boxes + arrows appear top-to-bottom | 10s |
| 7 | `online-phase` | OnlinePhaseFrame | Agent rows light up one by one | 15s |
| 8 | `progress` | ProgressFrame | Bars animate, numbers count, checks tick | 20s |
| 9 | `transition` | TransitionFrame | Text lines appear one per second | 10s |
| 10 | `field-session` | FieldSessionFrame | Card fade-in | 15s |
| 11 | `grounded` | GroundedFrame | Sources fade in one by one | 15s |
| 12 | `platform` | PlatformFrame | Pack cards pop in one by one | 15s |
| 13 | `closing` | ClosingFrame | Sequential text + logo fade-in | 10s |

### Tech Stack (Left Panel App)
- React + TypeScript + Tailwind (same as main app — shared tooling)
- No backend needed — pure frontend, static frames
- Controlled via URL: `localhost:5174/#persona` or `localhost:5174/#stats`
- OR controlled via query param timer: `localhost:5174/?auto=true` plays all frames sequentially
- Playwright navigates between frames by changing the URL hash

### Design System
- Background: Dark (#1B2B1F or #0F1A14)
- Primary text: Cream (#F5F1EB)
- Accent numbers: Amber Gold (#D4A017)
- Highlight: Forest Green (#2D6A4F)
- Alert: Muted Red (#C44536)
- Font: Inter (body), Plus Jakarta Sans (headlines) — matches main app
- Animations: CSS transitions + @keyframes. Smooth, not flashy. 0.5-1s durations.

---

## Narration — Full Script (Continuous)

For AI voice generation, the complete narration as one continuous script.

Target timeline: **2:50 total**. Clips 1 and 2 (original cold-open VO) are not used — the video opens with a 3-second title card over music, then narration begins.

```
[0:03]  Meet Amina. She's an agronomist with Action Against Hunger,
        deploying to Senegal's Casamance region for three weeks.
        Her mission: help smallholder farmers survive a drought season
        complicated by cassava mosaic virus outbreaks.

[0:13]  Casamance is 450 kilometers from Dakar. Once she's there —
        no reliable internet. No cloud AI. No expert database
        to fall back on.

[0:20]  Cassava feeds 800 million people. In Sub-Saharan Africa,
        mosaic virus alone destroys up to half the harvest.
        And 3.7 billion people worldwide lack the internet access
        that could bring AI to help.

[0:30]  What if AI could prepare before she loses connectivity?
        Powerful cloud models research her specific mission,
        compile a portable Knowledge Pack, and hand it to an edge AI
        that works completely offline.

[0:40]  Before leaving Dakar, Amina describes her mission. The AI
        understands what she needs — disease identification,
        treatment protocols, resistant crop varieties, climate data —
        all specific to Casamance.

[0:55]  A team of AI agents fans out — gathering data from crop disease
        databases, agricultural extension services, climate records.
        In minutes, they compile everything into a single portable
        Knowledge Pack. 200 megabytes of expert knowledge she can carry
        in her pocket.

[1:15]  Amina flies to Ziguinchor. No WiFi. No data. No cloud.

[1:21]  Just her and her Knowledge Pack.

[1:25]  Day three in the field. A farmer asks about planting schedules.
        Amina asks her Knowledge Pack.

[1:35]  Locally relevant. Source-cited. Immediate.
        No internet required.

[1:40]  A farmer shows her a plant with curled, yellowing leaves.
        She photographs it.

[1:52]  Cassava Mosaic Disease. Moderate severity. Remove infected plants.
        Replant with CMD-resistant TME 419 — available right here
        in Ziguinchor. Use neem oil against whiteflies — neem trees
        grow everywhere in Casamance.

[2:02]  Every answer traced back to verified sources.
        Not hallucination. Curated knowledge.

[2:05]  She asks follow-ups. Gets prevention strategies, intercropping
        advice, biological control methods — all from verified
        agricultural databases. No hallucination. No guessing.
        Curated, mission-specific knowledge.

[2:20]  Agriculture is just the first Knowledge Pack. The same
        architecture serves any expert going where internet doesn't.
        Disaster medical triage. Rural education. Wildlife conservation.
        Infrastructure assessment. Same system. Different pack.
        Any mission. Anywhere. Offline.

[2:35]  FieldPack AI. Built with Gemma 4 on Ollama.
        Because the people who need AI most are the ones
        furthest from the cloud.
```

Total narration: approximately 440 words at ~170 words/minute = ~2:35 of speaking.
Remaining ~15 seconds is title card intro and micro-pauses between sections.

---

## Production Pipeline

```
1. Write demo response content  →  demo/script.json
2. Build demo backend mode      →  DEMO_MODE=true in backend
3. Build left-panel app         →  video-frames/ directory
4. Write Playwright script      →  demo/record.ts
5. Run Playwright               →  captures both apps simultaneously
6. Generate AI narration        →  ElevenLabs / Google TTS
7. Composite in video editor    →  DaVinci Resolve
   - Left panel recording (1152x1080)
   - Right panel recording (768x1080) in phone mockup
   - Narration audio track
   - Background music track
   - Stock footage inserts (Scene 1)
   - Title cards (Scene 3, 15)
8. Export final video            →  1080p MP4, upload to YouTube
```

---

## Stock Assets Needed

| Asset | Source | Notes |
|-------|--------|-------|
| Diseased cassava leaf photo | PlantVillage or own photo | Close-up, mosaic pattern visible |
| Senegal/Casamance landscape | Pexels / Pixabay (free) | Farmland, rural, golden hour if possible |
| Map of Senegal | Simple vector map | Highlight Casamance region |
| Phone mockup frame | Free device mockup | iPhone or Android frame |
| Gemma 4 logo | Google brand assets | Check usage guidelines |
| Ollama logo | Ollama brand assets | Check usage guidelines |
| Background music | Royalty-free | Cinematic ambient, 3 minutes |

---

## Quality Checklist

Before final export, verify:

- [ ] Cold open grabs attention in first 3 seconds
- [ ] Amina's story is clear by 0:28 (first 28 seconds)
- [ ] Architecture is understood by 0:55 (no jargon)
- [ ] Hero shot (plant → diagnosis) is the emotional peak
- [ ] "Offline" is said/shown at least 5 times
- [ ] "Ollama" is mentioned in narration AND shown on screen
- [ ] "Gemma 4" is mentioned in narration AND shown on screen
- [ ] Sources/grounding is visible — judges see this isn't hallucination
- [ ] Platform vision is stated but not overpromised
- [ ] Closing line is memorable
- [ ] No scene runs longer than 25 seconds (attention span)
- [ ] Total runtime ≤ 3:00.0
- [ ] Audio levels: narration clear over music, no clipping
- [ ] Phone mockup is crisp and readable at 1080p
