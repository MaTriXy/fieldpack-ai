"""ChromaDB seed chunks for the Casamance Agriculture Knowledge Pack.

Parent/child pairs for all 4 collections. Per disease: 3 pairs
(symptoms, treatment, prevention). Plus farming practices and regional context.

Child chunks: short, keyword-rich, written as a farmer would describe it.
Parent chunks: full detailed information for the LLM to generate answers from.
"""

from app.knowledge_pack.seed_data import CROPS, DISEASES, TREATMENTS


def _crop_name_for_disease(disease_id: int) -> str:
    """Get the crop name for a disease based on seed data mapping."""
    from app.knowledge_pack.seed_data import CROP_DISEASES
    for cd in CROP_DISEASES:
        if cd["disease_id"] == disease_id:
            for crop in CROPS:
                if crop["id"] == cd["crop_id"]:
                    return crop["name"]
    return "unknown"


def _make_id(entity: str, disease_id: int, topic: str, chunk_type: str) -> str:
    """Generate a human-readable document ID."""
    return f"{entity}_{disease_id:03d}_{topic}_{chunk_type}"


def _get_disease_chunks() -> dict[str, list[dict]]:
    """Generate parent/child pairs for disease_knowledge and treatment_guides."""
    disease_knowledge = []
    treatment_guides = []

    for disease in DISEASES:
        d_id = disease["id"]
        crop = _crop_name_for_disease(d_id)
        short_name = disease["name"].lower().replace(" ", "_")[:20]
        severity = disease.get("severity_scale", "medium")
        d_type = disease.get("type", "unknown")

        # --- SYMPTOMS pair (disease_knowledge collection) ---
        symptoms_child_text = (
            f"My {crop} plant looks sick. {disease['visual_markers'][:200]}"
        ).strip()

        disease_knowledge.append({
            "id": _make_id(short_name, d_id, "symptoms", "child"),
            "content": symptoms_child_text,
            "metadata": {
                "disease_id": str(d_id),
                "crop": crop,
                "type": d_type,
                "severity": severity,
                "topic_id": f"{short_name}_{d_id:03d}_symptoms",
                "chunk_type": "child",
            },
        })

        symptoms_parent_text = (
            f"{disease['name']}\n"
            f"Type: {d_type}\n"
            f"Severity: {severity}\n"
            f"Crops affected: {crop}\n\n"
            f"Symptoms:\n{disease['symptoms_text']}\n\n"
            f"Visual identification:\n{disease['visual_markers']}\n\n"
            f"How it spreads:\n{disease.get('spread_mechanism', 'Unknown')}"
        )

        disease_knowledge.append({
            "id": _make_id(short_name, d_id, "symptoms", "parent"),
            "content": symptoms_parent_text,
            "metadata": {
                "disease_id": str(d_id),
                "crop": crop,
                "type": d_type,
                "severity": severity,
                "topic_id": f"{short_name}_{d_id:03d}_symptoms",
                "chunk_type": "parent",
            },
        })

        # --- PREVENTION pair (disease_knowledge collection) ---
        prevention_notes = disease.get("prevention_notes", "")
        if prevention_notes:
            prevention_child_text = (
                f"How to prevent {disease['name'].lower()} in {crop}. "
                f"{prevention_notes[:150]}"
            ).strip()

            disease_knowledge.append({
                "id": _make_id(short_name, d_id, "prevention", "child"),
                "content": prevention_child_text,
                "metadata": {
                    "disease_id": str(d_id),
                    "crop": crop,
                    "type": d_type,
                    "severity": severity,
                    "topic_id": f"{short_name}_{d_id:03d}_prevention",
                    "chunk_type": "child",
                },
            })

            prevention_parent_text = (
                f"Prevention of {disease['name']}\n"
                f"Crop: {crop}\n\n"
                f"{prevention_notes}\n\n"
                f"Disease type: {d_type}\n"
                f"Spread mechanism: {disease.get('spread_mechanism', 'Unknown')}"
            )

            disease_knowledge.append({
                "id": _make_id(short_name, d_id, "prevention", "parent"),
                "content": prevention_parent_text,
                "metadata": {
                    "disease_id": str(d_id),
                    "crop": crop,
                    "type": d_type,
                    "severity": severity,
                    "topic_id": f"{short_name}_{d_id:03d}_prevention",
                    "chunk_type": "parent",
                },
            })

        # --- TREATMENT pairs (treatment_guides collection) ---
        disease_treatments = [t for t in TREATMENTS if t["disease_id"] == d_id]
        for treat in disease_treatments:
            t_id = treat["id"]
            t_short = treat["method"].lower().replace(" ", "_")[:20]

            treatment_child_text = (
                f"How to treat {disease['name'].lower()} in {crop}. "
                f"{treat['method']}. {treat['description'][:120]}"
            ).strip()

            treatment_guides.append({
                "id": _make_id(t_short, t_id, "treatment", "child"),
                "content": treatment_child_text,
                "metadata": {
                    "disease_id": str(d_id),
                    "treatment_id": str(t_id),
                    "is_organic": str(treat.get("is_organic", True)).lower(),
                    "difficulty": treat.get("difficulty", "medium"),
                    "topic_id": f"{t_short}_{t_id:03d}_treatment",
                    "chunk_type": "child",
                },
            })

            treatment_parent_text = (
                f"Treatment: {treat['method']}\n"
                f"For: {disease['name']} in {crop}\n"
                f"Difficulty: {treat.get('difficulty', 'medium')}\n"
                f"Organic: {'Yes' if treat.get('is_organic') else 'No'}\n"
                f"Effectiveness: {treat.get('effectiveness', 'unknown')}\n\n"
                f"Description:\n{treat['description']}\n\n"
                f"Materials needed:\n{treat.get('materials_needed', '[]')}\n\n"
                f"Local availability:\n{treat.get('local_availability', 'Unknown')}\n\n"
                f"When to apply:\n{treat.get('application_timing', 'See description')}\n\n"
                f"Safety notes:\n{treat.get('safety_notes', 'None')}"
            )

            treatment_guides.append({
                "id": _make_id(t_short, t_id, "treatment", "parent"),
                "content": treatment_parent_text,
                "metadata": {
                    "disease_id": str(d_id),
                    "treatment_id": str(t_id),
                    "is_organic": str(treat.get("is_organic", True)).lower(),
                    "difficulty": treat.get("difficulty", "medium"),
                    "topic_id": f"{t_short}_{t_id:03d}_treatment",
                    "chunk_type": "parent",
                },
            })

    return {
        "disease_knowledge": disease_knowledge,
        "treatment_guides": treatment_guides,
    }


