# FieldPack AI — Submission Playbook

> Everything we need to produce, how to produce it, and what the judges are looking for.
> Companion to [PHILOSOPHY.md](./PHILOSOPHY.md) (strategy) and [TECH_FRAMEWORK.md](./TECH_FRAMEWORK.md) (architecture).

---

## Table of Contents

1. [What We Must Submit](#1-what-we-must-submit)
2. [What Won Last Time — Raw Data](#2-what-won-last-time--raw-data)
3. [The 7 Patterns That Win](#3-the-7-patterns-that-win)
4. [Judging Criteria — Exact Weights](#4-judging-criteria--exact-weights)
5. [Prize Strategy — Multiple Shots at Winning](#5-prize-strategy--multiple-shots-at-winning)
6. [Video Plan](#6-video-plan)
7. [Demo Recording System](#7-demo-recording-system)
8. [Writeup Plan](#8-writeup-plan)
9. [Live Demo Plan](#9-live-demo-plan)
10. [Media Gallery Plan](#10-media-gallery-plan)
11. [Production Timeline](#11-production-timeline)

---

## 1. What We Must Submit

All five are **mandatory** for a valid submission:

| Deliverable | Format | Key Constraint |
|-------------|--------|----------------|
| **Kaggle Writeup** | Blog-style on Kaggle | Max 1,500 words. Must select a Track. Needs cover image. |
| **Video** | YouTube (public, no login required) | Max 3 minutes. Attached to Media Gallery. |
| **Public Code Repository** | GitHub (public) | Well-documented. Proves the tech is real. |
| **Live Demo** | URL or files | Publicly accessible, no login/paywall. |
| **Media Gallery** | Images + video on Kaggle | Cover image required. Screenshots, architecture diagrams. |

**Deadline**: May 18, 2026, 11:59 PM UTC.

One writeup per team. Can be un-submitted, edited, and re-submitted unlimited times before deadline.

---

## 2. What Won Last Time — Raw Data

### The Gemma 3n Impact Challenge (2025)

- 600+ submissions, $150,000 prize pool, 8 winners
- Source: [Google Blog announcement](https://blog.google/technology/developers/developers-changing-lives-with-gemma-3n/)

#### All 8 Winners

| # | Project | What It Did | Why It Won | Tech Highlight |
|---|---------|-------------|------------|----------------|
| 1 | **Vite Vere** | Offline companion for people with cognitive disabilities. Images → simple spoken instructions. | Offline-first. Hyper-specific user (Down syndrome cooperative). Undeniable human impact. | Flutter + MediaPipe LLM Inference API. Multi-language. |
| 2 | **LENTERA** | Transforms cheap hardware into offline WiFi microservers running Gemma 3n for schools. | Infrastructure-level thinking. Not an app — a platform. Offline-first. | Ollama. Local WiFi hotspot broadcast. |
| 3 | **Sixth Sense** | Security camera AI. YOLO-NAS detects movement, Gemma 3n provides human-level context. | Multimodal pipeline (vision + reasoning). Clear practical "wow" — 360fps across 16 cameras. | YOLO-NAS + Gemma 3n cascade. |
| 4 | **Gemma Vision** | Chest-mounted phone camera for blind users. AI describes surroundings via voice. | Simple concept, flawless execution. Developer's blind brother co-designed it. | 8BitDo controller for no-touch interaction. |
| 5 | **3VA** | Fine-tuned Gemma 3n to translate pictograms into rich language for Eva (cerebral palsy). | Named real person. Fine-tuning showcase. Cost-effective on-device AAC. | Apple MLX for local fine-tuning. |
| 6 | **Dream Assistant** | Trained on individual's audio to understand unique speech patterns (speech impairment). | Personalization at its most meaningful. | Unsloth for efficient fine-tuning. |
| 7 | **Better-ed** | Voice-based educational assessment. Students speak understanding instead of writing. | Practical classroom tool. Tested against simulated student personas. | Unsloth for performance. Offline + sync. |
| 8 | **Graph-based Cost Learning** | Robotics planning with Gemma 3n. Scanning-time-first pipeline on LeRobot. | Embodied AI at the edge. Novel domain for small models. | IGMC + Gemma 3n planning. |

#### Winner Presentation Quality

**Vite Vere** (the one public GitHub repo found):
- Badge indicators (Flutter version, Gemma 3N, Kaggle contest, Apache 2.0 license)
- Dual-language README (Italian + English)
- Clear section hierarchy with emoji navigation
- Developer biography emphasizing mission-driven work
- Explicit model size warnings (2.9GB vs 4.1GB)
- Link: [github.com/guidomarangoni/vite-vere-offline](https://github.com/guidomarangoni/vite-vere-offline)

**Better-ed** (the one public post-mortem found):
- Founder Allan Tan narrated the video directly (face on camera)
- Video structured: problem → product in action → bigger vision
- Post-mortem explicitly stated competition valued "creativity, usability, and inclusivity" over raw technical metrics
- Link: [better-ed.ai/blog/gemma-3n-better-ed](https://better-ed.ai/blog/gemma-3n-better-ed)

---

## 3. The 7 Patterns That Win

Distilled from all 8 winners + Better-ed's post-mortem + competition evaluation criteria.

### Pattern 1: One Person, One Story

Not "farmers in Africa." Not "3.7 billion people." ONE named human with a face, a job, and a problem.

- 3VA named Eva. Gemma Vision's developer had his blind brother co-design it.
- **Our Amina**: Agronomist with Action Against Hunger, deploying to Casamance, Senegal. Cassava and rice farmers. Drought + mosaic virus.

### Pattern 2: Offline Is the Centerpiece, Not a Feature

Every offline winner made disconnected operation the REASON the project exists, not an afterthought. Google designed these models for edge deployment — projects that leaned into this design intent won.

- **We're aligned**: "Offline is not a feature — it is the point" (PHILOSOPHY.md, Principle 11.4).

### Pattern 3: The Demo Explains Itself in 5 Seconds

Judges watch hundreds of submissions. They decide in the first minute. If the value needs explanation, you've already lost.

- Plant photo → diagnosis → treatment plan. Anyone on Earth understands this instantly.
- **Our hero shot**: Snap a photo of a sick cassava plant → get disease ID + local treatment.

### Pattern 4: Creativity, Usability, Inclusivity > Raw Metrics

Direct quote from Better-ed's post-mortem: the competition emphasized *"creativity, usability, and inclusivity"* rather than purely technical metrics. A polished, usable, inclusive tool beats a technically superior but unusable one.

### Pattern 5: Technology Serves the User, Never the Other Way Around

No winner showcased technology for its own sake. Fine-tuning, multimodal pipelines, offline inference — means to an end. The technique is invisible to the user and visible only to judges reading the writeup.

### Pattern 6: The Platform Story

LENTERA wasn't just a server — it was "an educational hub." 3VA wasn't just a translator — it was "AAC technology." Winners framed their work as bigger than one demo.

- **Our frame**: "Knowledge Packs" — agriculture is the first, but the architecture supports medical triage, education, conservation, infrastructure assessment.

### Pattern 7: Technology Partners = Bonus Prizes

Both the Gemma 3n and Gemma 4 hackathons have dedicated $10K prizes for Ollama and Unsloth. Projects using these tools get additional shots at winning.

- **We use Ollama** → eligible for the $10K Ollama special technology prize.

---

## 4. Judging Criteria — Exact Weights

From the Gemma 4 Good Hackathon rules:

| Criteria | Points | What Judges Ask | How We Score |
|----------|--------|-----------------|--------------|
| **Impact & Vision** | 40/100 | How clearly does the video address a real-world problem? Is the vision inspiring? | Amina. 3.7B without internet. Cassava = food for 800M people. Platform vision. |
| **Video Pitch & Storytelling** | 30/100 | How exciting, engaging, and well-produced is the video? | Cold open hero shot. AI narration. Professional editing. Story arc. |
| **Technical Depth & Execution** | 30/100 | How innovative is the use of Gemma 4? Is it real, functional, well-engineered? | Full model family. Agentic RAG. Function calling. WebSocket streaming. Public repo proves it. |

**Key insight**: Impact + Video = 70 points. Technical = 30 points. The video is where we win or lose. The code repo just has to prove the demo isn't faked.

---

## 5. Prize Strategy — Multiple Shots at Winning

We are eligible for multiple prizes simultaneously:

| Prize | Amount | Our Angle |
|-------|--------|-----------|
| **Main Track (1st–4th)** | $50K / $25K / $15K / $10K | Full project — strongest submission |
| **Global Resilience** | $10K | Agriculture, climate adaptation, offline edge |
| **Ollama Special Technology** | $10K | We run Gemma 4 E2B on Ollama — it's our core inference engine |

**Total potential**: Up to $60K if we win Main Track 1st + Global Resilience + Ollama.

We should explicitly mention Ollama prominently in the writeup and video to maximize the Ollama prize chances.

---

## 6. Video Plan

### Format Decision

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Face on camera | Human connection, credibility | Requires good English, presentation skills | Brief intro only (5s) |
| AI narration | Professional, polished, consistent | Less personal | Primary narration |
| Pure screen recording | Easy to produce | Boring, no story | Never alone |

**Decision**: AI-narrated voiceover (ElevenLabs or Google TTS) over automated screen recording. Optional 5-second face intro ("Hi, I'm [name], and this is FieldPack AI"). Cold open with hero shot before any narration.

### Minute-by-Minute Script

```
[0:00–0:10]  COLD OPEN — Hero shot. No narration.
             Phone camera points at diseased cassava plant. Tap.
             Diagnosis + treatment streams onto screen.
             Ambient sound only. Let the moment breathe.

[0:10–0:20]  HOOK + TITLE
             Narration: "This diagnosis just happened without internet.
             Without cloud. Without a single byte leaving this device."
             Title card: FieldPack AI.

[0:20–0:45]  THE PROBLEM (25 seconds)
             Narration: "3.7 billion people lack reliable internet.
             Among them — humanitarian workers, field researchers,
             teachers — deploying to the world's hardest places.
             Their phone has an AI model. But without internet,
             that model knows nothing about their specific mission."
             Visuals: Connectivity map. Rural landscape. Phone with no signal.

[0:45–1:00]  THE INSIGHT (15 seconds)
             Narration: "What if AI could prepare before you lose connectivity?
             What if powerful cloud agents could research your mission,
             compile everything into a portable Knowledge Pack,
             and hand it to an edge AI that goes with you into the field?"
             Visuals: Simple animation — cloud → Knowledge Pack → device.

[1:00–1:40]  ONLINE PHASE DEMO (40 seconds)
             Narration: "Meet Amina. She's an agronomist deploying to
             Senegal's Casamance region. Before she leaves, she briefs
             FieldPack AI on her mission..."
             Visuals: App screen recording (Playwright-driven).
             - Amina types her mission description
             - Agent progress UI shows research steps activating
             - Sources being gathered, knowledge being compiled
             - Knowledge Pack ready → download
             Narration: "In under 10 minutes, a team of AI agents
             researches her specific needs — crop diseases, treatments,
             local materials, climate data — and packages it all into
             a single portable Knowledge Pack."

[1:40–1:50]  THE TRANSITION (10 seconds)
             Narration: "Now Amina goes to the field. No internet. No cloud.
             Just her phone and her Knowledge Pack."
             Visuals: Airplane mode toggle. WiFi icon disappears.
             Dramatic pause.

[1:50–2:30]  OFFLINE PHASE DEMO (40 seconds)
             Narration walks through 2-3 interactions:
             1. Text question about cassava planting season → contextual answer
             2. Plant photo upload → disease diagnosis + treatment with local materials
             3. Follow-up question → response citing specific sources
             Visuals: App screen recording showing streaming responses,
             source citations, expandable source details.
             Narration: "Every answer is grounded in curated, mission-specific
             knowledge. Not generic AI — expert-level, locally relevant guidance."

[2:30–2:45]  THE PLATFORM VISION (15 seconds)
             Narration: "Agriculture is just the first Knowledge Pack.
             The same architecture supports disaster medical triage,
             rural education, wildlife conservation —
             any mission where an expert needs knowledge and has no internet."
             Visuals: Grid of 5 Knowledge Pack cards with icons.

[2:45–3:00]  CLOSING (15 seconds)
             Narration: "Same architecture. Different pack.
             Any mission. Anywhere. Offline.
             FieldPack AI — built with Gemma 4 on Ollama."
             Visuals: Logo. "Built with Gemma 4" badge. GitHub link.
             Mention Ollama explicitly for the special prize.
```

### Production Elements Needed

| Element | Tool | Notes |
|---------|------|-------|
| AI narration audio | ElevenLabs / Google Cloud TTS | Natural male or female voice. Record as one track. |
| Screen recording | Playwright automation | Deterministic, repeatable. See Section 7. |
| Cold open footage | Phone camera (real or simulated) | Real hand, real plant photo, real app on phone screen. OR Playwright on mobile viewport. |
| Connectivity map | Stock image or generated | Show internet coverage gaps in Sub-Saharan Africa. |
| Rural landscape | Stock footage (Pexels/Pixabay, free) | Senegal/West Africa farmland. 3-5 seconds. |
| Architecture animation | Simple motion graphic | Cloud → Pack → Device. Can be Canva/PowerPoint animated. |
| Knowledge Pack grid | Single designed slide | 5 packs with icons. Canva or Figma. |
| Title card + logo | Designed asset | Clean, professional. |
| Background music | Royalty-free ambient track | Subtle. Underscore, not distraction. |
| Video editing | DaVinci Resolve (free) or CapCut | Layer: screen recording + narration + music + overlays. |

---

## 7. Demo Recording System

### The Problem

The real online pipeline takes minutes. Manual screen recording is error-prone and non-repeatable. We need narration synced to exact screen events.

### The Solution: Playwright + Demo Backend

```
Playwright script          Demo backend (DEMO_MODE=true)
(exact timing)      →      (cached responses, controlled delays)
      ↓                              ↓
Drives browser                Returns pre-computed results
Types, clicks, scrolls       Streams text at natural reading pace
      ↓
Identical screen recording every run
      ↓
Sync with narration audio in video editor
```

### Component 1: Demo Backend Mode

A `DEMO_MODE=true` environment flag that:
- Intercepts all WebSocket and API calls
- Returns pre-written responses from a JSON script file
- Streams tokens character-by-character at a controlled pace (~30 chars/sec, natural reading speed)
- Simulates agent progress steps with realistic delays (2-3 seconds per step)
- Serves the same plant diagnosis, same treatment plan, every single run
- No Ollama, no ChromaDB, no LLM needed — pure replay

The demo script file (`demo/script.json`) contains:
```json
{
  "scenes": [
    {
      "id": "mission_briefing",
      "input": "I'm deploying to the Casamance region...",
      "agent_steps": [
        {"status": "Analyzing mission requirements...", "delay_ms": 2000},
        {"status": "Researching cassava diseases in Casamance...", "delay_ms": 3000},
        {"status": "Gathering treatment protocols...", "delay_ms": 2500},
        {"status": "Compiling Knowledge Pack...", "delay_ms": 3000}
      ],
      "response": "Your Knowledge Pack is ready...",
      "stream_speed": 30
    },
    {
      "id": "plant_diagnosis",
      "input_image": "demo/cassava_mosaic.jpg",
      "response": "This appears to be Cassava Mosaic Disease...",
      "sources": [...],
      "stream_speed": 30
    }
  ]
}
```

### Component 2: Playwright Automation Script

`demo/record.ts` — drives the browser with exact timing:

```
Step 1:  Open http://localhost:5173 (pause 2s)
Step 2:  Click "New Mission" or navigate to mission briefing
Step 3:  Type mission description (character by character, 50ms per char)
Step 4:  Hit send
Step 5:  Wait for agent progress steps (demo backend controls timing)
Step 6:  Knowledge Pack download animation completes
Step 7:  Navigate to Field Chat
Step 8:  Type first question (character by character)
Step 9:  Wait for streaming response
Step 10: Click camera/upload, select plant photo
Step 11: Wait for diagnosis to stream
Step 12: Type follow-up question
Step 13: Wait for response
Step 14: Click on sources panel
Step 15: Pause on final screen (2s)
```

Each step logs its timestamp. We use these timestamps to align narration.

### Component 3: Narration Script with Timestamps

Written AFTER the Playwright script is finalized, so narration matches screen events exactly.

### Workflow

```
1. Write demo script JSON (pre-computed responses)
2. Build demo backend mode (serve cached responses)
3. Write Playwright automation (exact screen actions)
4. Run Playwright → produces screen recording + timestamp log
5. Write narration text synced to timestamp log
6. Generate AI narration audio
7. Combine in video editor: recording + narration + stock footage + music
8. Review, adjust timing, re-run if needed (deterministic = free re-takes)
```

---

## 8. Writeup Plan

### Structure (Under 1,500 Words)

```
Title: FieldPack AI — Offline Expert Knowledge for Humanitarian Field Workers
Subtitle: Gemma 4 agents curate mission-specific Knowledge Packs
         that an edge model serves without internet

Section 1: The Problem (150 words)
  - 3.7B without internet
  - Humanitarian workers, the knowledge gap
  - Amina's story (2 sentences)

Section 2: The Insight (100 words)
  - Offline AI has intelligence but no knowledge
  - Knowledge Packs: curate before deployment, serve offline

Section 3: Architecture (300 words)
  - Two-phase system: Online (cloud agents) → Offline (edge RAG)
  - Full Gemma 4 family usage (table: which model does what)
  - Agentic RAG pipeline diagram
  - Knowledge Pack format

Section 4: The Demo — Amina's Mission (300 words)
  - Walk through the full flow
  - Mission briefing → knowledge gathering → field deployment
  - Hero shot: plant photo → diagnosis → local treatment
  - Cite specific knowledge: CMD, TME 419 variety, neem oil

Section 5: Technical Depth (300 words)
  - LangGraph orchestration
  - Parent/child chunking + two-tier rerank
  - WebSocket streaming for token-by-token UX
  - ChromaDB persistent vector store
  - Ollama for local inference (mention prominently for prize)
  - Sentence-transformers MiniLM-L6-v2 for embeddings

Section 6: The Platform (150 words)
  - Same architecture, different pack
  - 5 example Knowledge Packs (table)
  - One built, five shown, infinite implied

Section 7: Impact (100 words)
  - Cassava feeds 800M people
  - 50% yield loss from disease in Sub-Saharan Africa
  - Cost: one laptop + one phone. No internet required.

Total: ~1,400 words (leaves 100-word buffer)
```

### Cover Image

The cover image is required and appears as the thumbnail on Kaggle. It should be:
- The hero shot: app screen showing plant diagnosis
- OR: a clean branded graphic with the FieldPack AI logo + tagline
- High resolution, landscape orientation

---

## 9. Live Demo Plan

Judges need a URL or files to try the demo themselves.

### Options

| Option | Pros | Cons | Effort |
|--------|------|------|--------|
| **Colab notebook** | Runs anywhere, Kaggle-native | Complex setup for judges | Medium |
| **Hosted demo (Railway/Render)** | Click and use | Costs money, needs Ollama hosting | High |
| **Demo mode on GitHub** | Download and run locally | Judges need Python/Node | Medium |
| **Pre-recorded walkthrough + APK** | No infra needed | Not truly "live" | Low |

**Recommendation**: Provide BOTH:
1. The APK + local server setup instructions (the real thing)
2. A demo-mode Docker compose that runs without Ollama (demo backend serves cached responses — same system we use for video recording)

The demo-mode Docker option lets judges experience the real UI without needing a GPU or Ollama installed.

---

## 10. Media Gallery Plan

Required: cover image. Recommended: additional screenshots showing key features.

| Image | Content | Purpose |
|-------|---------|---------|
| **Cover image** | FieldPack AI logo + hero shot composite | Kaggle thumbnail |
| **Screenshot 1** | Mission briefing screen with agent progress | Shows online phase |
| **Screenshot 2** | Plant diagnosis with streaming response | The hero shot |
| **Screenshot 3** | Source citations expanded | Shows grounded, verifiable AI |
| **Screenshot 4** | Knowledge Pack grid (5 packs) | Platform vision |
| **Architecture diagram** | Cloud → Pack → Device flow | Technical credibility |

---

## 11. Production Timeline

Working backwards from May 18, 2026 deadline.

| Week | Dates | Focus | Deliverable |
|------|-------|-------|-------------|
| **Week 1** | Apr 14–20 | Demo system | Demo backend mode + Playwright script + demo JSON |
| **Week 2** | Apr 21–27 | Video production | Screen recording + narration script + AI audio + editing |
| **Week 3** | Apr 28–May 4 | Writeup + assets | Kaggle writeup draft + cover image + screenshots + architecture diagram |
| **Week 4** | May 5–11 | Live demo + polish | Docker demo mode + GitHub README polish + test everything |
| **Week 5** | May 12–18 | Submit + buffer | Final review, re-record if needed, submit by May 16 (2-day buffer) |

### Critical Path

```
Demo backend → Playwright script → Screen recording → Narration sync → Video edit → Upload
     ↓                                                                        ↓
Demo JSON (pre-written responses)                               Writeup (can parallel)
```

The demo backend is the bottleneck. Everything downstream depends on it.

---

## Appendix: Reference Links

### Competition
- [Gemma 4 Good Hackathon — Kaggle](https://www.kaggle.com/competitions/gemma-4-good-hackathon)

### Previous Winners
- [Google Blog — Winners Announcement](https://blog.google/technology/developers/developers-changing-lives-with-gemma-3n/)
- [Better-ed Post-Mortem](https://better-ed.ai/blog/gemma-3n-better-ed)
- [Vite Vere GitHub](https://github.com/guidomarangoni/vite-vere-offline)
- [Better-ed Demo Video](https://www.youtube.com/watch?v=Vo9NvaV4hAk)

### Tools
- [ElevenLabs (AI narration)](https://elevenlabs.io/)
- [Playwright (browser automation)](https://playwright.dev/)
- [DaVinci Resolve (free video editor)](https://www.blackmagicdesign.com/products/davinciresolve)
- [Pexels (free stock footage)](https://www.pexels.com/)
- [Pixabay (free stock footage)](https://pixabay.com/)
