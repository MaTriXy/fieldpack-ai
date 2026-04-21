# FieldPack AI — Project Philosophy

> "Same architecture. Different knowledge pack. Any mission. Anywhere. Offline."

---

## Table of Contents

1. [The Competition We Are Entering](#1-the-competition-we-are-entering)
2. [What Won Before — And Why](#2-what-won-before--and-why)
3. [The Insight That Drives This Project](#3-the-insight-that-drives-this-project)
4. [What We Are Building](#4-what-we-are-building)
5. [Why This Specific Idea](#5-why-this-specific-idea)
6. [The Human Story We Are Telling](#6-the-human-story-we-are-telling)
7. [The Judging Criteria — And How We Win Each One](#7-the-judging-criteria--and-how-we-win-each-one)
8. [Strategic Positioning Against the Field](#8-strategic-positioning-against-the-field)
9. [The LinkedIn & Video Strategy](#9-the-linkedin--video-strategy)
10. [What Success Looks Like](#10-what-success-looks-like)
11. [Non-Negotiable Principles](#11-non-negotiable-principles)

---

## 1. The Competition We Are Entering

### The Gemma 4 Good Hackathon

- **Host**: Kaggle, in official partnership with Google DeepMind
- **Prize Pool**: $200,000 USD
- **Final Submission Deadline**: May 18, 2026
- **Competition URL**: https://www.kaggle.com/competitions/gemma-4-good-hackathon

### The Mission Statement

Google and Kaggle are asking one question: *Can you use Gemma 4's new capabilities — multimodal understanding, native function calling, and edge deployment — to solve real-world challenges that actually matter?*

### The Three Tracks

| Track | Focus | What They Want to See |
|-------|-------|----------------------|
| **Health & Sciences** | Medical, biological, scientific applications | Edge-based models improving healthcare access |
| **Global Resilience** | Climate, agriculture, disaster, sustainability | Solutions for communities facing environmental crisis |
| **Future of Education & Digital Equity** | Learning, literacy, access to knowledge | AI closing the gap for underserved populations |

### What They Gave Us to Build With

Gemma 4 is a family of four models released under Apache 2.0 (fully open, commercially permissive):

- **E2B** (2.3B active params) — Runs on smartphones. Handles text, images, video, AND audio. 128K context.
- **E4B** (4.5B active params) — Same targets, higher quality. Handles text, images, video, AND audio. 128K context.
- **26B MoE** (4B active per inference out of 26B total) — Near-frontier quality. 256K context. No audio.
- **31B Dense** (full 31B params) — Ranked #3 open model in the world. 256K context. No audio.

All models support native function calling, structured JSON output, and system instructions. The edge models are purpose-built to run without cloud connectivity. The large models are purpose-built for agentic, multi-step reasoning.

This is not a coincidence. Google designed this model family as a pipeline: **big models think, edge models act.** Our project is the purest expression of that design intent.

### Submission Requirements (Based on Kaggle Hackathon Standards)

From previous Gemma hackathons and Kaggle community hackathon norms, we expect:

1. **Kaggle Writeup** — Title, subtitle, detailed narrative (typically under 1,500 words). Must include a cover image.
2. **Public Kaggle Notebook** — Reproducible code showing the full pipeline.
3. **YouTube Video** — 3 minutes or less. This is where hackathons are won or lost. The video IS the first impression.
4. **Working Demo** — The project must actually function, not just be slides.

---

## 2. What Won Before — And Why

### The Gemma 3n Impact Challenge (Previous Hackathon)

The most recent comparable competition. 600+ submissions. $150,000 prize pool. 8 winners selected. Here is what won, and more importantly, **why** it won:

#### Winner Analysis

| Project | What It Did | Track | Why It Won |
|---------|-------------|-------|------------|
| **Vite Vere** | Offline companion for people with cognitive disabilities. Turns images into simple spoken instructions. Works without internet via MediaPipe LLM Inference API. | Accessibility | **Offline-first design. Hyper-specific user. Undeniable human impact.** |
| **LENTERA** | Transforms cheap hardware into offline WiFi microservers running Gemma 3n via Ollama. Broadcasts AI-powered educational hubs in disconnected regions. | Education / Equity | **Infrastructure-level thinking. Not an app — a platform. Offline-first.** |
| **Sixth Sense** | Real-time security camera analysis. YOLO-NAS detects objects, Gemma 3n provides human-level context to distinguish threats from benign events. | Safety / Practical | **Multimodal pipeline (vision + reasoning). Clear practical value.** |
| **Gemma Vision** | Chest-mounted phone camera for visually impaired users. AI describes surroundings via voice. | Accessibility | **Simple concept, flawless execution. One clear user story.** |
| **3VA** | Fine-tuned Gemma 3n to translate pictograms into rich language for a user with cerebral palsy. | Accessibility | **Deeply personal. Fine-tuning showcase. The story writes itself.** |
| **Dream Assistant** | Trained on an individual's audio recordings to understand their unique speech patterns (speech impairment). | Accessibility | **Personalization at its most meaningful. Technical + emotional.** |
| **Better-ed** | Voice-based educational assessment platform. Works offline, syncs when online. Paired with Unsloth for performance. | Education | **Practical classroom tool. Tested against simulated student personas.** |

#### The Winning Pattern — Five Rules

**Rule 1: Offline/Edge Was King**
Vite Vere and LENTERA both won *specifically because* they worked without internet. This is not optional — it is the competitive advantage Google designed into these models. Projects that treat edge deployment as an afterthought will lose to projects that make it the centerpiece.

**Rule 2: One User, One Story**
Not "everyone." Not "farmers worldwide." Not "students in developing countries." Every winner had a specific human you could picture: a person with cerebral palsy communicating through pictograms. A security guard on a night shift. A visually impaired person walking down a street. The specificity IS the impact.

**Rule 3: The Demo Tells the Story in Under 60 Seconds**
Judges watch hundreds of submissions. They decide in the first minute. If your demo needs explanation, you have already lost. Every winner had a moment — a single interaction — that made the value self-evident.

**Rule 4: Technical Depth Serves the User, Never the Other Way Around**
No winner showcased technology for its own sake. Fine-tuning, multimodal pipelines, offline inference — these were means to an end. The end was always a human being whose life got measurably better. The technique was invisible to the user and visible only to the judges reading the writeup.

**Rule 5: Creativity, Usability, and Inclusivity Over Raw Metrics**
Direct quote from Better-ed's post-competition analysis: the competition emphasized *"creativity, usability, and inclusivity"* rather than purely technical metrics. This means a polished, usable, inclusive tool beats a technically superior but unusable one.

---

## 3. The Insight That Drives This Project

### The Problem Nobody Has Solved

There are 3.7 billion people on Earth without reliable internet access. Among them are:
- Humanitarian workers deployed to crisis zones
- Agricultural extension officers in rural Sub-Saharan Africa
- Community health workers in remote villages
- Disaster responders after infrastructure collapse
- Teachers in schools without connectivity

These people need expert-level knowledge to do their jobs. Today, they either carry printed reference materials (outdated the moment they're printed), rely on their memory (limited and error-prone), or simply go without (and people suffer for it).

AI could solve this. But AI requires internet. And these people don't have internet.

### The Gap in the Market

Offline AI exists. You can run a model on a phone. But here's what's missing:

**Current offline AI = a general model with no domain knowledge.**

It's like deploying a doctor to a malaria zone with a medical degree but no information about malaria. The intelligence is there. The knowledge is not.

### Our Core Insight

> **The value of offline AI is not the model. It is the knowledge the model carries.**

This is the idea that separates us from every other submission. We are not building "an offline chatbot." We are building a system that **curates mission-specific knowledge using powerful cloud models, packages it into a portable database, and deploys it with an edge model that can navigate that knowledge intelligently — all without internet.**

We call these portable knowledge databases **"Knowledge Packs."**

---

## 4. What We Are Building

### FieldPack AI

A two-phase AI system that transforms powerful cloud intelligence into portable, offline, domain-specific field assistants.

### Phase 1: Online — "Mission Briefing" (Cloud, Gemma 4 31B/26B)

The user describes their upcoming mission in natural language:

> *"I'm deploying to the Casamance region of Senegal next week. Smallholder farmers are dealing with cassava mosaic disease, brown streak, and a severe drought season. I need to help them identify crop diseases, recommend treatments with locally available materials, and advise on drought-resistant planting strategies."*

The system responds with intelligence:

1. **Mission Planner Agent** (31B) interprets the request, identifies the knowledge domains needed, and creates a research plan.
2. **Parallel Research Agents** (26B MoE, multiple instances) fan out and gather data:
   - Crop disease databases for the specific region
   - Treatment protocols using locally available materials
   - Climate data and drought forecasting for Casamance
   - Reference images of healthy vs. diseased crops
   - Soil management and water conservation techniques
   - Local crop calendars and planting schedules
3. **Knowledge Compiler Agent** (31B) receives all research, deduplicates, validates, structures it into a hybrid database (structured data + semantic search + reference images), and packages it as a single downloadable Knowledge Pack.

The user downloads the Knowledge Pack. It is a single portable file — a few hundred megabytes containing everything they need.

### Phase 2: Offline — "Field Assistant" (Edge, Gemma 4 E2B)

The user is now in the field. No internet. They open the app.

The **Field Assistant Agent** (E2B, running locally on their device) has access to the Knowledge Pack through native function calling:

- `search_knowledge(query)` — semantic search through the vector store
- `identify_plant(image)` — analyze a photo using vision + reference image matching
- `get_treatment(disease_id)` — retrieve structured treatment protocols
- `check_climate(region, season)` — access local climate data
- `log_observation(data)` — record findings for later sync

**Example interaction:**

The user photographs a cassava plant with curled, yellowing leaves.

The agent processes the image. It recognizes leaf curl patterns consistent with Cassava Mosaic Disease. It cross-references with the local disease database. It pulls the treatment protocol. It checks what materials are locally available in Casamance. It responds:

> *"This appears to be Cassava Mosaic Disease (CMD), likely caused by the African cassava mosaic virus. Severity: moderate — the mosaic pattern covers approximately 40% of visible leaf area.*
>
> *Immediate action: Remove and burn this plant and any plants within 2 meters showing similar symptoms to prevent whitefly transmission.*
>
> *For replanting: Use CMD-resistant varieties — TME 419 or IITA-TMS-IBA30572 are available through the Senegalese agricultural extension service in Ziguinchor.*
>
> *Prevention: Plant clean stem cuttings from certified sources. Intercrop with maize to reduce whitefly density. Apply neem oil extract as a natural whitefly deterrent — neem trees are abundant in this region."*

This is not a generic chatbot answer. This is **curated, local, specific, actionable knowledge** — delivered without internet.

### The Platform Vision (What Makes This Bigger Than One Demo)

The Knowledge Pack architecture is domain-agnostic. The same system supports:

| Knowledge Pack | User | Mission |
|---------------|------|---------|
| **Casamance Agriculture Pack** | Humanitarian agronomist | Crop disease identification, drought strategy |
| **Disaster Medical Triage Pack** | First responder after earthquake | Injury assessment, triage protocols, drug dosing |
| **Rural Literacy Education Pack** | Teacher in off-grid school | Lesson plans, reading assessment, adaptive exercises |
| **Wildlife Conservation Pack** | Field researcher in rainforest | Species identification, habitat assessment, poaching detection |
| **Post-Conflict Infrastructure Pack** | Engineer assessing damaged buildings | Structural safety assessment, repair prioritization |

**We build one. We show five. We imply infinite.** This is what turns a hackathon project into something judges remember.

---

## 5. Why This Specific Idea

### Why It Wins — The Strategic Argument

Every design decision in this project is reverse-engineered from what wins hackathons. Here is the reasoning:

#### 5.1 It Uses the Full Gemma 4 Family — Purposefully

Most teams will use one model. We use all four tiers, each for what it's best at:

| Model | Role in Our System | Why This Model |
|-------|-------------------|----------------|
| 31B Dense | Mission Planner + Knowledge Compiler | Highest reasoning quality for planning and validation |
| 26B MoE | Parallel Research Agents | Best quality-per-compute ratio for parallelized work |
| E2B | Field Assistant (offline) | Smallest multimodal footprint (2.3B active params, ~8 GB RAM), fits on laptop for hotspot thin-client demo |
| E4B | Potential upgrade path for higher-quality vision | Same architecture, more capacity when hardware allows |

Judges will notice this. It shows we understood the model family as a system, not just picked the biggest one.

#### 5.2 It Targets the Least Crowded Track

The three tracks are Health, Global Resilience, and Education. We predict:
- **Health**: Most crowded. Every medical chatbot team will pile in here. MedGemma already has its own separate hackathon.
- **Education**: Second most crowded. Chatbot tutors are the default idea.
- **Global Resilience**: Least crowded. Agriculture and climate are less "obvious" applications. Less competition = better odds.

We are entering Global Resilience. With agriculture as our demo, we sidestep the bloodbath in Health and Education.

#### 5.3 It Is the Most Demo-Friendly Scenario Possible

Consider the alternatives:
- **Health AI**: One wrong diagnosis in the demo video and judges lose trust. Medical AI carries liability anxiety.
- **Education AI**: Text-heavy interactions. Hard to make visually compelling in a 3-minute video.
- **Agriculture AI**: User photographs a sick plant. App tells them exactly what's wrong and how to fix it. **This is a 5-second video hook that anyone on Earth understands instantly.**

The plant-photo-to-diagnosis moment is our "hero shot." It is visual, it is immediate, it is undeniable.

#### 5.4 It Cannot Harm Anyone If It's Wrong

A medical AI that gives wrong advice could kill someone. An educational AI that teaches wrong facts could miseducate children. An agricultural AI that misidentifies a disease? The farmer tries one treatment, it doesn't work, they try another. The stakes are meaningful but not dangerous. This makes judges comfortable rather than skeptical.

#### 5.5 It Has a Real, Specific, Picturable User

Not "farmers in Africa" (vague). Not "anyone without internet" (generic). Our user is:

> **Amina, an agronomist with Action Against Hunger, deploying to the Casamance region of Senegal for a 3-week field mission to help smallholder cassava and rice farmers survive a drought season complicated by mosaic virus outbreaks.**

Amina has a name. A job. A destination. A mission. A timeline. A problem. Judges will remember Amina.

#### 5.6 The Architecture Is Novel

No previous Kaggle Gemma hackathon winner has built a two-phase system where:
1. Large cloud models intelligently curate domain-specific knowledge
2. That knowledge is packaged into a portable database
3. An edge model navigates that knowledge offline using function calling

Previous offline winners (Vite Vere, LENTERA) used pre-baked models or pre-existing knowledge. Our system **generates custom knowledge on demand** using agentic workflows. This is a step-function more sophisticated.

#### 5.7 It Tells a Platform Story

Judges don't just evaluate what you built. They evaluate what you *could* build. By framing this as "Knowledge Packs" — a general architecture where agriculture is merely the first pack — we signal that this is a platform, not a toy. "This could be a company" is the sentence that wins grand prizes.

---

## 6. The Human Story We Are Telling

### The Narrative Arc (For Video and Writeup)

Every winning hackathon submission tells a story with this structure:

#### Act 1: The Problem (30 seconds)

> 3.7 billion people lack reliable internet. Among them are the people we count on most in a crisis — humanitarian workers, field researchers, teachers, health workers. They deploy to the world's hardest places carrying their training and their phone. Their phone has an AI model. But without internet, that model knows nothing about the specific crisis they're facing.

**Visual**: Montage of connectivity maps. Rural landscapes. A humanitarian worker looking at a phone with no signal bars.

#### Act 2: The Insight (15 seconds)

> What if the AI could prepare for the mission before you lose connectivity? What if a team of powerful AI agents could research your specific mission, compile everything you need into a portable knowledge pack, and hand it to an edge AI that goes with you into the field?

**Visual**: Animation showing cloud → knowledge pack → device.

#### Act 3: The Demo (90 seconds)

> Meet Amina. She's an agronomist deploying to Senegal's Casamance region. Before she leaves, she tells FieldPack AI about her mission...

Show the online phase. Show the knowledge gathering. Show the download. Show her going offline. Show her photographing a sick cassava plant. Show the diagnosis. Show the treatment plan. Show the locally-specific advice.

**Visual**: Screen recording of the actual working demo intercut with stock footage of the scenario.

#### Act 4: The Vision (30 seconds)

> Agriculture is just the first Knowledge Pack. The same architecture supports disaster medical triage, rural education, wildlife conservation, infrastructure assessment — any mission where an expert needs knowledge and doesn't have internet.

**Visual**: Grid showing 5 different Knowledge Packs. Quick flashes of each use case. End on logo.

---

## 7. The Judging Criteria — And How We Win Each One

Based on analysis of previous Kaggle Gemma hackathons and Kaggle community hackathon standards, submissions are evaluated on these dimensions. Here is how we score on each:

### 7.1 Impact and Real-World Value

**What judges ask**: *"Does this solve a real problem for real people?"*

**How we score**: Maximum. 3.7 billion people without internet. Humanitarian workers are a real, identifiable user base. Cassava is the primary food source for 800 million people. Crop disease causes up to 50% yield loss in Sub-Saharan Africa. This is not hypothetical. This is happening right now.

**What we show**: The problem is stated in numbers. The user is named and specific. The solution is demonstrated working.

### 7.2 Innovation and Novelty

**What judges ask**: *"Have I seen this before? Is there a new idea here?"*

**How we score**: Maximum. The two-phase architecture (cloud knowledge curation → offline edge deployment) has never been done in a Kaggle hackathon. The "Knowledge Pack" concept — a portable, AI-curated, domain-specific database — is genuinely original. The use of the full Gemma 4 model family as a coordinated system (big models research, edge models serve) is the most natural and novel use of the model lineup.

**What we show**: Architecture diagram in the writeup. The writeup explicitly names what is new and why.

### 7.3 Technical Execution

**What judges ask**: *"Does the code actually work? Is the implementation solid?"*

**How we score**: High. We demonstrate:
- Parallel agentic workflows (multiple research agents operating concurrently)
- Native function calling (both in cloud agents and edge agent)
- Multimodal processing (image analysis for plant disease identification)
- Hybrid database design (vector search + structured SQL + image matching)
- Edge deployment (model running offline on device)

**What we show**: Public Kaggle notebook with reproducible code. The demo video shows the system running end-to-end.

### 7.4 Creativity and Usability

**What judges ask**: *"Is the solution creative? Could a real user actually use this?"*

**How we score**: High. The interaction is natural language — the user describes their mission conversationally. The offline agent responds conversationally. Image upload is point-and-shoot. There is no complex UI to learn. A humanitarian worker with basic smartphone literacy can use this immediately.

**What we show**: The video shows a smooth, intuitive user flow. No menus, no jargon, no configuration.

### 7.5 Presentation and Storytelling

**What judges ask**: *"Is the writeup clear? Is the video compelling? Do I remember this project?"*

**How we score**: Maximum. The Amina story is our weapon. The plant-photo-to-diagnosis moment is our hero shot. The platform vision (five Knowledge Packs on one slide) is our closer. The video follows the problem → insight → demo → vision arc that every great pitch uses.

**What we show**: 3-minute video with narrative structure. Writeup with clear sections, architecture diagrams, and the human story front and center.

### 7.6 Use of Gemma 4 Capabilities

**What judges ask**: *"Did they actually leverage what makes Gemma 4 special, or could they have done this with any model?"*

**How we score**: Maximum. This project could NOT be built with any other model family. It specifically requires:
- **Large models with agentic capabilities** (31B/26B for knowledge gathering via function calling)
- **Edge models with multimodal support** (E2B for offline image analysis)
- **The full model family working as a system** (cloud → edge pipeline)
- **Native function calling** (the edge agent uses tool calls to query the local database)
- **Apache 2.0 licensing** (the Knowledge Pack concept requires full redistribution rights)

No other open model family offers this combination. We are building something that could only exist because Gemma 4 exists. This is exactly what Google wants to see.

### 7.7 Reproducibility

**What judges ask**: *"Can I run this myself?"*

**How we score**: High. The entire pipeline runs in Kaggle notebooks (online phase) and on any machine with enough RAM for E2B (offline phase). Dependencies are standard Python libraries. The Knowledge Pack format is documented. The Kaggle notebook is public and annotated.

---

## 8. Strategic Positioning Against the Field

### What Other Teams Will Build (Predicted)

Based on the hackathon tracks and common hackathon patterns:

| Category | Predicted Volume | Typical Approach | Why We Beat Them |
|----------|-----------------|------------------|------------------|
| Medical chatbots | Very High | RAG over medical texts using 31B | We have a more novel architecture. Medical chatbots are commodity. |
| Education tutors | High | 31B or 26B chatbot with curriculum data | Text-heavy, hard to demo. Our visual demo is more memorable. |
| Climate dashboards | Medium | Data analysis + visualization with Gemma | Analysis tools, not field tools. Our system works where dashboards can't — offline. |
| Translation tools | Medium | Fine-tuned Gemma for low-resource languages | Useful but narrow. We solve a broader problem. |
| Accessibility tools | Medium | Following Gemma 3n winners' playbook | Already won last time. Judges will look for something new. |
| Generic offline chatbots | Low-Medium | Edge model with no knowledge curation | This is our direct competitor, but without the Knowledge Pack architecture, they're just a model running offline with no domain knowledge. We render them obsolete. |

### Our Unique Position

We sit in a space no one else occupies: **the intersection of agentic cloud intelligence and offline edge deployment, connected by a knowledge transfer mechanism.**

Every other team will use either cloud OR edge. We use both, in sequence, with an intelligent handoff. This is unique.

---

## 9. The LinkedIn & Video Strategy

### The LinkedIn Post

The LinkedIn post is as important as the hackathon submission for the user's broader goals. Here is the philosophy:

#### The Hook (First 2 Lines — Before "See More")

The first two lines must stop the scroll. They must create tension or surprise.

> *"We built an AI that gets smarter BEFORE it goes offline."*
> *"Here's how we're giving expert agricultural knowledge to farmers who have never had internet."*

#### The Story Structure

1. **Problem** (2 sentences): 3.7 billion people without internet. Humanitarian workers deploy with knowledge gaps.
2. **Insight** (1 sentence): What if AI could prepare for the mission before losing connectivity?
3. **What we built** (3-4 sentences): Two-phase system. Cloud agents gather knowledge. Edge model serves it offline. Plant photo → diagnosis.
4. **Results / Demo** (embed video or GIF): The hero shot — plant photo to diagnosis.
5. **The bigger vision** (1-2 sentences): Knowledge Packs for any domain.
6. **Call to action**: Link to the Kaggle writeup. Invite discussion.

#### Timing

Post the day results are announced (if we win) or the day after submission deadline (to get visibility regardless of outcome). Tag @Kaggle, @GoogleDeepMind, use #Gemma4, #AIForGood, #Hackathon.

### The Video (3-Minute Submission)

**Minute 0:00–0:30**: The problem. Connectivity maps. Rural footage. The gap.
**Minute 0:30–0:45**: The insight. Our approach in one sentence. Architecture animation.
**Minute 0:45–2:15**: The demo. Online phase (sped up, narrated). Knowledge Pack download. Go offline. The hero shot — photograph a plant, get diagnosis. Show follow-up conversation. Show the agent using function calling in real-time.
**Minute 2:15–2:45**: The platform vision. Five Knowledge Packs. Other use cases. One slide.
**Minute 2:45–3:00**: Closing. Team. Thank you. Links.

---

## 10. What Success Looks Like

### Primary Goal: Win the Hackathon

This means placing in the top tier of the Global Resilience track, ideally winning the track outright or being selected as an overall standout project.

### Secondary Goal: LinkedIn Virality

The project, video, and writeup should generate meaningful engagement on LinkedIn — demonstrating the team's AI engineering capability and social impact thinking to a professional audience.

### Tertiary Goal: A Project Worth Continuing

If the architecture works as designed, FieldPack AI is genuinely useful beyond the hackathon. It could be open-sourced, adopted by humanitarian organizations, or developed into a startup. We should build it as if it will outlive the competition.

### How We Know We've Won (Internal Success Metrics)

Before submitting, we should be able to answer YES to all of these:

- [ ] **The hero shot works flawlessly.** A user photographs a plant, the offline agent correctly identifies the disease and provides a locally-specific treatment plan.
- [ ] **The online knowledge gathering is visibly intelligent.** The parallel agents gather non-trivial, domain-specific data. The Knowledge Pack contains structured, validated, useful information — not generic text dumps.
- [ ] **The offline agent uses function calling, not just text generation.** It queries the database. It looks up structured data. It cross-references. This is visible in the demo.
- [ ] **The video tells Amina's story in under 3 minutes.** A viewer who knows nothing about AI should understand the value by minute 1.
- [ ] **The writeup is clear, concise, and under 1,500 words.** It leads with impact, not technology. The architecture diagram is readable. The human story is on the first page.
- [ ] **The Kaggle notebook is public and runs.** A judge can reproduce our results.
- [ ] **The platform vision is stated but not overpromised.** We built one Knowledge Pack. We show the architecture supports many. We do not claim we built all of them.

---

## 11. Non-Negotiable Principles

These are the rules we do not break, regardless of time pressure or technical obstacles:

### 11.1 The Demo Must Work

A beautiful writeup with a broken demo loses to an ugly writeup with a working demo. Every single time. If we have to cut features to make the core flow work flawlessly, we cut features. The hero shot (plant photo → diagnosis) must work every time, not sometimes.

### 11.2 Impact First, Technology Second

Every decision is evaluated through the lens of: *"Does this make the tool more useful for Amina in the field?"* If the answer is no, we don't build it. We do not add technical complexity to impress judges. We add technical complexity because the user needs it.

### 11.3 Narrow Execution, Broad Vision

We build one Knowledge Pack (Casamance agriculture). We do not attempt to build two. We do not attempt to build a general-purpose platform. We build one scenario to perfection, and we SHOW the platform vision through architecture and a single slide. The breadth is in the pitch. The depth is in the code.

### 11.4 Offline Is Not a Feature — It Is the Point

Every other team will treat edge deployment as a nice-to-have. For us, offline operation is the entire reason this project exists. The Knowledge Pack concept only makes sense because there is no internet. The agentic RAG only matters because there is no cloud to fall back on. If we find ourselves building features that require connectivity, we are going in the wrong direction.

### 11.5 The Story Is as Important as the Code

We are not just submitting code. We are submitting a narrative. Amina. Casamance. Cassava mosaic disease. The photograph. The diagnosis. The treatment with locally available neem oil. Every element of this narrative is deliberate and must be maintained through the writeup, the video, and the demo.

### 11.6 We Use the Full Model Family — On Purpose

Our architecture must justify using multiple Gemma 4 model sizes. If we find ourselves only using one model, we are missing the point. The 31B/26B plan and research. The E2B serves in the field. This is the natural use of the model family, and judges will recognize it.

### 11.7 Respect the Time Constraint

The deadline is May 18, 2026. We have approximately 6 weeks. Every architectural decision must pass the test: *"Can we build this to demo quality in the time we have?"* Ambition is good. Overcommitting is fatal. When in doubt, simplify.

---

## Appendix: Key References

### Competition
- [Gemma 4 Good Hackathon — Kaggle](https://www.kaggle.com/competitions/gemma-4-good-hackathon)
- [Kaggle announcement tweet](https://x.com/kaggle/status/2039740198259462370)
- [Gemma 4 models on Kaggle Benchmarks](https://x.com/kaggle/status/2039763598768066774)

### Previous Winners
- [Gemma 3n Impact Challenge Winners — Google Blog](https://blog.google/technology/developers/developers-changing-lives-with-gemma-3n/)
- [Winners announcement thread](https://x.com/googleaidevs/status/1998808731870797875)
- [Better-ed post-competition analysis](https://better-ed.ai/blog/gemma-3n-better-ed)

### Gemma 4 Technical Details
- [HuggingFace: Welcome Gemma 4](https://huggingface.co/blog/gemma4)
- [DEV.to: Gemma 4 — Everything Developers Need to Know](https://dev.to/om_shree_0709/google-gemma-4-everything-developers-need-to-know-3daf)
- [Google Blog: Gemma 4](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/)

### Hackathon Strategy
- [GenAI Hackathon Lessons Learned — Towards Data Science](https://towardsdatascience.com/things-i-learnt-by-participating-in-genai-hackathons-over-the-past-6-months/)
- [Kaggle Hackathon Evaluation Landscape — Gabriel Preda](https://medium.com/@gabi.preda/from-algorithms-to-hackathons-the-evolving-landscape-of-kaggle-competitions-17960e0035b8)
