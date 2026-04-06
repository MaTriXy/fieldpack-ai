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
                "disease_name": disease["name"],
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
                "disease_name": disease["name"],
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
                    "disease_name": disease["name"],
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
                    "disease_name": disease["name"],
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
                    "disease_name": disease["name"],
                    "crop": crop,
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
                    "disease_name": disease["name"],
                    "crop": crop,
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
            "growth_stage": "planning",
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
            "growth_stage": "planning",
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
            "growth_stage": "planning",
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
            "practice_type": "pest",
            "growth_stage": "vegetative",
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
        # ── CASSAVA ──────────────────────────────────────────────────────────
        {
            "topic": "cassava_nursery_management",
            "crop": "cassava",
            "season": "wet",
            "practice_type": "planting",
            "growth_stage": "nursery",
            "child": "How to select and prepare cassava stem cuttings for planting. Good stems, cutting length, fungicide dip, storage before planting in Casamance.",
            "parent": (
                "Cassava Nursery and Cutting Preparation — Casamance\n\n"
                "Stem selection: Choose cuttings from healthy, disease-free plants that are 8-18 months old. "
                "Avoid stems showing mosaic leaf patterns (CMD) or brown internal discoloration (CBSD). "
                "Preferred varieties: TME 419, IITA-TMS-IBA30572, available from ISRA Djibelor station in Ziguinchor.\n\n"
                "Cutting preparation: Cut stems into 20-25 cm sections using a clean, sharp machete. "
                "Each cutting should have at least 5-6 nodes. Make clean cuts at 45-degree angles "
                "to improve water absorption and rooting surface area.\n\n"
                "Fungicide dip: Mix 5g mancozeb in 10L water. Dip cut ends for 10 minutes to prevent "
                "fungal rot during establishment. Mancozeb available at agricultural shops in Ziguinchor market.\n\n"
                "Storage before planting: Bundle 50 cuttings upright in shade. Keep cool and dry. "
                "Plant within 3 days of cutting — do not store longer, as viability drops sharply. "
                "Never store cuttings lying flat on bare soil (promotes fungal attack and ant damage).\n\n"
                "Quantity: 10,000 cuttings needed per hectare at 1m x 1m spacing. "
                "One mature cassava plant yields 30-50 cuttings for the next season."
            ),
        },
        {
            "topic": "cassava_land_preparation",
            "crop": "cassava",
            "season": "wet",
            "practice_type": "soil",
            "growth_stage": "planning",
            "child": "How to prepare land for cassava in Casamance. Clearing bush, tilling, making ridges or mounds for cassava planting on Casamance soils.",
            "parent": (
                "Land Preparation for Cassava — Casamance Soils\n\n"
                "Casamance soils: Predominantly sandy-loam (sols ferralitiques) with low organic matter. "
                "Cassava tolerates poor soils but yields better with good drainage and light tillage.\n\n"
                "Clearing: Remove previous crop residues and weeds. Slash-and-burn is traditional but "
                "degrading. Incorporate residues as mulch or compost where possible.\n\n"
                "Tillage: Plough or hoe to 20-25 cm depth. This breaks compaction, improves aeration, "
                "and reduces weeds. In wet years, deeper tillage increases drainage.\n\n"
                "Ridge formation: On flat land, form ridges 30 cm high, spaced 1 m apart. "
                "Ridges improve drainage (cassava is susceptible to root rot in waterlogged soil) "
                "and make harvest easier. On slopes, form ridges along contour lines to prevent erosion.\n\n"
                "Mounds: In very heavy-clay or low-lying areas, create mounds 40 cm high, 60 cm diameter, "
                "spaced 1 m x 1 m. Mounds are especially useful in flood-prone lowland areas of Bignona.\n\n"
                "Timing: Complete land preparation before rains establish (May) so you can plant "
                "at first reliable rains in mid-June. Planting in well-prepared, moist soil "
                "gives 20-30% better establishment than late planting."
            ),
        },
        {
            "topic": "cassava_planting_technique",
            "crop": "cassava",
            "season": "wet",
            "practice_type": "planting",
            "growth_stage": "seedling",
            "child": "How to plant cassava cuttings correctly. Angle, depth, spacing 1m x 1m, which way up, planting in ridges for Casamance fields.",
            "parent": (
                "Cassava Planting Technique — Casamance\n\n"
                "Spacing: 1 m x 1 m (10,000 plants/hectare). Wider spacing (1.2 m x 1.2 m) "
                "for drought-prone areas gives each plant more soil moisture. "
                "Narrower spacing increases yield per hectare but requires more cuttings and water.\n\n"
                "Orientation: Plant cuttings vertically or at a 45-degree angle. "
                "Vertical planting gives better shoot emergence. Angled planting gives "
                "slightly better root development on ridges.\n\n"
                "Depth: Insert 2/3 of the cutting into the soil (about 15 cm), leaving 5-8 cm above ground. "
                "Too shallow: dries out, poor rooting. Too deep: stem rot risk.\n\n"
                "Bud direction: Plant with buds (small bumps on stem nodes) facing upward. "
                "Wrong orientation reduces emergence rate by 40%.\n\n"
                "Soil contact: Press firm soil around the cutting base. Air pockets cause root failure. "
                "Water the base lightly if the soil is dry at planting.\n\n"
                "Planting time: Morning or late afternoon to avoid heat stress. "
                "If planting into dry soil, water each hole before inserting the cutting. "
                "Best results: plant the same day as cutting preparation."
            ),
        },
        {
            "topic": "cassava_weeding_management",
            "crop": "cassava",
            "season": "wet",
            "practice_type": "soil",
            "growth_stage": "vegetative",
            "child": "When and how to weed cassava in Casamance. First weeding at 4 weeks, how often to weed, tools for cassava weeding.",
            "parent": (
                "Cassava Weeding Management — Casamance\n\n"
                "Critical weeding window: The first 3 months after planting are the most critical. "
                "Weeds competing during this period can reduce yields by 40-60%. "
                "Once cassava canopy closes (3-4 months), it suppresses weeds naturally.\n\n"
                "First weeding: At 4 weeks after planting. Remove all weeds by hand hoe around each plant "
                "within a 50 cm radius. Use a short-handled daba (hoe) for precision without damaging shallow roots.\n\n"
                "Second weeding: At 8 weeks. Wider coverage, include inter-row weeding. "
                "This is often the most labor-intensive operation — organize family labor or weeding groups.\n\n"
                "Third weeding: At 12 weeks if weed pressure is high (especially during heavy rains "
                "which stimulate weed germination). By this time, cassava canopy begins closing.\n\n"
                "Tools: Daba (short hoe) for precision work. Longer-handled hilaire hoe for inter-rows. "
                "Both available at Ziguinchor market for 2,000-4,000 FCFA.\n\n"
                "Mulching to reduce weeding: After first weeding, apply 10 cm grass mulch. "
                "Reduces subsequent weed growth by 60% and conserves moisture. "
                "Use dry grass, crop residues, or palm fronds."
            ),
        },
        {
            "topic": "cassava_fertilization_guide",
            "crop": "cassava",
            "season": "wet",
            "practice_type": "fertilization",
            "growth_stage": "vegetative",
            "child": "How to fertilize cassava in Casamance. NPK basal dose, when to top-dress, compost rates, fertilizer amounts for cassava.",
            "parent": (
                "Cassava Fertilization Guide — Casamance\n\n"
                "Cassava is relatively low-input but responds well to balanced nutrition. "
                "Sandy Casamance soils are often deficient in potassium and nitrogen.\n\n"
                "Basal application (at planting):\n"
                "- Compost: 2-3 tonnes/ha incorporated into planting hole or ridge. "
                "Compost available from farm compost pits (see soil_management entry).\n"
                "- NPK 15-15-15: 150 kg/ha applied in a ring 15 cm from stem base, "
                "covered with soil to prevent volatilization.\n\n"
                "Top-dress at 2 months:\n"
                "- Urea (46% N): 50 kg/ha applied 30 cm from stem base. "
                "Apply when soil is moist (after rain) so nitrogen is absorbed, not lost.\n"
                "- Potassium (muriate of potash): 50 kg/ha at 2-3 months — critical for root bulking.\n\n"
                "Organic option (low cost):\n"
                "- Chicken manure: 3 tonnes/ha at planting, incorporated into soil.\n"
                "- Wood ash: 500 kg/ha broadcast and incorporated — provides potassium and corrects soil acidity.\n\n"
                "Where to buy: NPK, urea, potash available at Societe Generale des Engrais "
                "distributors in Ziguinchor and at ANCAR-partnered agro-dealers. "
                "Prices: NPK ~25,000 FCFA/50kg bag (2025 estimate)."
            ),
        },
        {
            "topic": "cassava_pest_monitoring",
            "crop": "cassava",
            "season": "wet",
            "practice_type": "pest",
            "growth_stage": "vegetative",
            "child": "How to check cassava for pests. Whitefly scouting, mealybug signs, green mite damage, when to scout in Casamance cassava fields.",
            "parent": (
                "Cassava Pest Monitoring — Casamance\n\n"
                "Scout every 2 weeks from 1 month after planting. Check 20 plants per hectare "
                "randomly across the field. Check top 3 leaves and stem underside.\n\n"
                "Whitefly (Bemisia tabaci): Major vector of Cassava Brown Streak Virus (CBSV) and CMD. "
                "Look for tiny white insects on leaf undersides — shake leaf and watch for cloud. "
                "Silvery or yellowed leaves indicate infestation. "
                "Action threshold: more than 10 adults per leaf. "
                "Control: Neem oil spray (500g seeds/10L water), yellow sticky traps.\n\n"
                "Cassava Mealybug (Phenacoccus manihoti): White cottony masses at stem growing points "
                "and leaf axils. Causes bunchy top symptoms. "
                "Action: Physically remove with soapy water cloth wipe; "
                "neem spray on affected areas. Parasitic wasp (Apoanagyrus lopezi) is a natural enemy — "
                "do not use broad-spectrum insecticides.\n\n"
                "Green Mite (Mononychellus tanajoa): Bronze/yellow stippling on upper leaf surface. "
                "Worse in dry conditions. "
                "Control: Increase plant spacing for airflow; neem oil spray; encourage predatory mites "
                "by avoiding synthetic acaricides.\n\n"
                "Record observations: Write down date, plant affected, pest type, and severity "
                "(1=light, 2=moderate, 3=severe) in a field notebook."
            ),
        },
        {
            "topic": "cassava_harvest_technique",
            "crop": "cassava",
            "season": "all",
            "practice_type": "harvest",
            "growth_stage": "harvest",
            "child": "When and how to harvest cassava. Maturity signs at 8-18 months, how to lift roots without breaking, harvesting cassava in Casamance.",
            "parent": (
                "Cassava Harvest Technique — Casamance\n\n"
                "Maturity window: Most varieties in Casamance mature at 8-12 months (sweet cassava) "
                "or 12-18 months (bitter/high-HCN varieties). "
                "TME 419 is typically harvestable at 9-12 months.\n\n"
                "Maturity signs: Stems begin to lighten in color; lower leaves yellow and drop; "
                "roots reach 5-8 cm diameter. Test-harvest 2-3 plants to confirm root size before field harvest.\n\n"
                "Harvest technique:\n"
                "1. Cut stems at 30-40 cm height first (preserve as cuttings for next season).\n"
                "2. Loosen soil 20-30 cm from stem with a hoe or digging fork — do not pierce roots.\n"
                "3. Grip stem stump and pull roots upward with a rotating motion.\n"
                "4. Inspect: discard roots with internal brown discoloration (CBSD sign).\n\n"
                "Timing: Harvest in the morning to reduce heat stress on exposed roots. "
                "Avoid harvesting in heavy rain (slippery, root quality drops).\n\n"
                "Yield expectation: 15-25 tonnes/ha for improved varieties; 8-12 tonnes/ha for local varieties.\n\n"
                "Urgency: Fresh cassava roots deteriorate within 24-72 hours of harvest due to "
                "Post-Harvest Physiological Deterioration (PPD). Process immediately."
            ),
        },
        {
            "topic": "cassava_post_harvest_handling",
            "crop": "cassava",
            "season": "all",
            "practice_type": "post_harvest",
            "growth_stage": "post_harvest",
            "child": "What to do with cassava after harvest. Making gari and attieke, storing fresh cassava, drying cassava chips in Casamance.",
            "parent": (
                "Cassava Post-Harvest Handling — Casamance\n\n"
                "Critical constraint: Cassava roots deteriorate within 24-72 hours of harvest (PPD — "
                "Post-Harvest Physiological Deterioration). They must be processed or sold immediately.\n\n"
                "Gari production (West African fermented product):\n"
                "1. Peel and wash roots within 2 hours of harvest.\n"
                "2. Grate roots (manual or mechanical grater at Ziguinchor processing center).\n"
                "3. Press in sacks for 2-3 days to ferment and remove water (bags weighted with stones).\n"
                "4. Fry (garification) in shallow pan until dry and cream-colored.\n"
                "5. Cool and bag. Shelf life: 6-12 months in sealed bags.\n\n"
                "Attieke production (fermented couscous, Casamance speciality):\n"
                "Similar to gari but pressed into granules and steamed rather than fried. "
                "Local women's cooperatives in Ziguinchor and Bignona produce attieke for local markets.\n\n"
                "Fresh storage (max 48 hours): Keep roots in cool shade. "
                "Do NOT wash before storage. Cover with wet cloth to slow PPD by 12-24 hours.\n\n"
                "Dried cassava chips (cossettes): Peel, slice 5mm thick, sun-dry 3-5 days on raised racks. "
                "Dried chips store 6-12 months and can be ground to cassava flour (farine de manioc). "
                "Raised racks prevent contamination and reduce drying time vs ground drying."
            ),
        },
        # ── RICE ─────────────────────────────────────────────────────────────
        {
            "topic": "rice_nursery_management",
            "crop": "rice",
            "season": "wet",
            "practice_type": "planting",
            "growth_stage": "nursery",
            "child": "How to prepare a rice nursery in Casamance. Nursery bed preparation, seed rate, watering schedule, when rice seedlings are ready to transplant.",
            "parent": (
                "Rice Nursery Management — Casamance\n\n"
                "Nursery vs direct seeding: Transplanted rice uses 30-40% less seed, "
                "allows early land preparation, and produces more uniform stands. "
                "Recommended for lowland and irrigated rice in Casamance.\n\n"
                "Nursery bed preparation: Choose a flat, near-water location. "
                "Till to 15 cm depth. Form raised beds 1 m wide, any length. "
                "Apply 1-2 kg compost per square meter and incorporate. "
                "Flood the bed 3 days before sowing to soften soil and germinate weed seeds "
                "(then remove weed seedlings before sowing rice).\n\n"
                "Pre-germination: Soak certified rice seed for 48 hours in clean water. "
                "Drain and keep in wet sacks for 24 hours until small white radicles appear. "
                "Recommended varieties: ITA 123, Sahel 108, or local Casamance lowland varieties "
                "from ISRA Djibelor research station.\n\n"
                "Sowing: Broadcast pre-germinated seed at 400-500 g per square meter of nursery bed. "
                "1 m2 of nursery feeds 10 m2 of field, so plan nursery area accordingly. "
                "For 1 ha, prepare 100-120 m2 of nursery beds.\n\n"
                "Nursery care: Keep flooded to 2-3 cm for first 7 days. "
                "Thin to reduce overcrowding at 10 days. Apply 5 g urea per m2 at 10 days.\n\n"
                "Transplanting age: 21-25 days after sowing. Older seedlings (>30 days) "
                "transplant poorly and tiller less."
            ),
        },
        {
            "topic": "rice_transplanting",
            "crop": "rice",
            "season": "wet",
            "practice_type": "planting",
            "growth_stage": "seedling",
            "child": "How to transplant rice seedlings in Casamance. Seedling age 21-25 days, spacing 20x20cm, depth, preparing puddled paddy field for rice transplanting.",
            "parent": (
                "Rice Transplanting — Casamance Lowlands\n\n"
                "Field preparation (puddling): 3-5 days before transplanting, flood the paddy field "
                "and puddle (till wet soil) with hoes or a mechanical tiller. "
                "Puddling destroys weeds, seals the base to retain water, and creates soft soil for roots. "
                "Keep 5-8 cm water depth in the field.\n\n"
                "Seedling removal: Pull seedlings from nursery with roots intact. "
                "Do not expose roots to sun — wrap in wet cloth for transport. "
                "Remove up to 1/3 of leaf tips to reduce transplant shock.\n\n"
                "Transplanting technique:\n"
                "- Spacing: 20 cm x 20 cm (25 hills/m2 = 250,000 hills/ha)\n"
                "- Insert 2-3 seedlings per hill at 3-5 cm depth\n"
                "- Keep rows straight using a marker rope for even spacing\n"
                "- Transplant in the morning or evening, never during midday heat\n\n"
                "Water management after transplanting: Maintain 3-5 cm water for first 7 days "
                "to reduce transplant shock. Then raise to 10 cm.\n\n"
                "Gap-filling: At 7-10 days after transplanting, identify missing hills "
                "and fill with nursery reserve seedlings.\n\n"
                "Labor: Transplanting 1 ha requires 15-20 person-days. "
                "Organize community labor exchange (navétane groups)."
            ),
        },
        {
            "topic": "rice_water_management",
            "crop": "rice",
            "season": "wet",
            "practice_type": "irrigation",
            "growth_stage": "vegetative",
            "child": "How to manage water in rice paddy fields in Casamance. Flooding depth, when to drain, alternate wetting and drying AWD technique for water saving.",
            "parent": (
                "Rice Water Management — Casamance\n\n"
                "Lowland rice in Casamance depends on both rainfall and controlled flooding. "
                "Proper water management is the single biggest yield determinant.\n\n"
                "Flooding depth by growth stage:\n"
                "- Transplanting to active tillering (0-30 days): 3-5 cm — shallow water promotes tillering\n"
                "- Maximum tillering to panicle initiation (30-60 days): 5-10 cm — deeper discourages weeds\n"
                "- Booting to heading (60-80 days): 10-15 cm — protect from cold\n"
                "- Grain filling (80-100 days): 5-10 cm\n"
                "- 2 weeks before harvest: drain field completely\n\n"
                "Alternate Wetting and Drying (AWD): Saves 25-30% water without yield loss. "
                "Technique: after tillering, let field dry until soil surface cracks (not more than "
                "3-4 days dry). Then re-flood to 5 cm. Repeat cycle. "
                "Monitor using a bamboo tube (tube piezometre) inserted in soil.\n\n"
                "Drainage: Casamance lowlands can flood too deep during heavy rain. "
                "Maintain a drainage outlet. Standing water >20 cm for more than 3 days "
                "causes oxygen deficiency and yield loss.\n\n"
                "Salt intrusion: In coastal lowlands near estuaries (Bignona, Oussouye), "
                "check water salinity. Rice tolerates up to 3 dS/m — above this, use salt-tolerant "
                "varieties from ISRA (Sahel 108, DJ 11-509)."
            ),
        },
        {
            "topic": "rice_fertilization_guide",
            "crop": "rice",
            "season": "wet",
            "practice_type": "fertilization",
            "growth_stage": "vegetative",
            "child": "How to fertilize rice in Casamance. Basal NPK dose, urea top-dressing at tillering and panicle initiation, fertilizer timing for lowland rice.",
            "parent": (
                "Rice Fertilization Guide — Casamance\n\n"
                "Rice is a high-nutrient-demand crop. Without fertilization, "
                "Casamance lowland rice yields 1.5-2 t/ha. With proper fertilization: 3-5 t/ha.\n\n"
                "Basal application (at transplanting or 1 week after):\n"
                "- NPK 15-15-15: 100 kg/ha broadcast in standing water\n"
                "- Compost: 2 t/ha incorporated during puddling\n\n"
                "First top-dress (at maximum tillering, ~30 days after transplanting):\n"
                "- Urea (46% N): 50 kg/ha broadcast in flooded field in the morning. "
                "Apply when no rain expected for 24 hours — rain washes nitrogen before uptake.\n\n"
                "Second top-dress (at panicle initiation, ~60 days after transplanting):\n"
                "- Urea: 50 kg/ha — critical for grain number and weight\n"
                "- Potassium sulfate: 30 kg/ha — improves grain filling and disease resistance\n\n"
                "Deficiency symptoms:\n"
                "- Nitrogen: uniform yellowing of older leaves — apply urea immediately\n"
                "- Phosphorus: dark green leaves, reddish-purple coloring, stunted tillering\n"
                "- Potassium: brown leaf margins (scorch), lodging\n\n"
                "Organic option: Azolla (floating fern) grown in the paddy fixes nitrogen naturally. "
                "Inoculate paddies with azolla at transplanting — available from ISRA Djibelor.\n\n"
                "Input source: NPK and urea from agro-dealers in Ziguinchor, Bignona, Kolda markets."
            ),
        },
        {
            "topic": "rice_weeding_management",
            "crop": "rice",
            "season": "wet",
            "practice_type": "soil",
            "growth_stage": "vegetative",
            "child": "How to weed rice paddies in Casamance. Hand weeding at 3 and 6 weeks after transplanting, cono weeder for row-planted rice.",
            "parent": (
                "Rice Weeding Management — Casamance\n\n"
                "Weeds are the major cause of yield loss in Casamance lowland rice, "
                "especially Cynodon dactylon (devil's grass), Echinochloa (barnyardgrass), "
                "and floating aquatic weeds in poorly drained paddies.\n\n"
                "Critical weed-free period: First 30-40 days after transplanting. "
                "Weeds competing during this period cause 40-60% yield loss.\n\n"
                "First weeding: 3 weeks after transplanting. "
                "Pull weeds by hand between hills. Work backwards to avoid disturbing roots. "
                "Push uprooted weeds into mud — they decompose as green manure.\n\n"
                "Second weeding: 6 weeks after transplanting. "
                "At this point the canopy is closing and weed competition reduces naturally.\n\n"
                "Cono weeder: For row-planted rice (20 cm x 20 cm rows), "
                "a cono weeder (rotary hand weeder) covers 1 ha in 3-4 person-days vs "
                "12-15 days for hand weeding. Local fabricators can make cono weeders "
                "in Ziguinchor metal workshops for 15,000-25,000 FCFA.\n\n"
                "Chemical option (if available): Pretilachlor herbicide at 0.75 L/ha applied "
                "3-5 days after transplanting. Use with care — follow label, wear gloves, "
                "do not let herbicide reach non-target water areas. Available at Ziguinchor agro-dealers."
            ),
        },
        {
            "topic": "rice_harvest_technique",
            "crop": "rice",
            "season": "wet",
            "practice_type": "harvest",
            "growth_stage": "harvest",
            "child": "When and how to harvest rice in Casamance. Signs of maturity 80% golden grains, cutting and threshing, drying to 14% moisture target.",
            "parent": (
                "Rice Harvest Technique — Casamance\n\n"
                "Maturity indicators: Harvest when 80-85% of grains are golden/straw-colored. "
                "Check by pressing a grain — firm, not milky. Most lowland Casamance varieties "
                "(ITA 123, Sahel 108) mature 95-115 days after transplanting.\n\n"
                "Pre-harvest drainage: Drain the paddy field 2 weeks before harvest. "
                "Dry soil makes cutting easier and reduces grain shattering.\n\n"
                "Harvesting:\n"
                "- Sickle harvest: Cut stems at 10-15 cm above ground. Work in rows.\n"
                "- Bundle into sheaves of 30-40 stems, tie with rice straw.\n"
                "- Stack bundles upright in the field for 2-3 hours to wilt before threshing.\n\n"
                "Threshing: Thresh within 24 hours of cutting to minimize field losses and fungal attack. "
                "Beat sheaves against a wooden platform or drum thresher. "
                "Drum threshers available for hire in Ziguinchor — cover 1 ha in half a day.\n\n"
                "Drying: Spread grain on tarpaulins or raised platforms in sun. "
                "Target: 14% moisture content for safe storage. Test: bite a grain — it should be hard, not soft. "
                "Mechanical moisture meters available through ANCAR field offices.\n\n"
                "Yield: 3-5 t/ha (improved variety, fertilized) vs 1.5-2 t/ha (local variety, no inputs)."
            ),
        },
        {
            "topic": "rice_post_harvest_handling",
            "crop": "rice",
            "season": "wet",
            "practice_type": "post_harvest",
            "growth_stage": "post_harvest",
            "child": "How to store rice after harvest in Casamance. Winnowing, bagging, hermetic triple bags to prevent weevil damage, safe rice storage.",
            "parent": (
                "Rice Post-Harvest Handling — Casamance\n\n"
                "Post-harvest losses in Casamance can reach 15-25% without proper handling. "
                "Main threats: moisture re-absorption, weevils (Sitophilus oryzae), "
                "rats, and mold.\n\n"
                "Winnowing: After threshing, winnow to remove chaff and light debris. "
                "Use traditional calabash (calebasse) or bamboo trays in a breeze, "
                "or improvise a raised platform to drop grain through wind.\n\n"
                "Moisture check: Do not store rice above 14% moisture. "
                "Test: put a handful in a closed plastic bag in sun for 10 minutes — "
                "condensation means too moist. Dry further.\n\n"
                "Storage bags:\n"
                "- Standard woven polypropylene bags (50 kg): Adequate if kept dry and cool. "
                "Susceptible to weevils after 2-3 months.\n"
                "- Hermetic triple bags (Purdue Improved Crop Storage — PICS bags): "
                "Seal airtight, suffocate insects. Store 6-12 months without chemical treatment. "
                "Available through NGO distribution programs and ANCAR offices (price ~2,000 FCFA each).\n\n"
                "Storage conditions: Elevate bags on wooden pallets, never on bare earth. "
                "Keep away from walls (rodents). Inspect monthly — "
                "if weevils appear, seal bag immediately and consult ANCAR.\n\n"
                "Traditional methods: Clay grain stores (greniers en banco) with tight-fitting lids "
                "and ash layers between bags — effective and free."
            ),
        },
        # ── TOMATO ───────────────────────────────────────────────────────────
        {
            "topic": "tomato_nursery_management",
            "crop": "tomato",
            "season": "dry",
            "practice_type": "planting",
            "growth_stage": "nursery",
            "child": "How to prepare a tomato nursery in Casamance. Seed trays, shade structure, watering seedlings, when to transplant and harden off tomato plants.",
            "parent": (
                "Tomato Nursery Management — Casamance\n\n"
                "Tomato is grown as a dry-season irrigated crop in Casamance (October-March). "
                "Nursery preparation is done in October for November transplanting.\n\n"
                "Seed tray preparation: Use 72-cell or 128-cell plastic seed trays. "
                "Fill with nursery mix: 2 parts fine topsoil + 1 part compost + 1 part sand. "
                "Sterilize by solarizing under clear plastic for 7-10 days before use.\n\n"
                "Sowing: Sow 2 seeds per cell at 1 cm depth. "
                "Recommended varieties for Casamance: Mongal F1, Padma F1 (heat-tolerant hybrids), "
                "or local Roma varieties. Seed from ISRA Djibelor or Ziguinchor agro-dealers.\n\n"
                "Shade structure: Build a bamboo frame covered with shade cloth (50% shade) "
                "or palm frond thatch. Seedlings are vulnerable to direct sun and heavy rain. "
                "Structure height: 1.5 m minimum for air circulation.\n\n"
                "Watering: Water gently twice daily using a watering can with rose head. "
                "Never flood — tomato seedlings are highly susceptible to damping-off "
                "(Pythium fungus) in overwatered conditions.\n\n"
                "Thinning: At 10 days, thin to 1 seedling per cell (keep the stronger plant).\n\n"
                "Hardening off: 5 days before transplanting, reduce shade and watering to "
                "acclimatize to field conditions. Move trays to full sun for 2 hours per day, increasing each day.\n\n"
                "Transplanting age: 21-28 days after sowing, when seedlings are 10-15 cm tall "
                "with 3-4 true leaves."
            ),
        },
        {
            "topic": "tomato_transplanting",
            "crop": "tomato",
            "season": "dry",
            "practice_type": "planting",
            "growth_stage": "seedling",
            "child": "How to transplant tomato seedlings in Casamance. Evening transplanting, watering, mulch basin, spacing 60x40cm for dry season tomatoes.",
            "parent": (
                "Tomato Transplanting — Casamance Dry Season\n\n"
                "Timing: Transplant in the evening (after 4 PM) or on cloudy days to minimize "
                "transplant shock. Morning transplanting in Casamance heat causes 20-30% wilting loss.\n\n"
                "Spacing: 60 cm between rows, 40 cm between plants. "
                "This gives 41,000 plants/ha — appropriate for determinate varieties. "
                "For indeterminate (staked) varieties: 60 cm x 60 cm.\n\n"
                "Hole preparation: Dig holes 20 cm deep, 25 cm diameter. "
                "Mix 200 g compost into each hole before planting. "
                "For each hole, add a small fistful of NPK 15-15-15 (about 10 g), "
                "mixed into the bottom soil — do not let fertilizer directly touch roots.\n\n"
                "Planting: Remove seedling from tray carefully preserving root ball. "
                "Plant to the same depth as in the tray. Firm soil around roots.\n\n"
                "Watering: Water each plant immediately after transplanting (0.5L per plant). "
                "Water again the next morning.\n\n"
                "Mulch basin: Apply 5-8 cm of dry grass or crop residue around each plant "
                "in a 40 cm radius basin. Mulch reduces irrigation frequency by 40%, "
                "suppresses weeds, and keeps roots cool.\n\n"
                "Gap-filling: At 7 days after transplanting, replace dead or weak plants "
                "with nursery reserve seedlings."
            ),
        },
        {
            "topic": "tomato_irrigation_schedule",
            "crop": "tomato",
            "season": "dry",
            "practice_type": "irrigation",
            "growth_stage": "vegetative",
            "child": "How often to water tomatoes in Casamance dry season. Drip vs furrow irrigation, irrigation frequency, critical stages for tomato watering.",
            "parent": (
                "Tomato Irrigation Schedule — Casamance Dry Season\n\n"
                "Tomatoes require consistent moisture — irregular watering causes blossom-end rot "
                "and fruit cracking. In the Casamance dry season (November-March), "
                "all water must come from irrigation.\n\n"
                "Drip irrigation: Most efficient for tomatoes. "
                "1 drip emitter per plant at 4 L/hour. "
                "Run 1-2 hours every 2 days. Reduces water use by 40-50% vs furrow. "
                "Simple gravity drip kits (bucket drip) from NGO programs or Ziguinchor hardware shops.\n\n"
                "Furrow irrigation: More common in Casamance. Open furrows between rows. "
                "Flood furrows every 3-4 days in cool weather (November-January), "
                "every 2-3 days in warm weather (February-March). "
                "Volume: 30-40 L per meter of furrow.\n\n"
                "Critical water stages:\n"
                "- Transplanting to establishment (0-14 days): Daily watering, small volumes\n"
                "- Flowering: Never let soil dry completely — causes blossom drop\n"
                "- Fruit set and development: Most critical period — consistent moisture\n"
                "- Ripening: Reduce water 2 weeks before harvest to improve flavor and storage\n\n"
                "Deficit signs: Leaf curl in morning (temporary, OK); "
                "leaf curl at 9 AM (deficit — water today); "
                "purplish leaf tinge combined with curl (severe, yield impacted).\n\n"
                "Water quality: If using river or well water with high salinity near estuaries, "
                "test before use. Tomatoes tolerate up to 2.5 dS/m."
            ),
        },
        {
            "topic": "tomato_fertilization_guide",
            "crop": "tomato",
            "season": "dry",
            "practice_type": "fertilization",
            "growth_stage": "flowering",
            "child": "How to fertilize tomatoes at flowering in Casamance. Side-dressing fertilizer at flowering, potassium for fruit quality, tomato fertilization schedule.",
            "parent": (
                "Tomato Fertilization Guide — Casamance\n\n"
                "Tomatoes are heavy feeders requiring nitrogen for growth, "
                "phosphorus for root development, and potassium for fruit quality.\n\n"
                "Pre-plant: Incorporate 3-5 t/ha compost into beds before transplanting.\n\n"
                "Basal at transplanting: 200 kg/ha NPK 15-15-15 in planting furrow. "
                "Do not apply directly to roots — mix into the row, then transplant.\n\n"
                "First top-dress at 3 weeks: 50 kg/ha urea dissolved in irrigation water "
                "(fertigate) or broadcast 10 cm from plant stem.\n\n"
                "Flowering top-dress (critical): At first flower clusters opening, apply:\n"
                "- 50 kg/ha potassium sulfate (K2SO4): improves fruit size, shelf life, taste\n"
                "- 30 kg/ha calcium nitrate: prevents blossom-end rot (calcium deficiency disease)\n"
                "Side-dress 15 cm from stem base, water in immediately.\n\n"
                "Fruit set top-dress: At heavy fruit set (small green fruits visible), apply:\n"
                "- 30 kg/ha urea + 30 kg/ha potassium sulfate\n\n"
                "Organic option: Fermented compost tea (1 kg mature compost soaked 48h in 10L water, "
                "strained, applied at 1L per plant per week) provides balanced slow-release nutrition.\n\n"
                "Deficiency signs:\n"
                "- Nitrogen: pale yellow lower leaves, slow growth\n"
                "- Potassium: brown leaf edges, soft fruits\n"
                "- Calcium: brown rot at blossom end of fruit (BER)\n\n"
                "Inputs available: NPK, urea, K2SO4 at Ziguinchor agro-dealers."
            ),
        },
        {
            "topic": "tomato_staking_and_pruning",
            "crop": "tomato",
            "season": "dry",
            "practice_type": "planting",
            "growth_stage": "vegetative",
            "child": "How to stake and prune tomatoes in Casamance. Bamboo stakes, single-stem training, removing suckers for better tomato yield.",
            "parent": (
                "Tomato Staking and Pruning — Casamance\n\n"
                "Staking is essential for indeterminate (tall-growing) tomato varieties. "
                "Unstaked plants drag on soil, leading to fruit rot, more pest problems, "
                "and difficult harvesting.\n\n"
                "Staking:\n"
                "- Use bamboo poles 1.5-2 m long. Bamboo grows abundantly along Casamance riverbanks "
                "and is free or very cheap from local markets.\n"
                "- Insert stake 20-30 cm deep, 10 cm from plant stem.\n"
                "- Tie plant to stake with soft cloth strips or raffia (not wire — it cuts stem). "
                "Tie loosely to allow stem thickening.\n"
                "- Re-tie every 2 weeks as plant grows.\n\n"
                "Single-stem (cordon) training:\n"
                "- Remove all suckers (side shoots growing from leaf axils) when they are 5-10 cm long. "
                "This keeps one main stem, improving air circulation and fruit size.\n"
                "- For commercial production: limit to 4-6 fruit clusters per stem, "
                "then pinch the growing tip to concentrate energy into existing fruit.\n\n"
                "Two-stem training: Leave one sucker (the one just below first flower cluster). "
                "Train both stems up separate stakes. Good compromise between yield and management.\n\n"
                "Leaf removal: Remove old yellowing leaves below the lowest fruit cluster. "
                "This improves airflow and reduces fungal disease pressure (Alternaria, early blight).\n\n"
                "Labor note: Staking and pruning 1 ha requires 2-3 person-days per week — "
                "significant labor investment but returns 30-50% yield improvement."
            ),
        },
        {
            "topic": "tomato_pest_monitoring",
            "crop": "tomato",
            "season": "dry",
            "practice_type": "pest",
            "growth_stage": "vegetative",
            "child": "How to check tomatoes for pests in Casamance. Fruit borer scouting, whitefly damage, early blight signs on tomato plants.",
            "parent": (
                "Tomato Pest and Disease Monitoring — Casamance\n\n"
                "Scout twice per week from transplanting onward. Check 20 plants per 0.5 ha. "
                "Record observations by date.\n\n"
                "Tomato Fruit Borer (Helicoverpa armigera): Most damaging pest in Casamance. "
                "Look for: small holes at fruit calyx (blossom end); internal frass (brown droppings). "
                "Check 5 fruits per scouted plant. "
                "Action threshold: 1 damaged fruit in 10. "
                "Control: Spinosad 0.75 mL/L water — organic-approved, effective. "
                "Apply at dusk when moths are active. Rotate with neem oil to prevent resistance.\n\n"
                "Whitefly (Bemisia tabaci): Tomato yellow leaf curl virus vector. "
                "Look for: sticky honeydew on leaves; black sooty mold; tiny white insects under leaves. "
                "Control: Yellow sticky traps (1 per 10 m2); neem oil spray; "
                "reflective aluminum mulch repels whiteflies.\n\n"
                "Early Blight (Alternaria solani): "
                "Brown circular spots with yellow halo on lower leaves, rings visible inside spot. "
                "Spreads up plant in humid conditions. "
                "Control: Remove affected leaves; copper oxychloride spray (3 g/L) every 7-10 days; "
                "improve air circulation by pruning.\n\n"
                "Bacterial Wilt (Ralstonia solanacearum): "
                "Sudden wilting of entire plant. Cut stem in water — milky bacterial ooze confirms. "
                "No cure: remove and burn affected plants immediately. Do not replant tomato or "
                "solanaceous crops in same spot for 3 years. Solarize soil."
            ),
        },
        {
            "topic": "tomato_harvest_technique",
            "crop": "tomato",
            "season": "dry",
            "practice_type": "harvest",
            "growth_stage": "harvest",
            "child": "When and how to harvest tomatoes in Casamance. Breaker stage for market sales, handling to avoid bruising, harvesting tomato correctly.",
            "parent": (
                "Tomato Harvest Technique — Casamance\n\n"
                "Market timing is critical for tomatoes. Unlike cassava, tomatoes must be "
                "harvested at exactly the right stage for successful sale.\n\n"
                "Maturity stages:\n"
                "- Mature green: Full size, firm, fully green — can be harvested for long-distance transport\n"
                "- Breaker: First blush of color change (10-30% red/yellow). "
                "Best stage for market — ripens in transit.\n"
                "- Pink: 30-60% red. For local/nearby markets. 2-3 days shelf life.\n"
                "- Table ripe: Fully red, soft. For home use or immediate sale. 1 day shelf life.\n\n"
                "Harvest technique:\n"
                "1. Harvest in the morning before heat builds.\n"
                "2. Twist and lift — do not pull downward (breaks stem, creates entry point for disease).\n"
                "3. Leave calyx (green cap) attached — extends shelf life and looks better at market.\n"
                "4. Place gently in lined baskets (cushioned with dry grass). Never throw or drop.\n"
                "5. Harvest every 2-3 days during peak production — don't let fruits over-ripen on plant.\n\n"
                "Yield: 20-40 t/ha for hybrid varieties under good management; "
                "8-15 t/ha for local varieties. Peak production at weeks 8-14 after transplanting.\n\n"
                "Handling: Do not wash before storage. Avoid stacking more than 30 cm deep in containers."
            ),
        },
        {
            "topic": "tomato_post_harvest_handling",
            "crop": "tomato",
            "season": "dry",
            "practice_type": "post_harvest",
            "growth_stage": "post_harvest",
            "child": "How to store and preserve tomatoes after harvest in Casamance. Shade storage, solar drying method for tomato preservation.",
            "parent": (
                "Tomato Post-Harvest Handling — Casamance\n\n"
                "Tomatoes are highly perishable — fresh shelf life at ambient temperature "
                "(25-30 degC in Casamance) is only 3-5 days. Without refrigeration, "
                "value-addition processing is the key to reducing losses.\n\n"
                "Fresh storage (3-5 days):\n"
                "- Store at breaker or pink stage in a cool, shaded, well-ventilated room.\n"
                "- Single layer or maximum 2 layers in shallow crates or baskets.\n"
                "- Do NOT store in sealed plastic bags — ethylene buildup accelerates ripening and rot.\n"
                "- Evaporative cooling: wrap crates in wet jute sacks in shade — "
                "reduces temperature by 5-8 degC, extends shelf life 1-2 extra days.\n\n"
                "Solar drying (most practical preservation):\n"
                "1. Select firm, ripe (not over-ripe) fruits.\n"
                "2. Wash and slice into 0.5-1 cm thick rounds.\n"
                "3. Arrange on raised wire-mesh racks or palm-frond trays.\n"
                "4. Cover with fine-mesh netting to exclude flies.\n"
                "5. Dry in full sun 4-6 days, turning daily.\n"
                "6. Dried tomato: moisture below 10%, shelf life 6-12 months in sealed containers.\n\n"
                "Tomato paste (value addition for women cooperatives):\n"
                "Blend ripe tomatoes, cook down to thick paste, sun-dry or bottle. "
                "Women's cooperative processing groups in Ziguinchor and Bignona produce and sell "
                "tomato paste in local markets (marche de Ziguinchor, marche de Bignona).\n\n"
                "Market price guidance: Fresh tomato in Casamance peak season: 100-150 FCFA/kg. "
                "Dried: 1,500-2,500 FCFA/kg. Processing multiplies value 10-15x."
            ),
        },
        # ── GENERAL ──────────────────────────────────────────────────────────
        {
            "topic": "composting_advanced",
            "crop": "general",
            "season": "all",
            "practice_type": "soil",
            "growth_stage": "planning",
            "child": "How to make good compost in Casamance. Carbon to nitrogen ratio, compost recipe, turning schedule, how to know when compost is ready.",
            "parent": (
                "Advanced Composting for Casamance Smallholders\n\n"
                "Good compost requires the right balance of carbon-rich (brown) and "
                "nitrogen-rich (green) materials — the C:N ratio. Target: 25-30 parts carbon per "
                "1 part nitrogen by weight.\n\n"
                "Materials available in Casamance:\n"
                "High carbon (browns): Dry crop straw, dry grass, groundnut shells, dry leaves, "
                "cardboard (soak first), sawdust from Ziguinchor wood workshops.\n"
                "High nitrogen (greens): Green crop residues, fresh animal manure (cattle, goats, poultry), "
                "kitchen food scraps (no meat or oil), fresh grass clippings.\n\n"
                "Compost recipe (1 tonne batch):\n"
                "- 400 kg dry straw or crop residue (browns)\n"
                "- 300 kg fresh animal manure (greens)\n"
                "- 150 kg green plant material (greens)\n"
                "- 150 kg soil (introduces microorganisms)\n"
                "- Water: pile should feel like a wrung-out sponge\n\n"
                "Construction: Layer materials in a 1m x 1m x 1.2m heap. "
                "Alternate brown-green-brown layers 10 cm thick. "
                "Water each layer. Cover with plastic or banana leaves to retain moisture.\n\n"
                "Turning schedule:\n"
                "- Week 2: First turn — move outside in to center. Pile should be hot (60-70 degC inside).\n"
                "- Week 4: Second turn. Check moisture — add water if dry.\n"
                "- Week 6: Third turn.\n"
                "- Week 8-12: Compost ready when dark, earthy smell, original materials unrecognizable.\n\n"
                "Application rate: 3-5 t/ha for most crops. "
                "Double for degraded soils (recognized by pale color, crust formation, poor water infiltration)."
            ),
        },
        {
            "topic": "intercropping_design",
            "crop": "general",
            "season": "wet",
            "practice_type": "planting",
            "growth_stage": "planning",
            "child": "Which crops to grow together in Casamance. Cassava and maize intercropping, groundnut and millet combination, what works and what doesn't.",
            "parent": (
                "Intercropping Design for Casamance\n\n"
                "Intercropping (association culturale) is traditional in Casamance and "
                "reduces risk, improves income per hectare, and builds soil fertility.\n\n"
                "Cassava + Maize (recommended):\n"
                "Plant maize at 1 m x 1 m between cassava rows. "
                "Maize matures in 90 days (before cassava canopy closes at 3-4 months). "
                "Maize provides income while cassava establishes. No competition for light after 3 months. "
                "Maize residues mulch the cassava. Net yield gain 30-40% per hectare vs mono-crop maize.\n\n"
                "Cassava + Groundnut:\n"
                "Plant 2 rows groundnut between cassava rows at planting. "
                "Groundnut fixes nitrogen for cassava soil. Groundnut harvested at 90-100 days. "
                "Shade from cassava slightly reduces groundnut yield (10-15%) — "
                "accept this for the nitrogen benefit.\n\n"
                "Rice (monoculture only): Rice must be grown as monoculture in lowland paddies. "
                "Do not intercrop — flooding requirements and weed management incompatible with other crops.\n\n"
                "Groundnut + Millet (classic Casamance combination):\n"
                "Mixed stand: 1 hill millet per 2 hills groundnut. "
                "Millet provides structure for groundnut, different root depths avoid competition. "
                "Traditional combination with good resilience to variable rains.\n\n"
                "Tomato + Basil: Plant basil seedlings 30 cm from tomato plants. "
                "Repels whiteflies and tomato fruit borers. Basil sold in Ziguinchor market (extra income).\n\n"
                "Avoid: Tomato + groundnut (same Ralstonia wilt pathogen); "
                "Cassava + other root crops (deep soil competition)."
            ),
        },
        {
            "topic": "water_harvesting",
            "crop": "general",
            "season": "wet",
            "practice_type": "irrigation",
            "growth_stage": "planning",
            "child": "How to collect and save rainwater for farming in Casamance. Farm ponds, tied ridges, zai pits for dry season and drought coping.",
            "parent": (
                "Water Harvesting Techniques for Casamance\n\n"
                "Casamance receives 1000-1500mm rainfall in 5 months (June-October). "
                "Water harvesting captures this excess for use in dry spells and early dry season.\n\n"
                "Farm ponds (mares agricoles):\n"
                "- Dig a pond 6m x 6m x 2m deep in the lowest point of your field.\n"
                "- Line walls with compacted clay (laterite) to reduce seepage.\n"
                "- Volume: approximately 70,000 liters — enough to irrigate 0.2 ha of vegetables.\n"
                "- Cover surface with shade net or floating banana leaf mats to reduce evaporation.\n"
                "- Investment: 3-4 person-days of digging. NGO programs (ACF, Caritas) sometimes "
                "support pond construction with tools and materials.\n\n"
                "Tied ridges (billons cloisonnes):\n"
                "- Form ridges every 1 m across the slope.\n"
                "- Every 3-4 m along the ridge, build a small earthen cross-dam (cloisonnement).\n"
                "- Water collects in cells between dams instead of running off.\n"
                "- Increases soil moisture by 30-40% in upland fields. Reduces erosion.\n\n"
                "Zai pits (trous zai):\n"
                "- Dig small planting pits 30 cm diameter, 20 cm deep, spaced 1 m apart.\n"
                "- Fill each pit with 1-2 handfuls of compost or manure.\n"
                "- Plant into the pit. The pit concentrates both water and nutrients at the root zone.\n"
                "- Effective for degraded soils in the drier northern parts of Casamance (Kolda region).\n\n"
                "Contour planting: All crops planted along contour lines (same elevation), "
                "not up-down the slope. Combined with tied ridges, reduces runoff by 50-70%."
            ),
        },
        {
            "topic": "seed_saving",
            "crop": "general",
            "season": "all",
            "practice_type": "varieties",
            "growth_stage": "post_harvest",
            "child": "How to save seeds from your best plants in Casamance. Selecting mother plants, drying seeds, storing seeds, testing seed viability before planting.",
            "parent": (
                "Seed Saving for Casamance Farmers\n\n"
                "Saving your own seed reduces input costs and preserves locally adapted varieties. "
                "For open-pollinated (non-hybrid) varieties, saved seed performs as well as purchased.\n\n"
                "Selecting mother plants:\n"
                "- Select the healthiest, highest-yielding plants. Mark them with a stake or colored ribbon early.\n"
                "- For disease resistance: select from plants that stayed healthy when neighbors got sick.\n"
                "- For tomato/pepper: let 3-4 fruits reach full ripe red/yellow on plant before picking for seed.\n"
                "- For rice/maize: select from the tallest, fullest-panicled plants in the center of the field.\n"
                "- Never save from weak, diseased, or hybrid (F1) plants — F1 offspring are not uniform.\n\n"
                "Seed extraction:\n"
                "- Tomato: ferment pulp in water for 3 days, rinse, skim floating (non-viable) seeds. "
                "Good seeds sink.\n"
                "- Rice/maize: thresh and separate from chaff by winnowing.\n"
                "- Groundnut: select clean, uniform pods from best plants.\n\n"
                "Drying: Spread seeds on clean cloth in shade (not direct sun — kills embryo). "
                "Dry until seeds are hard and do not leave moisture marks on paper. "
                "Target moisture: below 12% for safe storage.\n\n"
                "Storage: Seal dried seeds in plastic bottles or metal tins with tight lids. "
                "Add a small packet of wood ash or dry chili powder as natural repellent. "
                "Store in a cool, dark, dry place. Label with crop, variety, date.\n\n"
                "Viability testing before planting: Place 10 seeds on wet paper towel. "
                "Roll up, keep moist and warm for 5-7 days. Count germinated seeds. "
                "8-10 germinated = excellent (>80%). 5-7 = acceptable. "
                "Below 5 = buy fresh seed (viability too low)."
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
                "growth_stage": entry.get("growth_stage", "planning"),
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
                "growth_stage": entry.get("growth_stage", "planning"),
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
