# Phone-Hero Images

Five phone-UI stills extracted from `demo/video/final.mp4` (1920x1080, 30fps, 180s).
Crop box applied to every frame: `x=[1306..1770]` (464px wide), `y=[30..1050]` (1020px tall) — the right-pane phone UI only, no slide content, no mockup bezel.

## Images

### 01-diagnosis-result.png
- Source: frame 4170, t = 139.0s
- Scene 12 — the hero shot
- Caption: Full Diagnosis Result screen for Cassava Mosaic Disease: 92% confidence arc, High Severity + Viral badges, four matched symptoms (yellow mosaic, leaf curling, stunted growth), and recommended treatment "Remove infected plants" with follow-up chips.
- Why picked: This is THE hero image. A judge scrolling the README sees the complete offline outcome — photo in, specific disease out, with confidence, symptoms, and an action plan. It directly evidences the non-negotiable from `CLAUDE.md`: "plant photo → diagnosis → treatment plan."

### 02-offline-field-answer.png
- Source: frame 3450, t = 115.0s
- Scene 11 — first offline interaction
- Caption: Field AI chat answering "When should I plant cassava in Casamance this season?" with a locally grounded, multi-paragraph response covering planting windows (June–July), land prep, spacing, variety recommendation (TME 419 from ISRA nurseries in Ziguinchor), and weeding schedule.
- Why picked: Shows agentic RAG streaming a long, specific, source-grounded answer on-device — proving the "offline is the point" value. Lots of readable text = shows the system *works*, not just a UI.

### 03-mission-brief.png
- Source: frame 2220, t = 74.0s
- Scene 8 — Online mission-chat phase
- Caption: Mission planner chat showing the compiled Mission Brief card: Region (Casamance, Senegal), Crops (Cassava, Rice), Season (Rainy Jun–Oct), Focus chips (Disease ID, Treatment Protocols, Farming Calendar, Pest Management), scale estimate, with "Dispatch Agents" CTA.
- Why picked: Represents Phase 1 (online prep). Proves the two-phase architecture by showing the AI *understanding* a mission before compiling the pack — a judge sees that this is more than a chatbot.

### 04-field-home.png
- Source: frame 3060, t = 102.0s
- Scene 11 entry — Field AI landing
- Caption: Field AI home in offline mode with header "Casamance, Senegal · 6 crops · 190 entries · 6 sources" and four use-case cards: Diagnose a plant, Pest control, Planting guide, Irrigation advice.
- Why picked: Clean, photogenic landing state. Communicates scope (190 entries, 6 sources) and capability surface area in one glance. Good "establishing shot" for the README above the detail screens.

### 05-knowledge-packs.png
- Source: frame 4710, t = 157.0s
- Scene 14 — Platform vision
- Caption: Knowledge Packs library listing the active Casamance Agriculture Pack — 6 crops, 190 knowledge entries, 6 expert sources, with crop chips (Cassava, Rice, Maize, Groundnut, Tomato, Millet) and a "Create New Pack" affordance.
- Why picked: Shows the platform concept — packs are swappable artifacts, not hardcoded. Matches the "One Pack shipped, platform in concept" positioning in `CLAUDE.md`.

## Pipeline notes

- Candidates: 180 (1 per second at 30 fps)
- After sharpness/richness filter + pHash dedup: 19 distinct frames
- All 5 picks were taken from the deduped set; no motion-blurred, spinner-covered, or mid-transition frames were retained.
- Sharpness floor: variance-of-Laplacian >= 150. Richness floor: grayscale std >= 25.
- Reproducible: `_work/extract.py` and `_work/pick.py` regenerate the set end-to-end.