def _get_farming_practice_chunks() -> list[dict]:
    """Generate parent/child pairs for farming_practices collection."""
    practices = []

    entries = [
        {
            "topic": "drought_resistant_planting",
            "crop": "cassava",
            "season": "wet",
            "practice_type": "planting",
            "child": "How to plant cassava to survive drought in Casamance. Drought resistant varieties, planting timing, mulching, water conservation for cassava during dry spells.",
            "parent": (
                "Drought-Resistant Cassava Planting for Casamance\n\n"
                "Variety selection: Plant TME 419 or IITA-TMS-IBA30572 — both are CMD-resistant AND drought-tolerant. "
                "These varieties have deeper root systems and recover better after water stress.\n\n"
                "Planting timing: Plant at the start of the rainy season (mid-June) to maximize root establishment "
                "before dry spells. Early-planted cassava develops deeper roots.\n\n"
                "Mulching: Apply 10-15cm of grass or straw mulch around plants after establishment. "
                "Mulch conserves soil moisture, reduces temperature, and suppresses weeds.\n\n"
                "Spacing: Use 1m x 1m spacing — wider spacing means each plant accesses more soil moisture.\n\n"
                "Water harvesting: Create small basins around plants to capture rainwater. "
                "On slopes, plant along contour lines with tied ridges to prevent runoff."
            ),
        },
        {
            "topic": "soil_management",
            "crop": "general",
            "season": "all",
            "practice_type": "soil",
            "child": "How to improve soil fertility in Casamance without expensive fertilizers. Composting, mulching, crop rotation, green manure, wood ash for soil improvement.",
            "parent": (
                "Soil Fertility Management for Casamance Smallholders\n\n"
                "Composting: Collect crop residues, animal manure, kitchen waste. Layer in a pit 1m x 1m x 1m. "
                "Keep moist. Turn every 2 weeks. Ready in 2-3 months. Apply 2-3 tonnes per hectare.\n\n"
                "Crop rotation: Alternate cereals (maize, rice) with legumes (groundnut, cowpea). "
                "Legumes fix nitrogen — the following cereal crop benefits. Never plant the same crop twice.\n\n"
                "Green manure: Plant mucuna (velvet bean) or cowpea as cover crop at end of season. "
                "Cut and incorporate before next planting. Adds 60-80 kg nitrogen per hectare.\n\n"
                "Wood ash: Rich in potassium and calcium. Apply 1-2 kg per 10 square meters. "
                "Raises soil pH — beneficial for acidic Casamance soils. Free from cooking fires.\n\n"
                "Intercropping: Grow cereal-legume combinations. Maize + groundnut is ideal for Casamance."
            ),
        },
        {
            "topic": "planting_calendar",
            "crop": "general",
            "season": "wet",
            "practice_type": "planning",
            "child": "When to plant each crop in Casamance Senegal. Planting calendar, rainy season timing, what to plant first, crop scheduling for the year.",
            "parent": (
                "Casamance Planting Calendar\n\n"
                "JUNE (rains begin):\n"
                "- Mid-June: Plant maize and groundnut at first reliable rains\n"
                "- Late June: Plant cassava stem cuttings\n"
                "- Sow rice nursery beds\n\n"
                "JULY:\n"
                "- Transplant rice seedlings to paddy fields\n"
                "- Weed maize (critical — first weeding at 2 weeks)\n"
                "- Apply first groundnut fungicide at 45 days after planting\n\n"
                "AUGUST:\n"
                "- Second weeding all crops\n"
                "- Monitor for blast in rice (booting stage)\n"
                "- Earthing up groundnut for peg burial\n\n"
                "SEPTEMBER:\n"
                "- Maize harvest (90-day varieties)\n"
                "- Groundnut fungicide at 75 days\n"
                "- Rice grain filling — protect from birds\n\n"
                "OCTOBER:\n"
                "- Groundnut harvest (lift, dry, store)\n"
                "- Rice harvest\n"
                "- Prepare dry-season vegetable gardens\n\n"
                "NOVEMBER-MAY (dry season):\n"
                "- Irrigated tomato and vegetable production\n"
                "- Cassava harvest (ongoing, 8-18 months after planting)\n"
                "- Land preparation for next rainy season\n"
                "- Soil solarization for bacterial wilt management (March-May)"
            ),
        },
        {
            "topic": "integrated_pest_management",
            "crop": "general",
            "season": "all",
            "practice_type": "pest_control",
            "child": "Natural pest control methods for Casamance farmers. Neem oil, companion planting, traps, biological control without expensive chemicals.",
            "parent": (
                "Integrated Pest Management for Casamance\n\n"
                "Neem oil spray (universal insect deterrent):\n"
                "Crush 500g neem seeds, soak in 10L water overnight, strain through cloth, "
                "add few drops of soap. Spray on leaf undersides. Effective against whiteflies, "
                "aphids, leafhoppers, beetles. Reapply every 7-10 days and after rain.\n\n"
                "Companion planting:\n"
                "- Maize + cassava: taller maize blocks whitefly movement\n"
                "- Tomato + basil: basil repels whiteflies\n"
                "- Groundnut + maize: nitrogen fixation + different pest profiles\n\n"
                "Yellow sticky traps:\n"
                "Coat yellow plastic sheets with motor oil or petroleum jelly. "
                "Whiteflies and aphids attracted to yellow. Place at canopy height.\n\n"
                "Biological control:\n"
                "Encourage natural predators: ladybugs eat aphids, spiders catch many pests. "
                "Avoid broad-spectrum insecticides that kill beneficial insects.\n\n"
                "Cultural practices:\n"
                "Remove crop residues. Rotate crops. Plant early to avoid peak pest seasons."
            ),
        },
    ]

    for entry in entries:
        topic_id = f"practice_{entry['topic']}"
        practices.append({
            "id": f"{entry['topic']}_child",
            "content": entry["child"],
            "metadata": {
                "topic": entry["topic"],
                "crop": entry["crop"],
                "season": entry["season"],
                "practice_type": entry["practice_type"],
                "topic_id": topic_id,
                "chunk_type": "child",
            },
        })
        practices.append({
            "id": f"{entry['topic']}_parent",
            "content": entry["parent"],
            "metadata": {
                "topic": entry["topic"],
                "crop": entry["crop"],
                "season": entry["season"],
                "practice_type": entry["practice_type"],
                "topic_id": topic_id,
                "chunk_type": "parent",
            },
        })

    return practices


