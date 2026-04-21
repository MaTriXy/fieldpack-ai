# Kaggle Notebook — Description (copy-paste)

**Title:** FieldPack AI — Offline Expert Knowledge for Humanitarian Field Workers

**Subtitle:** Big Gemma 4 models research the mission. An edge model goes into the field with the knowledge they curated.

---

## Description (180 words — lead draft)

A laptop, a phone, a sick cassava plant, no internet — and a full diagnosis in five seconds.

Amina Diallo is an agronomist with Action Against Hunger, deployed to the Casamance region of Senegal. A farmer hands her a cutting with curled, yellowing leaves. No signal. No cell tower. No cloud. She photographs it. Her phone streams back: *Cassava Mosaic Disease. Moderate severity. Use TME 419 — available at the extension service in Ziguinchor. Intercrop with maize. Apply neem oil.*

FieldPack AI is a two-phase Gemma 4 system for humanitarian field workers. **Before the mission**, cloud-tier Gemma 4 agents (31B + 26B MoE) on Google AI Studio curate a mission-specific *Knowledge Pack* — structured data, semantic vectors, reference images, ~200 MB. **In the field**, Gemma 4 E2B runs offline on a laptop via Ollama and serves that pack to a phone over a local WiFi hotspot through an agentic LangGraph RAG pipeline.

One pack shipping: Casamance agriculture — 5 crops, 15 diseases, 190 curated entries. The architecture is domain-agnostic: disaster triage, rural literacy, wildlife conservation — any mission, any domain.

*The value of offline AI is not the model. It is the knowledge the model carries.*

📱 APK + 60-second Docker setup in the writeup · 🎥 3-min demo: youtu.be/y9FSAkYpFII · 🌍 Track: Global Resilience · Impact + Special Technology