def _get_regional_context_chunks() -> list[dict]:
    """Generate parent/child pairs for regional_context collection."""
    contexts = []

    entries = [
        {
            "topic": "casamance_overview",
            "region": "Casamance",
            "data_type": "geography",
            "child": "Casamance region Senegal climate agriculture overview. Tropical savanna, rainy season June to October, main crops cassava rice maize groundnut.",
            "parent": (
                "Casamance Region — Agricultural Overview\n\n"
                "Location: Southern Senegal, bordered by The Gambia (north) and Guinea-Bissau (south).\n"
                "Climate: Tropical savanna (Aw). Two seasons: wet (June-October, 1000-1500mm rainfall) "
                "and dry (November-May, near zero rainfall).\n"
                "Temperature: 25-30°C year-round. Hottest: March-April.\n\n"
                "Agriculture:\n"
                "- Main food crops: Rice (staple), cassava, maize, millet\n"
                "- Main cash crops: Groundnut, cashew, palm oil\n"
                "- Livestock: Cattle, goats, poultry\n"
                "- Fishing: Important in coastal and river areas\n\n"
                "Casamance is Senegal's most productive agricultural region due to higher rainfall "
                "than the north. However, farmers face: disease pressure (humidity-driven), "
                "limited access to improved seeds, post-harvest losses, and market access challenges.\n\n"
                "Key institutions: ISRA (Senegalese Agricultural Research), ANCAR (extension), "
                "AfricaRice, ICRISAT, various NGOs (Action Against Hunger, CRS, etc.)."
            ),
        },
        {
            "topic": "local_resources",
            "region": "Casamance",
            "data_type": "resources",
            "child": "What materials are locally available in Casamance Senegal for farming. Neem trees, wood ash, compost, local seeds, agricultural supply shops in Ziguinchor.",
            "parent": (
                "Locally Available Agricultural Resources in Casamance\n\n"
                "Natural resources:\n"
                "- Neem trees (Azadirachta indica): Abundant throughout. Seeds for organic pesticide.\n"
                "- Wood ash: From cooking fires. Rich in potassium, useful for soil amendment and pest control.\n"
                "- Compost materials: Crop residues, animal manure, kitchen waste.\n"
                "- Clay/laterite: For pot making, raised bed construction.\n\n"
                "Agricultural inputs (Ziguinchor and Kolda towns):\n"
                "- Copper sulfate, mancozeb, chlorothalonil: Agricultural supply shops\n"
                "- Improved seed varieties: ISRA station, ANCAR offices, NGO seed fairs\n"
                "- Basic tools: Local markets and hardware shops\n"
                "- Plastic sheeting (for solarization): Hardware shops\n\n"
                "Seed sources:\n"
                "- ISRA Djibelor station (Ziguinchor): Certified cassava cuttings, rice seed\n"
                "- ANCAR regional office: Extension advice and seed referrals\n"
                "- NGO seed distribution programs: Seasonal seed fairs\n"
                "- Farmer-to-farmer seed exchange: Common for traditional varieties"
            ),
        },
        {
            "topic": "water_management",
            "region": "Casamance",
            "data_type": "climate",
            "child": "Water management and irrigation in Casamance Senegal. Rainy season water harvesting, dry season irrigation, drought coping strategies for farmers.",
            "parent": (
                "Water Management in Casamance Agriculture\n\n"
                "Rainy season (June-October):\n"
                "- Rainfall 1000-1500mm concentrated in 5 months\n"
                "- Challenge: too much water, not too little. Drainage critical for lowland rice.\n"
                "- Tied ridges on upland fields to capture rainfall and reduce erosion\n"
                "- Mulching to reduce evaporation during dry spells within the rainy season\n\n"
                "Dry season (November-May):\n"
                "- Near-zero rainfall for 7 months\n"
                "- Irrigation sources: Wells, boreholes, river diversions, small reservoirs\n"
                "- Drip irrigation using simple bucket kits reduces water use by 50%\n"
                "- Focus on high-value crops: tomato, onion, chili pepper, leafy vegetables\n\n"
                "Drought coping:\n"
                "- Plant drought-tolerant varieties (cassava is most resilient)\n"
                "- Mulch heavily to conserve soil moisture\n"
                "- Harvest rainwater in small farm ponds (3m x 3m x 1.5m)\n"
                "- Plant early to maximize use of rainy season\n"
                "- Diversify: don't depend on a single rain-fed crop"
            ),
        },
    ]

    for entry in entries:
        topic_id = f"context_{entry['topic']}"
        contexts.append({
            "id": f"{entry['topic']}_child",
            "content": entry["child"],
            "metadata": {
                "region": entry["region"],
                "topic": entry["topic"],
                "data_type": entry["data_type"],
                "topic_id": topic_id,
                "chunk_type": "child",
            },
        })
        contexts.append({
            "id": f"{entry['topic']}_parent",
            "content": entry["parent"],
            "metadata": {
                "region": entry["region"],
                "topic": entry["topic"],
                "data_type": entry["data_type"],
                "topic_id": topic_id,
                "chunk_type": "parent",
            },
        })

    return contexts


def get_all_chunks() -> dict[str, list[dict]]:
    """Return all chunks organized by collection name.

    Returns:
        dict mapping collection name to list of chunk dicts,
        each with 'id', 'content', and 'metadata' keys.
    """
    disease_chunks = _get_disease_chunks()

    return {
        "disease_knowledge": disease_chunks["disease_knowledge"],
        "treatment_guides": disease_chunks["treatment_guides"],
        "farming_practices": _get_farming_practice_chunks(),
        "regional_context": _get_regional_context_chunks(),
    }
