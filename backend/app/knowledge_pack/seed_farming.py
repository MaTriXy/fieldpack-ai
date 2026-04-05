"""Supplemental farming data for the Casamance Agriculture Knowledge Pack.

Extends the base seed_data.py with agronomic detail that a field worker
or extension agent needs beyond disease identification:
  - CROPS_EXTRA: soil pH range, seed rates, intercrop companions
  - PESTS: 12 economically important pests across all 5 crops
  - VARIETIES: 18 named varieties (improved + local) with performance data
  - FERTILIZATION_SCHEDULE: stage-specific inputs with XOF cost estimates
  - PLANTING_CALENDAR: month-by-month activities for cassava, rice, and tomato
  - STORAGE_GUIDELINES: post-harvest handling for the 3 hero crops
  - SOIL_REQUIREMENTS: texture, drainage, and amendment needs per crop

All data validated against ISRA (Institut Senegalais de Recherches Agricoles),
ANCAR, IITA, and AfricaRice published guidance for the Casamance/Ziguinchor region.
XOF prices reflect 2024 Ziguinchor market averages.
"""

import json

# ============================================================
# CROPS_EXTRA
# Additional columns for the crops table, keyed by crop_id.
# Applied via UPDATE after the base CROPS rows are inserted.
# ============================================================

CROPS_EXTRA = {
    1: {  # cassava
        "soil_ph_min": 5.5,
        "soil_ph_max": 6.5,
        "seed_rate_kg_per_ha": None,  # propagated by stem cuttings, not seed
        "intercrop_companions": json.dumps(["maize", "groundnut", "cowpea"]),
    },
    2: {  # rice
        "soil_ph_min": 5.0,
        "soil_ph_max": 7.0,
        "seed_rate_kg_per_ha": 60.0,
        "intercrop_companions": json.dumps([]),  # monoculture paddy
    },
    3: {  # maize
        "soil_ph_min": 5.5,
        "soil_ph_max": 7.5,
        "seed_rate_kg_per_ha": 20.0,
        "intercrop_companions": json.dumps(["cassava", "groundnut", "cowpea"]),
    },
    4: {  # groundnut
        "soil_ph_min": 5.5,
        "soil_ph_max": 7.0,
        "seed_rate_kg_per_ha": 80.0,
        "intercrop_companions": json.dumps(["millet", "maize", "sorghum"]),
    },
    5: {  # tomato
        "soil_ph_min": 6.0,
        "soil_ph_max": 6.8,
        "seed_rate_kg_per_ha": 0.3,  # seed for nursery transplant; field area equivalent
        "intercrop_companions": json.dumps(["basil", "onion", "marigold"]),
    },
}

# ============================================================
# PESTS (12)
# crop_id FK: 1=cassava 2=rice 3=maize 4=groundnut 5=tomato
# ============================================================

PESTS = [
    # --- Cassava pests (3) ---
    {
        "id": 1,
        "name": "Cassava Whitefly",
        "common_names": json.dumps([
            "Bemisia tabaci", "mouche blanche du manioc", "aleurode du manioc",
        ]),
        "crop_id": 1,
        "type": "insect",
        "damage_description": (
            "Adults and nymphs suck phloem sap from leaf undersides, causing yellowing, "
            "leaf distortion, and premature drop. Heavy infestations produce honeydew that "
            "promotes sooty mold. More critically, B. tabaci is the primary vector of "
            "Cassava Mosaic Disease (CMD) and Cassava Brown Streak Disease (CBSD), "
            "which cause up to 70% yield loss independently of direct feeding damage."
        ),
        "season_peak": "Peak populations during dry season (January-May) and early rains. "
                       "Populations crash in mid-rainy season. Second flush August-September.",
        "identification_notes": (
            "Tiny white-winged insects (1-2mm) on leaf undersides. When disturbed, "
            "a cloud of white flies rises from the plant. Nymphs are flat, oval, "
            "translucent yellow scales cemented to the leaf underside. "
            "Sooty black mold on upper leaf surfaces indicates active infestation."
        ),
        "control_organic": (
            "Neem oil spray (500g seeds crushed, soaked 10L water overnight, strained, "
            "2 drops soap, spray every 7-10 days on leaf undersides). "
            "Yellow sticky traps to monitor and reduce adult populations. "
            "Intercrop with maize — dense canopy reduces whitefly movement. "
            "Remove heavily infested leaves and burn them."
        ),
        "control_chemical": (
            "Imidacloprid (Confidor 200 SL): 0.5 mL/L water, spray leaf undersides. "
            "Limit to 2 applications per season to avoid resistance. "
            "Bifenthrin (Talstar) as alternative. Avoid broad-spectrum pyrethroids "
            "that kill natural enemies (parasitic wasps)."
        ),
        "economic_threshold": (
            "Treat when more than 50 whiteflies per leaf on 20% of monitored plants, "
            "or whenever CMD/CBSD symptoms are observed on neighboring plants."
        ),
        "prevention_notes": (
            "Plant CMD/CBSD-resistant varieties to reduce impact of whitefly-transmitted viruses. "
            "Source certified virus-free cuttings. Maintain field hygiene — remove infected plants. "
            "Avoid planting downwind of infected fields. Encourage natural enemies "
            "(Encarsia parasitic wasps) by minimizing chemical sprays."
        ),
    },
    {
        "id": 2,
        "name": "Cassava Green Mite",
        "common_names": json.dumps([
            "Mononychellus tanajoa", "acarien vert du manioc", "green spider mite",
        ]),
        "crop_id": 1,
        "type": "insect",
        "damage_description": (
            "Mites colonize young apical leaves, feeding on cell contents. Affected leaves "
            "develop angular yellow spots ('shot-hole' pattern), then bronze discoloration. "
            "Severe infestations stunt shoot growth and deform new leaves. "
            "Yield losses 13-80% depending on infestation timing and variety. "
            "Damage worst in dry season and during dry spells within the rainy season."
        ),
        "season_peak": "Dry season (November-May). Populations explode rapidly during drought stress. "
                       "Can collapse within 2 weeks when rains resume.",
        "identification_notes": (
            "Mites are tiny (0.3-0.4mm), pale green to yellow-green. Visible as moving "
            "dots on young leaves with hand lens. Look for silky webbing on apical leaves "
            "in heavy infestations. Characteristic angular yellow spots on leaves resemble "
            "nutrient deficiency — check for mite presence before applying fertilizer."
        ),
        "control_organic": (
            "Water-spray knockdown: forceful water spray dislodges mites. "
            "Sulfur dust (200g/ha) on new growth. Neem oil spray effective against nymphs. "
            "Introduce Typhlodromalus aripo predatory mite — widely distributed in Casamance "
            "through IITA biological control program and now established naturally."
        ),
        "control_chemical": (
            "Abamectin (Vertimec): 0.5 mL/L, target young leaves and apical growth. "
            "Acaricides (propargite, fenpyroximate) if abamectin unavailable. "
            "Do not use pyrethroids — they kill T. aripo predatory mite."
        ),
        "economic_threshold": (
            "Treat when more than 20 mites per young leaf on 30% of plants. "
            "Monitor apical leaves weekly during dry season."
        ),
        "prevention_notes": (
            "Maintain plant vigor with adequate moisture — stressed plants are more susceptible. "
            "Mulch to reduce soil temperature and drought stress. "
            "Intercrop to create humid microclimate unfavorable to mites. "
            "Avoid planting near dusty roadsides where mite pressure is highest."
        ),
    },
    {
        "id": 3,
        "name": "Variegated Grasshopper",
        "common_names": json.dumps([
            "Zonocerus variegatus", "criquet puant", "grasshopper criquets", "sauterelle bariolée",
        ]),
        "crop_id": 1,
        "type": "insect",
        "damage_description": (
            "Nymphs and adults defoliate cassava rapidly, consuming entire leaves and "
            "stripping stems. Large aggregations (several hundred per plant) can completely "
            "defoliate a field in days. Damage most severe on young plants. "
            "Also attacks maize, sweet potato, and many vegetables. "
            "Toxins in their body make them distasteful to most bird predators."
        ),
        "season_peak": "Post-harvest dry season (November-February). Nymphs hatch in "
                       "October-November, adults present November-March. Egg-laying in dry season.",
        "identification_notes": (
            "Adults 50-60mm, distinctive bright yellow and black warning coloration with "
            "red and blue patches on hindwings. Nymphs (instars 1-4) are black with "
            "yellow-orange spots, forming tight groups. Characteristic unpleasant smell "
            "when disturbed. Found on field borders first, migrating inward."
        ),
        "control_organic": (
            "Hand collection of nymphs in early morning when cold and sluggish — "
            "knock into containers of water with kerosene. "
            "Neem extract spray repels and reduces feeding. "
            "Early morning application of wood ash along field borders deters entry. "
            "Chickens and guinea fowl consume nymphs if present in field."
        ),
        "control_chemical": (
            "Chlorpyrifos (Dursban 48 EC): 2 mL/L, spray at first nymph sighting before "
            "aggregations form. Lambda-cyhalothrin (Karate) effective but use sparingly. "
            "Treat field borders and surrounding waste ground where grasshoppers concentrate."
        ),
        "economic_threshold": (
            "Act immediately when nymph aggregations of 20+ individuals are found on field borders. "
            "Do not wait for adults — adults are harder to control and disperse rapidly."
        ),
        "prevention_notes": (
            "Clear vegetation around field edges before October to remove egg-laying sites. "
            "Monitor field borders weekly from October onward. "
            "Coordinate with neighbors — grasshoppers move between farms. "
            "Cassava planted in June-July is most vulnerable — ensure early canopy closure."
        ),
    },
    # --- Rice pests (3) ---
    {
        "id": 4,
        "name": "African Rice Gall Midge",
        "common_names": json.dumps([
            "Orseolia oryzivora", "cécidomyie galligène du riz", "gall midge",
        ]),
        "crop_id": 2,
        "type": "insect",
        "damage_description": (
            "Larvae bore into the central leaf of young tillers, causing the tiller to "
            "form a characteristic hollow, onion-leaf shaped 'silver shoot' (galle). "
            "Infested tillers do not produce panicles. Yield losses 30-100% "
            "in heavily infested fields. Gall midge is the most damaging rice pest "
            "in the lowland areas of Casamance."
        ),
        "season_peak": "Peak infestation from tillering to panicle initiation — July to September. "
                       "Worst in years with late onset of rains and poor drainage.",
        "identification_notes": (
            "Look for pale green or silver tubular 'onion shoot' — a rolled, hollow leaf "
            "10-20cm long emerging from the tiller base. This is the diagnostic symptom. "
            "Pull gall apart gently — a white maggot (larva) 3-4mm is visible inside. "
            "Heavily infested fields show many such silver tubes among normal tillers."
        ),
        "control_organic": (
            "Drain fields at transplanting for 3-5 days — disrupts larval survival. "
            "Clip and remove galls immediately when first noticed to prevent adult emergence. "
            "Avoid excess nitrogen — lush growth attracts egg-laying females. "
            "Neem seed extract spray (10g seeds/L) at transplanting as repellent."
        ),
        "control_chemical": (
            "Carbofuran granules (Furadan 3G): 20 kg/ha broadcast at transplanting. "
            "Effective but highly toxic — use only with proper protective equipment. "
            "Fipronil (Regent): 1 mL/L spray as drench at base of tillers. "
            "Apply at first sign of damage or preventively in historically infested fields."
        ),
        "economic_threshold": (
            "Treat when 5% or more tillers show silver shoot symptoms. "
            "In areas with history of heavy infestation, treat preventively at transplanting."
        ),
        "prevention_notes": (
            "Plant WITA 4 or Gigante — moderate gall midge tolerance. "
            "Transplant at recommended density — overcrowded plants attract more egg-laying. "
            "Early transplanting (before July 15) reduces peak-pressure exposure. "
            "Improve field drainage — waterlogged fields have highest gall midge pressure."
        ),
    },
    {
        "id": 5,
        "name": "Yellow Rice Stem Borer",
        "common_names": json.dumps([
            "Diopsis thoracica", "Chilo suppressalis", "foreuse des tiges du riz",
            "borer de la tige", "deadheart borer",
        ]),
        "crop_id": 2,
        "type": "insect",
        "damage_description": (
            "Larvae bore into tillers at tillering stage, killing the central shoot "
            "('deadheart' — the central leaf turns brown and pulls out easily). "
            "At heading stage, boring into the culm causes 'whitehead' — the panicle "
            "becomes white with empty sterile grains. Yield losses 5-30%. "
            "Diopsis (stalk-eyed fly) is particularly prevalent in swampy Casamance lowlands."
        ),
        "season_peak": "Diopsis: August-October in flooded lowlands. "
                       "Chilo: multiple generations, July-November.",
        "identification_notes": (
            "Deadheart: central tiller brown and dead, pulls out easily. "
            "Whitehead: white panicle standing erect among green ones, grains are empty. "
            "Pull the affected tiller — look for caterpillar frass (sawdust-like material) inside. "
            "Diopsis adults: distinctive stalked eyes, yellow-orange markings, found on stems."
        ),
        "control_organic": (
            "Remove and destroy deadhearts immediately to prevent adult emergence. "
            "Light traps to attract and kill adults. "
            "Trichogramma parasitic wasp egg parasitoids — released in some ANCAR programs. "
            "Avoid split application of nitrogen that promotes excessive tillering."
        ),
        "control_chemical": (
            "Chlorantraniliprole (Coragen): 0.4 mL/L, spray at tiller base at first deadheart. "
            "Cartap hydrochloride: granule form applied at early tillering. "
            "Do not exceed 2 chemical applications per season."
        ),
        "economic_threshold": (
            "Treat at 10% deadheart incidence during vegetative stage. "
            "At heading, a single whitehead on 5% of plants justifies treatment."
        ),
        "prevention_notes": (
            "Synchronize planting in a village — staggered plantings maintain pest populations. "
            "Plant at recommended spacing — dense planting increases borer movement. "
            "Harvest stubble low and burn — destroys overwintering larvae in stems."
        ),
    },
    {
        "id": 6,
        "name": "Quelea Bird (Quelea quelea)",
        "common_names": json.dumps([
            "Quelea quelea", "travailleur à bec rouge", "mangemil", "oiseaux granivores",
        ]),
        "crop_id": 2,
        "type": "bird",
        "damage_description": (
            "Enormous flocks (millions of birds) descend on ripening rice fields, "
            "stripping panicles of grain within hours. Fields at milk-grain and "
            "soft-dough stages are most vulnerable. A flock of 1 million birds can "
            "eat 50 tonnes of grain per day. Total field loss in a single overnight "
            "attack is not uncommon in Casamance lowland areas."
        ),
        "season_peak": "October-November during rice grain-fill and harvest period. "
                       "Birds follow rainfall across the Sahel — timing varies year to year.",
        "identification_notes": (
            "Small (12cm) sparrow-like birds in enormous flocks — flocks appear as "
            "shifting clouds or dark smoke at a distance. Males: red bill, black face mask, "
            "yellowish-buff body. Females: streaked brown, red bill. "
            "Their collective feeding creates a loud rustling noise audible at distance."
        ),
        "control_organic": (
            "Continuous human presence in fields from panicle emergence through harvest — "
            "bird-scaring with drums, clappers, and voice. "
            "Reflective tape and CDs strung on lines across fields. "
            "Scarecrow effigies (changed daily — birds habituate quickly). "
            "Early morning patrol most critical (dawn feeding peak). "
            "Harvest as soon as grain is mature — do not delay."
        ),
        "control_chemical": (
            "Parathion avicide (Queletox) — used by national brigades on roosting sites. "
            "Not available to individual farmers. Report large Quelea concentrations "
            "to local ANCAR office for coordinated brigade action."
        ),
        "economic_threshold": (
            "Any Quelea sighting near ripening fields requires immediate bird-scaring action. "
            "Organize communal bird-scaring rotations with neighboring farmers."
        ),
        "prevention_notes": (
            "Plant early-maturing NERICA varieties (90-100 days) to finish before peak Quelea. "
            "Stagger planting with neighbors reduces attractive target area. "
            "Plant thorny hedges (Ziziphus) around field borders as partial deterrent. "
            "Register with ANCAR village committee for early-warning Quelea alerts."
        ),
    },
    # --- Maize pests (2) ---
    {
        "id": 7,
        "name": "Fall Armyworm",
        "common_names": json.dumps([
            "Spodoptera frugiperda", "chenille legionnaire d'automne",
            "légionnaire du maïs", "fall armyworm",
        ]),
        "crop_id": 3,
        "type": "insect",
        "damage_description": (
            "Young larvae feed on leaf surfaces ('windowing'), older larvae bore into "
            "the whorl and consume leaves from inside (characteristic ragged holes and "
            "frass in whorl). Larvae also attack ears at silk stage. "
            "Yield losses 20-73% without control. Invasive pest first reported in Senegal "
            "in 2016, now established and the primary maize pest in Casamance."
        ),
        "season_peak": "June-September (rainy season maize crop). First generation appears "
                       "within 2-3 weeks of crop emergence. Multiple overlapping generations.",
        "identification_notes": (
            "Look inside whorl for frass (soft brown pellets mixed with leaf shreds). "
            "Larva: 1-4cm caterpillar, brown-green-black variable coloration. "
            "Key identification: inverted Y marking on head capsule, four black spots "
            "on the second-to-last abdominal segment arranged in a square pattern. "
            "Adults: gray-brown moths with white spots on forewing; active at night."
        ),
        "control_organic": (
            "Apply sand/ash mixture into whorl — abrasive damages soft larvae. "
            "Bacillus thuringiensis (Bt) spray (DiPel or local formulation): "
            "apply into whorl weekly. Neem oil (4% solution) into whorl. "
            "Trichogramma egg parasitoid releases at egg stage. "
            "Hand-pick and destroy larvae in small plots. "
            "Attract natural enemies: spiders, ground beetles, braconid wasps."
        ),
        "control_chemical": (
            "Chlorantraniliprole (Coragen): 0.4 mL/L. Most effective against young larvae. "
            "Lambda-cyhalothrin + thiamethoxam (Voliam Trego): 0.3 mL/L. "
            "Spinetoram (Radiant): 0.5 mL/L. Apply into whorl, not foliar spray. "
            "Rotate modes of action to prevent resistance (FAW has shown rapid resistance in Africa)."
        ),
        "economic_threshold": (
            "Treat when 20% of plants show fresh whorl damage or when 1+ larvae per plant "
            "found during whorl inspection. Scout weekly from emergence to V8 stage."
        ),
        "prevention_notes": (
            "Early planting (first reliable rains) to reach V8 before peak moth flight. "
            "TZPB SR variety shows moderate tolerance. Intercrop with cassava or cowpea "
            "increases natural enemy populations. Push-pull system (Napier grass border, "
            "Desmodium intercrop) under investigation by ISRA Ziguinchor."
        ),
    },
    {
        "id": 8,
        "name": "Larger Grain Borer",
        "common_names": json.dumps([
            "Prostephanus truncatus", "grande bostryche", "bostryche destructeur",
            "greater grain borer",
        ]),
        "crop_id": 3,
        "type": "insect",
        "damage_description": (
            "Adults and larvae bore into stored maize cobs and grain, creating "
            "characteristic fine sawdust ('borer dust') and round exit holes. "
            "Can destroy 30-40% of grain in on-cob storage within 3-4 months. "
            "Also attacks stored cassava chips and dried roots. "
            "An invasive pest from Central America; highly destructive in sub-Saharan Africa."
        ),
        "season_peak": "Year-round in storage. Populations build during grain storage "
                       "October-April. Peak damage by February-March.",
        "identification_notes": (
            "Adult: 3-4mm cylindrical, dark brown-black beetle. "
            "Distinctive fine dust (powdery borer frass) accumulating below storage containers. "
            "Round 2-3mm exit holes in grain and cobs. "
            "Damage much more severe than weevils — hollowed grains and extensive tunneling. "
            "Check stored grain monthly: sieve sample, look for live adults and frass."
        ),
        "control_organic": (
            "Ash admixture: mix thoroughly 1 part dry wood ash with 10 parts grain before storage. "
            "Neem leaf admixture: dry neem leaves mixed at 1:50 ratio with grain. "
            "Hermetic storage: use PICS triple-layer bags or metal silos — grain suffocates pest. "
            "Solar disinfection: spread grain thinly on tarpaulin in direct sun for 3 hours "
            "before storage to kill initial infestation."
        ),
        "control_chemical": (
            "Actellic Super (pirimiphos-methyl + permethrin): 50mL/100kg grain. Mix thoroughly. "
            "Aluminum phosphide fumigation tablets for large storage volumes — "
            "requires proper sealing and safety training. Never use without adequate ventilation."
        ),
        "economic_threshold": (
            "Act at first detection — P. truncatus multiplies rapidly. "
            "One pair of adults can produce 500+ offspring per month under warm storage conditions."
        ),
        "prevention_notes": (
            "Harvest at correct moisture (13-14%). Dry thoroughly before storage. "
            "Clean storage facilities before loading new crop. "
            "Use hermetic storage bags (PICS or GrainSafe) — highly effective, available through ANCAR. "
            "Do not mix new grain with old grain in same storage."
        ),
    },
    # --- Groundnut pests (2) ---
    {
        "id": 9,
        "name": "Groundnut Aphid",
        "common_names": json.dumps([
            "Aphis craccivora", "puceron de l'arachide", "black aphid",
        ]),
        "crop_id": 4,
        "type": "insect",
        "damage_description": (
            "Dense colonies on young shoots and growing points suck sap, causing "
            "leaf curl, stunting, and shoot death. Excreted honeydew causes sooty mold. "
            "Most critically, A. craccivora is the primary vector of Groundnut Rosette Virus — "
            "even 5-minute feeding by a single viruliferous aphid can transmit the disease. "
            "Direct yield loss from feeding 10-25%; vector transmission loss up to 100%."
        ),
        "season_peak": "Late planting conditions (August-September). Early rains with cool dry spells. "
                       "Populations peak before natural enemy populations catch up.",
        "identification_notes": (
            "Shiny black aphids 1.5-2mm, densely packed on young stems and undersides of "
            "young leaflets. Winged forms (alates) appear when colony is stressed — these "
            "disperse and colonize new plants. White cast skins (exuviae) around colonies. "
            "Ants tend aphid colonies — ant trails to young shoots indicate aphid presence."
        ),
        "control_organic": (
            "Neem oil spray (3-4% solution) on infested shoots every 5-7 days. "
            "Insecticidal soap spray: 5g soap/L water. "
            "Kaolin clay dusting to deter aphids. "
            "Encourage parasitic wasps (Lysiphlebus) — do not spray when parasitized "
            "aphids (brown swollen mummies) visible in colony."
        ),
        "control_chemical": (
            "Imidacloprid seed treatment (Gaucho 70WS): 5g/kg seed — provides "
            "3-4 weeks systemic protection during critical seedling stage. "
            "Dimethoate (Rogor 40 EC): 1.5 mL/L foliar spray. "
            "Lambda-cyhalothrin (Karate 5 EC): 0.5 mL/L for heavy infestations."
        ),
        "economic_threshold": (
            "Treat when 20% of plants show aphid colonies of 10+ individuals, "
            "or immediately when Rosette symptoms appear on neighboring plants."
        ),
        "prevention_notes": (
            "Plant at first reliable rains (late June) — early-planted groundnut experiences "
            "lower aphid pressure than late-planted. "
            "Plant at full recommended density — gaps and thin stands increase aphid colonization. "
            "Plant rosette-resistant variety ICG 12991 where available. "
            "Rogue infected plants immediately — they serve as rosette virus reservoir."
        ),
    },
    {
        "id": 10,
        "name": "Termites (groundnut)",
        "common_names": json.dumps([
            "Microtermes sp.", "Odontotermes sp.", "termites", "termites souterrains",
        ]),
        "crop_id": 4,
        "type": "insect",
        "damage_description": (
            "Subterranean termites attack germinating seeds, roots, pods, and stems "
            "at soil level. Seeds may fail to germinate or seedlings collapse suddenly. "
            "Pods are hollowed out underground — looks like a normal plant until harvest "
            "reveals empty shells. In dry years, losses can reach 20-40% in sandy soils. "
            "Damage worsens on soils with undecomposed crop residues (termite food source)."
        ),
        "season_peak": "Dry spells within the rainy season and late-season (September-October) "
                       "when soil dries. Year-round threat to germinating seeds.",
        "identification_notes": (
            "Mud tubes or earth cartons on plant stems at or below soil level. "
            "Sudden wilting and death of plants without obvious above-ground disease. "
            "Dig up affected plant — roots and lower stem show tunneling and pitting. "
            "Pods at harvest are hollow with thin papery shell, sometimes filled with earth. "
            "Small (3-5mm) creamy-white workers or brown soldiers in soil around roots."
        ),
        "control_organic": (
            "Neem cake (tourteau de neem) incorporated in planting hole: 500 kg/ha. "
            "Wood ash and sand mixture at planting — poured into seed hole. "
            "Maintain soil moisture — well-irrigated soil reduces termite activity. "
            "Remove dead wood and undecomposed residues from field (termite food source). "
            "Diatomaceous earth dusted in furrow at sowing."
        ),
        "control_chemical": (
            "Chlorpyrifos (Dursban 48 EC): soil drench around affected plants 2 mL/L. "
            "Fipronil (Regent 0.3G) granules: 10 kg/ha in furrow at planting. "
            "Imidacloprid seed dressing also provides partial termite protection."
        ),
        "economic_threshold": (
            "Treat at planting in fields with known termite history. "
            "During growing season, treat when more than 5% of plants show wilting or "
            "soil tubes on stems."
        ),
        "prevention_notes": (
            "Bury crop residues thoroughly or compost them away from the field. "
            "Avoid planting groundnut immediately after clearing uncultivated land "
            "(old termite colonies present). "
            "Crop rotation with rice or maize reduces termite populations over 2-3 seasons. "
            "Maintain soil cover with mulch to retain moisture."
        ),
    },
    # --- Tomato pests (2) ---
    {
        "id": 11,
        "name": "Tomato Fruit Borer",
        "common_names": json.dumps([
            "Helicoverpa armigera", "ver de la tomate", "bollworm", "chenille de la tomate",
        ]),
        "crop_id": 5,
        "type": "insect",
        "damage_description": (
            "Larvae bore into flowers and developing fruits, creating entry holes filled "
            "with greenish frass. Infested fruits rot rapidly and fall. "
            "A single larva destroys 3-5 fruits during its development (moves between fruits). "
            "Yield losses 20-60% without control. Fruits with entry holes have no market value."
        ),
        "season_peak": "November-April (dry season tomato crop). Peaks at flowering and "
                       "early fruit set (December-January). Moth flights increase with warm nights.",
        "identification_notes": (
            "Entry hole 3-5mm diameter on fruit surface, often surrounded by frass and "
            "greenish wet material. Larva inside is 2-4cm, variable color (green/brown/pink) "
            "with pale lateral stripes. Often only head visible at entry hole. "
            "Adult moth: 15-20mm wingspan, forewings olive-gray with dark spots."
        ),
        "control_organic": (
            "Bt spray (Bacillus thuringiensis var. kurstaki, DiPel): 2g/L, spray on flowers "
            "and young fruits weekly. Most effective against small larvae before fruit entry. "
            "Neem oil 4% spray on flowers deters egg-laying. "
            "Pheromone traps (Helilure) to monitor adult moth flights. "
            "Remove and destroy infested fruits — reduces larval load for next generation. "
            "Marigold (Tagetes) border planting repels ovipositing females."
        ),
        "control_chemical": (
            "Emamectin benzoate (Proclaim 5 SG): 0.4g/L, highly effective against young larvae. "
            "Chlorantraniliprole (Coragen): 0.3 mL/L. Spinosad (Tracer): 0.5 mL/L. "
            "Spray in evening when moths are active. Begin spraying at first flower opening. "
            "Respect pre-harvest interval (PHI): minimum 3 days for most products."
        ),
        "economic_threshold": (
            "Treat when pheromone trap catches exceed 10 moths per night, or when 2% of "
            "fruits show fresh entry holes. Once larvae are inside fruits, spraying is ineffective."
        ),
        "prevention_notes": (
            "Use pheromone traps to time spray applications accurately. "
            "Remove and bury all fruit drop (no composting — larvae pupate in soil). "
            "Deep plough field after harvest to kill pupae. "
            "Do not plant tomato after cotton (shared pest population). "
            "Install 40-mesh insect-proof net around nursery."
        ),
    },
    {
        "id": 12,
        "name": "Tomato Whitefly",
        "common_names": json.dumps([
            "Bemisia tabaci", "mouche blanche de la tomate", "aleurode de la tomate",
        ]),
        "crop_id": 5,
        "type": "insect",
        "damage_description": (
            "Direct damage: phloem feeding causes leaf yellowing, wilting, and reduced "
            "fruit size. Honeydew deposits cause sooty mold on fruits reducing market quality. "
            "Vector damage: B. tabaci transmits Tomato Yellow Leaf Curl Virus (TYLCV) — "
            "one infected transplant can spread TYLCV to an entire field within 2-3 weeks. "
            "Combined losses can reach 80-100% in unprotected crops."
        ),
        "season_peak": "Year-round in dry season irrigated tomato. Peak populations "
                       "November-March. Populations migrate from pepper and other solanaceous crops.",
        "identification_notes": (
            "Identical to cassava whitefly (same species, B. tabaci) — "
            "tiny white-winged adults 1-2mm, powder-white color, found on leaf undersides. "
            "Nymphs: flat oval yellow-green scales on leaf underside. "
            "Yellow sticky traps catch adults easily. "
            "TYLCV suspicion: inspect field for upward leaf curl within 3 weeks of transplanting."
        ),
        "control_organic": (
            "Silver/aluminum mulch film on soil — reflective surface confuses and repels whiteflies. "
            "Highly effective, widely used in Casamance peri-urban gardens. "
            "Yellow sticky traps: 20 per hectare for monitoring and mass trapping. "
            "Neem oil spray (3%) on leaf undersides every 5-7 days. "
            "Inspect transplants carefully — refuse any with whitefly or TYLCV symptoms."
        ),
        "control_chemical": (
            "Spiromesifen (Oberon): 0.75 mL/L, targets nymphs on leaf undersides. "
            "Buprofezin (Applaud): 1 mL/L, insect growth regulator — reduces nymphs. "
            "Imidacloprid (Confidor): 0.5 mL/L as drench or foliar. "
            "Rotate modes of action every 2 applications — whitefly resistance to neonicotinoids "
            "is widespread in West Africa."
        ),
        "economic_threshold": (
            "Treat when average 10 adults per leaf on 25% of monitored plants. "
            "Apply preventively on transplanting day in TYLCV-endemic areas."
        ),
        "prevention_notes": (
            "Plant TYLCV-resistant varieties (Mongal F1). "
            "Use insect-proof net (40-mesh) in nursery phase. "
            "Create a barrier of 2-3 rows of maize or sorghum upwind of tomato block. "
            "Do not plant next to old tomato, pepper, or eggplant fields."
        ),
    },
]

# ============================================================
# VARIETIES (18)
# 3-4 per crop. local_names as JSON string.
# disease_resistance as JSON string describing resistances.
# ============================================================

VARIETIES = [
    # --- Cassava varieties (4) ---
    {
        "id": 1,
        "crop_id": 1,
        "name": "TME 419",
        "local_names": json.dumps(["TMS 30572", "419"]),
        "days_to_maturity": 270,
        "yield_potential_kg_per_ha": 25000.0,
        "disease_resistance": json.dumps({
            "CMD": "high",
            "CBSD": "moderate",
            "CBB": "moderate",
        }),
        "drought_tolerance": "high",
        "seed_source_in_region": "ISRA Ziguinchor station; NGO distribution programs (ANCAR, CRS)",
        "planting_density": "1m x 1m (10,000 plants/ha)",
        "notes": (
            "Most widely recommended improved cassava for Casamance. Developed by IITA, "
            "widely distributed in West Africa. High dry-matter content (35-38%) — "
            "preferred for gari and attieke processing. Requires 9 months for optimal yield."
        ),
    },
    {
        "id": 2,
        "crop_id": 1,
        "name": "IITA-TMS-IBA30572",
        "local_names": json.dumps(["IBA 30572", "IBA", "TMS 30572"]),
        "days_to_maturity": 300,
        "yield_potential_kg_per_ha": 30000.0,
        "disease_resistance": json.dumps({
            "CMD": "very high",
            "CBSD": "moderate",
            "CBB": "moderate",
        }),
        "drought_tolerance": "high",
        "seed_source_in_region": "ISRA Ziguinchor; IITA regional seed systems",
        "planting_density": "1m x 1m (10,000 plants/ha)",
        "notes": (
            "Highest CMD resistance available. Preferred in areas with high whitefly and "
            "CMD pressure. Slightly longer cycle (10-12 months). High yield potential "
            "under adequate rainfall. Dry matter 33-36%."
        ),
    },
    {
        "id": 3,
        "crop_id": 1,
        "name": "Soya (local)",
        "local_names": json.dumps(["Soya manioc", "manioc doux local"]),
        "days_to_maturity": 240,
        "yield_potential_kg_per_ha": 12000.0,
        "disease_resistance": json.dumps({
            "CMD": "low",
            "CBSD": "low",
            "CBB": "medium",
        }),
        "drought_tolerance": "medium",
        "seed_source_in_region": "Farmer-to-farmer exchange; village seed banks throughout Casamance",
        "planting_density": "1m x 1m or 0.8m x 1m",
        "notes": (
            "Traditional sweet cassava variety widely grown for fresh consumption and leaves. "
            "Low HCN content — tubers can be eaten raw or minimally processed. "
            "Lower yield but preferred flavor. Susceptible to CMD — do not plant where "
            "CMD is endemic. Shorter cycle (8 months) suits smaller plots."
        ),
    },
    {
        "id": 4,
        "crop_id": 1,
        "name": "Diola (local)",
        "local_names": json.dumps(["manioc Diola", "manioc amer local"]),
        "days_to_maturity": 360,
        "yield_potential_kg_per_ha": 15000.0,
        "disease_resistance": json.dumps({
            "CMD": "low",
            "CBSD": "unknown",
            "CBB": "medium",
            "anthracnose": "medium",
        }),
        "drought_tolerance": "high",
        "seed_source_in_region": "Farmer-to-farmer; village-level; widely available in Basse Casamance",
        "planting_density": "1m x 1m",
        "notes": (
            "Bitter landrace variety maintained by Diola communities. Long cycle (12+ months) "
            "but exceptional drought and poor-soil tolerance. High HCN — requires extensive "
            "fermentation/processing (attieke, gappal). Culturally important; grown alongside "
            "improved varieties for processing quality and food security resilience."
        ),
    },
    # --- Rice varieties (5) ---
    {
        "id": 5,
        "crop_id": 2,
        "name": "NERICA 1",
        "local_names": json.dumps(["NERICA L-1", "New Rice for Africa"]),
        "days_to_maturity": 100,
        "yield_potential_kg_per_ha": 4000.0,
        "disease_resistance": json.dumps({
            "blast": "moderate",
            "RYMV": "moderate",
            "BLB": "moderate",
        }),
        "drought_tolerance": "high",
        "seed_source_in_region": "ANCAR regional offices; SAED Casamance; village-level extension",
        "planting_density": "20cm x 20cm transplanted; 25cm x 25cm direct seeded",
        "notes": (
            "Upland interspecific hybrid (O. sativa x O. glaberrima). Short-cycle (100 days) — "
            "suited to erratic rainfall and shorter wet seasons. Best for upland plateau "
            "rice areas. Tills profusely. Good for food security — ready before WITA. "
            "Lower yield ceiling than lowland varieties."
        ),
    },
    {
        "id": 6,
        "crop_id": 2,
        "name": "NERICA 4",
        "local_names": json.dumps(["NERICA L-4", "NERICA quatre"]),
        "days_to_maturity": 95,
        "yield_potential_kg_per_ha": 4500.0,
        "disease_resistance": json.dumps({
            "blast": "high",
            "RYMV": "moderate",
            "gall_midge": "moderate",
        }),
        "drought_tolerance": "high",
        "seed_source_in_region": "ANCAR Ziguinchor; USAID/WFP seed distribution programs",
        "planting_density": "20cm x 20cm",
        "notes": (
            "Best-performing NERICA in Casamance trials (ISRA 2018-2022). "
            "Higher blast resistance than NERICA 1. 95-day cycle suitable for "
            "late-onset rainy seasons. Strong straw for organic matter return. "
            "Responds well to modest P fertilization (20 kg P2O5/ha)."
        ),
    },
    {
        "id": 7,
        "crop_id": 2,
        "name": "SAHEL 108",
        "local_names": json.dumps(["Sahel 108", "riz irrigue Sahel"]),
        "days_to_maturity": 120,
        "yield_potential_kg_per_ha": 7000.0,
        "disease_resistance": json.dumps({
            "blast": "high",
            "BLB": "moderate",
            "RYMV": "low",
        }),
        "drought_tolerance": "low",
        "seed_source_in_region": "SAED (Societe d'Amenagement et d'Exploitation des terres du Delta); "
                                  "irrigated perimeter schemes in Casamance",
        "planting_density": "20cm x 20cm transplanted",
        "notes": (
            "AfricaRice irrigated lowland variety. Highest yield potential of any rice "
            "in the region but requires reliable water management. Grown in formal "
            "irrigated perimeters (bas-fonds amenages). Not suitable for rain-fed upland. "
            "Excellent milling quality and grain length — premium price on Ziguinchor market."
        ),
    },
    {
        "id": 8,
        "crop_id": 2,
        "name": "WITA 4",
        "local_names": json.dumps(["WITA quatre", "riz WITA"]),
        "days_to_maturity": 130,
        "yield_potential_kg_per_ha": 5500.0,
        "disease_resistance": json.dumps({
            "RYMV": "high",
            "blast": "moderate",
            "gall_midge": "moderate",
        }),
        "drought_tolerance": "low",
        "seed_source_in_region": "ISRA Djibelor (Ziguinchor); ANCAR extension",
        "planting_density": "20cm x 20cm transplanted",
        "notes": (
            "AfricaRice lowland lowland variety. Best RYMV resistance among widely-grown "
            "varieties in Casamance lowlands. Recommended for bas-fonds with history of "
            "RYMV (yellow mottle). 130-day cycle — plant nursery by June 1 for "
            "transplanting before July 15."
        ),
    },
    {
        "id": 9,
        "crop_id": 2,
        "name": "Diofor (local African rice)",
        "local_names": json.dumps(["Oryza glaberrima", "riz rouge local", "riz Diola"]),
        "days_to_maturity": 160,
        "yield_potential_kg_per_ha": 2000.0,
        "disease_resistance": json.dumps({
            "RYMV": "high",
            "blast": "moderate",
            "BLB": "moderate",
        }),
        "drought_tolerance": "high",
        "seed_source_in_region": "Farmer-to-farmer; village seed banks; women's groups (groupements)",
        "planting_density": "25cm x 25cm direct-seeded or broadcast",
        "notes": (
            "Traditional African rice maintained by Diola women farmers of Casamance. "
            "Long cycle and lower yield than improved varieties but excellent adaptation "
            "to flooded mangrove soils and salinity tolerance. Cultural and food-security "
            "importance — mixed with improved varieties in subsistence plots. "
            "Red grain preferred for certain ceremonies; high iron content."
        ),
    },
    # --- Maize varieties (3) ---
    {
        "id": 10,
        "crop_id": 3,
        "name": "Suwan 1 SR",
        "local_names": json.dumps(["Suwan 1", "mais jaune ameliore"]),
        "days_to_maturity": 95,
        "yield_potential_kg_per_ha": 3500.0,
        "disease_resistance": json.dumps({
            "MSV": "moderate",
            "NCLB": "moderate",
            "streak_virus": "moderate",
        }),
        "drought_tolerance": "medium",
        "seed_source_in_region": "ISRA Bambey (national distribution); Ziguinchor agro-dealers",
        "planting_density": "75cm x 25cm, 2 plants per hill (53,000 plants/ha)",
        "notes": (
            "Open-pollinated yellow variety from CIMMYT/Thailand adapted for West Africa. "
            "Widely tested and recommended by ISRA for Senegal. 95-day cycle fits Casamance "
            "rainfall window. Slightly sensitive to waterlogging — avoid bas-fonds. "
            "Can save seed for replanting — important for resource-poor farmers."
        ),
    },
    {
        "id": 11,
        "crop_id": 3,
        "name": "TZPB SR",
        "local_names": json.dumps(["TZPB", "mais blanc ameliore"]),
        "days_to_maturity": 90,
        "yield_potential_kg_per_ha": 4000.0,
        "disease_resistance": json.dumps({
            "MSV": "high",
            "NCLB": "moderate",
            "fall_armyworm": "moderate",
        }),
        "drought_tolerance": "medium",
        "seed_source_in_region": "ISRA; agro-dealers Ziguinchor; NGO input programs",
        "planting_density": "75cm x 25cm, 2 plants per hill",
        "notes": (
            "IITA open-pollinated white maize. SR (Streak Resistant) designation indicates "
            "good maize streak virus tolerance. Shorter cycle (90 days) than Suwan 1. "
            "Preferred for fresh consumption (cobs) and flour. "
            "Moderate fall armyworm tolerance makes it less dependent on pesticide input."
        ),
    },
    {
        "id": 12,
        "crop_id": 3,
        "name": "Local Yellow (Casamance landrace)",
        "local_names": json.dumps(["mais local jaune", "mais traditionnel"]),
        "days_to_maturity": 110,
        "yield_potential_kg_per_ha": 1500.0,
        "disease_resistance": json.dumps({
            "MSV": "low",
            "NCLB": "medium",
            "smut": "medium",
        }),
        "drought_tolerance": "medium",
        "seed_source_in_region": "Farmer-to-farmer; village seed stores; local markets",
        "planting_density": "75cm x 30cm",
        "notes": (
            "Traditional yellow maize maintained by Casamance farmers for generations. "
            "Lower yield but valued for flavor, cultural identity, and zero seed cost. "
            "Often grown in mixed plots with sorghum, millet, or cassava. "
            "Recommended to replace with improved varieties on main production plots "
            "while maintaining small patches for seed security and cultural use."
        ),
    },
    # --- Groundnut varieties (3) ---
    {
        "id": 13,
        "crop_id": 4,
        "name": "ICG 12991",
        "local_names": json.dumps(["ICG 12991", "arachide ICRISAT"]),
        "days_to_maturity": 100,
        "yield_potential_kg_per_ha": 2500.0,
        "disease_resistance": json.dumps({
            "rosette": "high",
            "early_leaf_spot": "moderate",
            "late_leaf_spot": "moderate",
        }),
        "drought_tolerance": "medium",
        "seed_source_in_region": "ISRA Nioro du Rip (national groundnut program); "
                                  "ANCAR regional seed multiplication plots",
        "planting_density": "40cm x 15cm (167,000 plants/ha)",
        "notes": (
            "ICRISAT rosette-resistant variety. Best choice for areas with high Aphis craccivora "
            "pressure (Casamance interior). 100-day cycle fits rainy season. "
            "Good shelling percentage (72-74%). Not widely available locally — "
            "source from ISRA Ziguinchor or ANCAR seed programs."
        ),
    },
    {
        "id": 14,
        "crop_id": 4,
        "name": "55-437",
        "local_names": json.dumps(["cinquante cinq quatre-cent-trente-sept", "arachide 55", "GH 119-20"]),
        "days_to_maturity": 90,
        "yield_potential_kg_per_ha": 2000.0,
        "disease_resistance": json.dumps({
            "rosette": "low",
            "early_leaf_spot": "low",
            "late_leaf_spot": "low",
        }),
        "drought_tolerance": "high",
        "seed_source_in_region": "Widely available from local agro-dealers and markets throughout Senegal",
        "planting_density": "40cm x 15cm",
        "notes": (
            "ISRA variety, most widely grown groundnut in Senegal for decades. "
            "Early maturity (90 days), good drought escape. Produces Virginia-type large seeds "
            "preferred on export market and for oil extraction. "
            "High disease susceptibility — requires good crop rotation and rosette monitoring."
        ),
    },
    {
        "id": 15,
        "crop_id": 4,
        "name": "73-33",
        "local_names": json.dumps(["soixante-treize trente-trois", "TS 32-1"]),
        "days_to_maturity": 110,
        "yield_potential_kg_per_ha": 2200.0,
        "disease_resistance": json.dumps({
            "rosette": "low",
            "early_leaf_spot": "medium",
            "late_leaf_spot": "medium",
        }),
        "drought_tolerance": "medium",
        "seed_source_in_region": "ISRA Ziguinchor multiplication plots; cooperative seed programs",
        "planting_density": "40cm x 15cm",
        "notes": (
            "ISRA Valencia-type variety recommended for confectionery use. "
            "Higher leaf spot tolerance than 55-437 — suitable where leaf spot is endemic. "
            "Longer cycle (110 days) — plant by June 20 to avoid late-season drought. "
            "Good kernel quality — 3-4 seeds per pod, high oil content (48%)."
        ),
    },
    # --- Tomato varieties (3) ---
    {
        "id": 16,
        "crop_id": 5,
        "name": "Roma VF",
        "local_names": json.dumps(["Roma", "tomate Roma", "tomate paste"]),
        "days_to_maturity": 75,
        "yield_potential_kg_per_ha": 25000.0,
        "disease_resistance": json.dumps({
            "verticillium_wilt": "resistant",
            "fusarium_wilt": "resistant",
            "TYLCV": "low",
        }),
        "drought_tolerance": "medium",
        "seed_source_in_region": "Widely available from agro-dealers in Ziguinchor; SODEFITEX inputs",
        "planting_density": "60cm x 40cm (42,000 plants/ha) staked",
        "notes": (
            "Standard plum tomato for processing and fresh market. VF = Verticillium and "
            "Fusarium resistance. Firm fruit with high dry matter — suited to tomato paste "
            "making and drying in solar dryers. 75-day cycle from transplant. "
            "Widely known and accessible seed — good choice for first-time growers."
        ),
    },
    {
        "id": 17,
        "crop_id": 5,
        "name": "Mongal F1",
        "local_names": json.dumps(["Mongal", "tomate Mongal", "tomate hybride"]),
        "days_to_maturity": 70,
        "yield_potential_kg_per_ha": 45000.0,
        "disease_resistance": json.dumps({
            "TYLCV": "high",
            "TMV": "resistant",
            "fusarium_wilt": "resistant",
            "verticillium_wilt": "resistant",
        }),
        "drought_tolerance": "medium",
        "seed_source_in_region": "Agro-dealers Ziguinchor (Syngenta/Rijk Zwaan distributors); "
                                  "higher cost than OPVs",
        "planting_density": "60cm x 50cm staked (33,000 plants/ha)",
        "notes": (
            "Syngenta F1 hybrid with TYLCV resistance — the primary reason to choose this variety "
            "in Casamance where TYLCV is endemic via B. tabaci. Highest yield potential "
            "but F1 seed is expensive (~15,000 XOF/10g packet) and cannot be saved. "
            "Round fruit preferred on fresh market. Pays off investment in TYLCV-prone areas."
        ),
    },
    {
        "id": 18,
        "crop_id": 5,
        "name": "Tropimech",
        "local_names": json.dumps(["Tropimech", "tomate déterminée"]),
        "days_to_maturity": 80,
        "yield_potential_kg_per_ha": 30000.0,
        "disease_resistance": json.dumps({
            "TYLCV": "low",
            "fusarium_wilt": "resistant",
            "bacterial_wilt": "moderate",
        }),
        "drought_tolerance": "medium",
        "seed_source_in_region": "ISRA Djibelor trial plots; select Ziguinchor seed dealers",
        "planting_density": "70cm x 50cm (28,000 plants/ha); determinate growth, no staking needed",
        "notes": (
            "Determinate (bush) variety. No staking required — reduces labor cost. "
            "Concentrated fruit set — all fruits mature within 2-week window, "
            "suitable for cooperative processing campaigns. "
            "Moderate bacterial wilt tolerance compared to Roma VF. "
            "Tested by ISRA Djibelor in Casamance conditions with positive results."
        ),
    },
]

# ============================================================
# FERTILIZATION_SCHEDULE
# Cassava (ids 1-4), Rice (ids 5-9), Maize (ids 10-13), Tomato (ids 14-18)
# ============================================================

FERTILIZATION_SCHEDULE = [
    # --- Cassava (4 entries) ---
    {
        "id": 1,
        "crop_id": 1,
        "growth_stage": "Planting",
        "fertilizer_type": "Organic compost / manure",
        "dose_per_ha": "5-10 tonnes compost or 3-5 tonnes well-rotted manure",
        "application_method": "Broadcast and incorporate before ridging, or apply in planting hole",
        "timing_notes": "Apply 2-3 weeks before planting if broadcasting; "
                        "apply directly to planting hole at time of cutting insertion",
        "organic_alternative": "Compost from household food waste + crop residues. "
                               "Allow 6 weeks for aerobic composting before use.",
        "cost_estimate_xof": 10000,
    },
    {
        "id": 2,
        "crop_id": 1,
        "growth_stage": "Establishment (4-6 weeks after planting)",
        "fertilizer_type": "NPK 15-15-15",
        "dose_per_ha": "200 kg NPK 15-15-15",
        "application_method": "Basal placement 10-15cm from stem, cover with soil. "
                              "Do not apply on dry soil — wait for rain.",
        "timing_notes": "Apply at 4-6 weeks when 3-4 leaves are visible. "
                        "One application is usually sufficient for cassava.",
        "organic_alternative": "Top-dress with 2 tonnes well-rotted poultry manure + "
                               "500g rock phosphate per plant hole.",
        "cost_estimate_xof": 50000,
    },
    {
        "id": 3,
        "crop_id": 1,
        "growth_stage": "Canopy closure (3 months)",
        "fertilizer_type": "Urea (46% N)",
        "dose_per_ha": "50 kg urea",
        "application_method": "Side-dress 15cm from stem, in shallow furrow, cover with soil",
        "timing_notes": "Only if plants show signs of nitrogen deficiency (pale-yellow older leaves). "
                        "Apply when soil is moist. This application is optional.",
        "organic_alternative": "Intercrop with cowpea — fixes 40-80 kg N/ha and improves soil structure. "
                               "Chop and incorporate cowpea biomass before cassava canopy closes.",
        "cost_estimate_xof": 12500,
    },
    {
        "id": 4,
        "crop_id": 1,
        "growth_stage": "Pre-harvest (1 month before)",
        "fertilizer_type": "No chemical fertilizer",
        "dose_per_ha": "N/A",
        "application_method": "No fertilizer 1 month before harvest — avoids luxury uptake",
        "timing_notes": "Cease all fertilization at 7-8 months after planting. "
                        "Focus on soil moisture retention (mulch) for final bulking.",
        "organic_alternative": "Mulch with dry straw or leaf litter at 3 tonnes/ha — "
                               "retains moisture and regulates soil temperature for tuber bulking.",
        "cost_estimate_xof": 0,
    },
    # --- Rice (5 entries) ---
    {
        "id": 5,
        "crop_id": 2,
        "growth_stage": "Nursery (before transplanting)",
        "fertilizer_type": "DAP (18-46-0)",
        "dose_per_ha": "50 kg DAP on nursery bed (for seedlings to transplant 1 ha)",
        "application_method": "Broadcast on prepared nursery bed 1 day before sowing, "
                              "incorporate lightly by raking",
        "timing_notes": "Apply during nursery preparation in June. "
                        "Produces strong seedlings for transplanting at 3-4 weeks.",
        "organic_alternative": "Incorporate 200g compost per m2 of nursery bed. "
                               "Slightly slower seedling growth but adequate for NERICA varieties.",
        "cost_estimate_xof": 15000,
    },
    {
        "id": 6,
        "crop_id": 2,
        "growth_stage": "Transplanting / establishment",
        "fertilizer_type": "NPK 15-15-15",
        "dose_per_ha": "150 kg NPK 15-15-15",
        "application_method": "Broadcast and incorporate into flooded soil before transplanting, "
                              "or side-dress 7-10 days after transplanting",
        "timing_notes": "Apply within 7 days of transplanting. Flooded field takes up P and K "
                        "faster than dry-seeded systems.",
        "organic_alternative": "Broadcast 3 tonnes compost/ha and work into soil before flooding. "
                               "Add 300g bone meal per 10m2 for phosphorus.",
        "cost_estimate_xof": 37500,
    },
    {
        "id": 7,
        "crop_id": 2,
        "growth_stage": "Active tillering (3-4 weeks after transplanting)",
        "fertilizer_type": "Urea (46% N)",
        "dose_per_ha": "50 kg urea (first split)",
        "application_method": "Broadcast evenly on flooded field in early morning. "
                              "Maintain 5-7cm water level for 3 days after application.",
        "timing_notes": "First urea split at 3-4 weeks (active tillering onset). "
                        "Correct timing critical — too early loses N to leaching.",
        "organic_alternative": "Green manure incorporation (Sesbania): grow alongside rice for "
                               "2 weeks, chop and incorporate before flooding. Provides 30-60 kg N/ha.",
        "cost_estimate_xof": 12500,
    },
    {
        "id": 8,
        "crop_id": 2,
        "growth_stage": "Panicle initiation (6-7 weeks after transplanting)",
        "fertilizer_type": "Urea (46% N)",
        "dose_per_ha": "50 kg urea (second split)",
        "application_method": "Broadcast on flooded field. Apply in morning before sun is high.",
        "timing_notes": "Second urea split at panicle initiation stage. "
                        "This application determines spikelet number and panicle size. Critical.",
        "organic_alternative": "No effective organic substitute for panicle-stage N. "
                               "Ensure compost and green manure applied at establishment for baseline N.",
        "cost_estimate_xof": 12500,
    },
    {
        "id": 9,
        "crop_id": 2,
        "growth_stage": "Grain filling",
        "fertilizer_type": "Potassium chloride (KCl 60%)",
        "dose_per_ha": "30 kg KCl (optional, for flooded lowland only)",
        "application_method": "Broadcast on flooded field at beginning of grain fill",
        "timing_notes": "Optional application on soils known to be K-deficient. "
                        "Improves grain weight and resistance to lodging. "
                        "Skip on naturally K-rich ferralitic soils.",
        "organic_alternative": "Wood ash broadcast: 500 kg/ha. Provides K, Ca, and micronutrients. "
                               "Widely available in Casamance from household cooking fires.",
        "cost_estimate_xof": 7500,
    },
    # --- Maize (4 entries) ---
    {
        "id": 10,
        "crop_id": 3,
        "growth_stage": "Sowing / establishment",
        "fertilizer_type": "NPK 15-15-15 or DAP",
        "dose_per_ha": "150 kg NPK 15-15-15",
        "application_method": "Basal placement in planting hole or in furrow 5cm below seed. "
                              "Cover with thin layer of soil before placing seed.",
        "timing_notes": "Apply at sowing — first reliable rains mid-June. "
                        "Ensures P and K availability throughout crop cycle.",
        "organic_alternative": "One handful of compost (250g) per planting hole + "
                               "1 kg well-rotted manure/m2 broadcast before planting.",
        "cost_estimate_xof": 37500,
    },
    {
        "id": 11,
        "crop_id": 3,
        "growth_stage": "V4-V6 (4-6 leaves, 3-4 weeks)",
        "fertilizer_type": "Urea (46% N)",
        "dose_per_ha": "75 kg urea (first split)",
        "application_method": "Side-dress 10cm from base of each plant, in furrow, cover with soil. "
                              "Apply when soil is moist (after rain or irrigation).",
        "timing_notes": "First N split at V4-V6. Critical for leaf area development "
                        "and cob number determination. Do not delay past V6.",
        "organic_alternative": "Side-dress with 500g poultry manure per plant (ring placement). "
                               "Or broadcast 2 tonnes compost/ha and ridge in.",
        "cost_estimate_xof": 18750,
    },
    {
        "id": 12,
        "crop_id": 3,
        "growth_stage": "V8-V10 (8-10 leaves, 5-6 weeks)",
        "fertilizer_type": "Urea (46% N)",
        "dose_per_ha": "75 kg urea (second split)",
        "application_method": "Side-dress 15cm from plant base. Hill-up soil around base after application.",
        "timing_notes": "Second N split determines kernel number and cob fill. "
                        "Apply 2-3 weeks before tasseling. This is the single most important application.",
        "organic_alternative": "Same as first split organic option. "
                               "Neem cake (500 kg/ha) also provides slow-release N and pest suppression.",
        "cost_estimate_xof": 18750,
    },
    {
        "id": 13,
        "crop_id": 3,
        "growth_stage": "Tasseling / silking",
        "fertilizer_type": "No additional N",
        "dose_per_ha": "N/A",
        "application_method": "No additional fertilizer at this stage",
        "timing_notes": "Focus on water supply (critical moisture period). "
                        "Potassium foliar spray (2% KCl solution) can improve kernel fill "
                        "if soil K is limiting. Optional.",
        "organic_alternative": "Wood ash foliar spray (10g/L water, filtered) provides K and micronutrients. "
                               "Apply in evening to leaves.",
        "cost_estimate_xof": 0,
    },
    # --- Tomato (5 entries) ---
    {
        "id": 14,
        "crop_id": 5,
        "growth_stage": "Nursery preparation",
        "fertilizer_type": "Organic compost",
        "dose_per_ha": "10 kg compost per m2 of nursery bed (for 1-ha equivalent transplant)",
        "application_method": "Thoroughly mix compost into top 15cm of nursery bed soil before seeding",
        "timing_notes": "Nursery prepared in October. Compost application gives seedlings "
                        "strong root development for 4-5 week nursery period.",
        "organic_alternative": "Coconut coir + river sand + compost (1:1:1) as nursery medium "
                               "in trays — superior to field nursery, reduces transplanting shock.",
        "cost_estimate_xof": 5000,
    },
    {
        "id": 15,
        "crop_id": 5,
        "growth_stage": "Transplanting (establishment)",
        "fertilizer_type": "DAP (18-46-0) + compost",
        "dose_per_ha": "100 kg DAP + 5 tonnes compost",
        "application_method": "Compost incorporated at bed preparation. DAP placed 10cm from "
                              "transplant hole, covered with soil, then plant transplant.",
        "timing_notes": "November transplant. Compost applied 2 weeks before; DAP at transplant day. "
                        "Water in immediately after transplanting.",
        "organic_alternative": "Planting-hole organic: 500g compost + 50g bone meal in each hole. "
                               "Water with diluted liquid compost tea (1:10 ratio) at transplanting.",
        "cost_estimate_xof": 37500,
    },
    {
        "id": 16,
        "crop_id": 5,
        "growth_stage": "Vegetative growth (2-3 weeks after transplant)",
        "fertilizer_type": "Urea (46% N)",
        "dose_per_ha": "50 kg urea",
        "application_method": "Drench in irrigation water (fertigation) or side-dress 10cm from stem, "
                              "cover with soil, water immediately.",
        "timing_notes": "Promotes rapid vegetative establishment. Apply at 2-3 weeks when "
                        "transplants are established (not wilting). Critical for leaf area.",
        "organic_alternative": "Liquid manure fertigation: 20% slurry of chicken manure in water, "
                               "diluted 1:5, applied at base of plants. Weekly application.",
        "cost_estimate_xof": 12500,
    },
    {
        "id": 17,
        "crop_id": 5,
        "growth_stage": "Flowering and fruit set",
        "fertilizer_type": "NPK 15-15-30 (high K formula) or calcium nitrate",
        "dose_per_ha": "150 kg NPK 15-15-30",
        "application_method": "Fertigation or side-dress every 2 weeks during flowering period. "
                              "Calcium nitrate: 50 kg/ha as separate application.",
        "timing_notes": "December-January. High K promotes fruit quality, reduces blossom end rot. "
                        "Ca essential for preventing blossom end rot (BER) in tomato.",
        "organic_alternative": "Crushed eggshells or lime (200 kg/ha) for calcium. "
                               "Wood ash (500 kg/ha) for potassium. Compost tea application weekly.",
        "cost_estimate_xof": 40000,
    },
    {
        "id": 18,
        "crop_id": 5,
        "growth_stage": "Fruiting / harvest period",
        "fertilizer_type": "Potassium sulphate (50% K2O)",
        "dose_per_ha": "50 kg K2SO4",
        "application_method": "Fertigation preferred. Side-dress if fertigation not available.",
        "timing_notes": "January-March during harvest period. K2SO4 preferred over KCl — "
                        "sulphate form improves flavor (sugar:acid ratio) without chloride buildup.",
        "organic_alternative": "Banana peel tea: soak banana peels 48h in water, dilute 1:5, "
                               "apply as fertigation — good K source with micronutrients.",
        "cost_estimate_xof": 15000,
    },
]

# ============================================================
# PLANTING_CALENDAR
# Cassava (crop_id 1), Rice (crop_id 2), Tomato (crop_id 5)
# is_critical: 1=critical, 0=routine
# ============================================================

PLANTING_CALENDAR = [
    # --- Cassava calendar ---
    {
        "id": 1, "crop_id": 1, "month": 4,
        "activity": "Soil testing and land assessment",
        "details": "Test soil pH before main planting season. Target 5.5-6.5. "
                   "Apply lime (dolomite) at 1-2 tonnes/ha if pH < 5.5. "
                   "Identify poorly drained areas — cassava roots rot in waterlogged soil.",
        "is_critical": 0,
    },
    {
        "id": 2, "crop_id": 1, "month": 5,
        "activity": "Land preparation",
        "details": "Slash and burn (or slash and mulch), deep plough or hand-dig to 30cm. "
                   "Form ridges or mounds on slopes for drainage. Incorporate compost or manure. "
                   "Mark planting positions at 1m x 1m spacing.",
        "is_critical": 1,
    },
    {
        "id": 3, "crop_id": 1, "month": 6,
        "activity": "Cutting selection and planting",
        "details": "Select cuttings 20-25cm long from middle third of mature healthy stems (8-12 months old). "
                   "Discard tips (too soft) and base sections. Plant at 45-degree angle, "
                   "3-4 nodes underground. Optimal: first week of June at start of rains. "
                   "Planting in dry soil possible — cuttings can wait 2-3 weeks for rain.",
        "is_critical": 1,
    },
    {
        "id": 4, "crop_id": 1, "month": 7,
        "activity": "First weeding and fertilizer application",
        "details": "Weed thoroughly at 4-6 weeks after planting — this is the most critical weeding. "
                   "Apply NPK 15-15-15 (200 kg/ha) at this time, placed 10-15cm from stem. "
                   "Check for CMD symptoms on young leaves — rogue any showing mosaic.",
        "is_critical": 1,
    },
    {
        "id": 5, "crop_id": 1, "month": 8,
        "activity": "Second weeding and pest monitoring",
        "details": "Second weeding at 10-12 weeks. Canopy beginning to close — "
                   "last hand-weeding opportunity before plants shade out weeds. "
                   "Check for cassava green mite (look at apical leaves). "
                   "Monitor for variegated grasshopper entry from field borders.",
        "is_critical": 0,
    },
    {
        "id": 6, "crop_id": 1, "month": 9,
        "activity": "Canopy closure monitoring",
        "details": "Cassava canopy should be closed by this point. No further weeding needed. "
                   "Count missing plants — up to 10% gaps acceptable, replant gaps if possible. "
                   "Begin planning harvesting schedule (first harvest possible at 8 months = February).",
        "is_critical": 0,
    },
    {
        "id": 7, "crop_id": 1, "month": 11,
        "activity": "Grasshopper season begins — monitoring",
        "details": "November marks start of grasshopper (Zonocerus variegatus) nymph season. "
                   "Walk field borders daily. At first nymph sighting, mobilize community "
                   "for early-morning hand collection before aggregations form and disperse.",
        "is_critical": 1,
    },
    {
        "id": 8, "crop_id": 1, "month": 2,
        "activity": "First possible harvest (8-month varieties)",
        "details": "Local sweet varieties (Soya, Diola) can be harvested from February onward. "
                   "TME 419 best at 10-12 months (April-June). "
                   "Stagger harvests — cassava stays in ground safely for 12-18 months. "
                   "Process tubers within 48 hours — they deteriorate rapidly after cutting.",
        "is_critical": 1,
    },
    {
        "id": 9, "crop_id": 1, "month": 4,
        "activity": "Main harvest and planting material selection",
        "details": "Harvest TME 419 and IBA30572 at 10-12 months. "
                   "Reserve healthy stems (middle sections) for next season's cuttings. "
                   "Store cuttings in shade, horizontal or slightly inclined, for up to 4 weeks. "
                   "Begin land preparation for next cycle.",
        "is_critical": 1,
    },
    # --- Rice calendar ---
    {
        "id": 10, "crop_id": 2, "month": 5,
        "activity": "Nursery site preparation",
        "details": "Select nursery site near water source. Prepare 1/20 of transplant area. "
                   "Till to 20cm, form flat beds 1.2m wide. Apply compost 3 kg/m2. "
                   "Flood and drain twice to soften soil and stimulate weed seed germination.",
        "is_critical": 0,
    },
    {
        "id": 11, "crop_id": 2, "month": 6,
        "activity": "Nursery sowing — CRITICAL TIMING",
        "details": "Sow pre-soaked (48h) rice seed densely on nursery bed: "
                   "40-50g pre-germinated seed per m2. For 1 ha, prepare 400m2 nursery. "
                   "For WITA 4 (130-day variety): sow by June 1. "
                   "For NERICA 1/4 (95-100 day): sow by July 1. "
                   "Maintain 2-3cm water on nursery from day 3 onward.",
        "is_critical": 1,
    },
    {
        "id": 12, "crop_id": 2, "month": 7,
        "activity": "Main field preparation and transplanting",
        "details": "Plough main field and flood 5-7 days before transplanting. "
                   "Puddle soil to destroy weeds. Apply NPK at transplanting. "
                   "Transplant 3-4 week old seedlings (3-5 tillers). "
                   "Spacing: 20x20cm, 1-2 seedlings per hill. "
                   "Transplant by July 15 — each week late reduces yield 5-8%.",
        "is_critical": 1,
    },
    {
        "id": 13, "crop_id": 2, "month": 8,
        "activity": "First weeding and tillering fertilizer",
        "details": "Hand weed or use rotary hoe 15-20 days after transplanting. "
                   "Apply first urea split (50 kg/ha) by broadcast at active tillering. "
                   "Maintain 5-7cm flood depth. Monitor for gall midge silver shoots "
                   "and stem borer deadhearts — treat if >5% affected.",
        "is_critical": 1,
    },
    {
        "id": 14, "crop_id": 2, "month": 9,
        "activity": "Panicle initiation fertilizer and bird-scaring preparation",
        "details": "Apply second urea split (50 kg/ha) at panicle initiation. "
                   "Begin organizing village bird-scaring rotation schedule. "
                   "Build bird-scaring hides (abris de gardiennage) at field corners. "
                   "Harvest any remaining nursery material; do not waste seedlings.",
        "is_critical": 1,
    },
    {
        "id": 15, "crop_id": 2, "month": 10,
        "activity": "Bird scaring at grain fill",
        "details": "Continuous bird scaring required from panicle emergence through harvest. "
                   "Organize communal rotation (2-hour shifts, dawn to dusk minimum). "
                   "Install reflective tape and noise-making devices on poles across field. "
                   "Contact ANCAR if Quelea flocks are sighted in region.",
        "is_critical": 1,
    },
    {
        "id": 16, "crop_id": 2, "month": 11,
        "activity": "Harvest and post-harvest",
        "details": "Harvest when 80-85% of grains are golden (not when all panicles are ripe — "
                   "delays increase bird and shattering losses). Cut at 20-25cm above ground. "
                   "Bundle, thresh within 24 hours. Sun-dry to 14% moisture (2-4 sunny days). "
                   "Bag in clean jute sacks, store in ventilated raised storage.",
        "is_critical": 1,
    },
    # --- Tomato calendar ---
    {
        "id": 17, "crop_id": 5, "month": 9,
        "activity": "Soil preparation and irrigation check",
        "details": "Prepare field beds: raised beds (30cm high, 1m wide) or flat beds with furrows. "
                   "Check irrigation system (drip or furrow). Flush pipes. "
                   "Apply compost (5 t/ha) and incorporate. Test soil pH — adjust to 6.0-6.8 with lime. "
                   "Order seed and inputs from Ziguinchor agro-dealer.",
        "is_critical": 0,
    },
    {
        "id": 18, "crop_id": 5, "month": 10,
        "activity": "Nursery establishment",
        "details": "Sow tomato seed in seedling trays or raised nursery beds (30 seeds/m2). "
                   "Use sterilized potting mix or compost:sand 1:1. "
                   "Cover trays with shade cloth (50%) for 5-7 days. "
                   "Water twice daily. Apply dilute DAP solution at day 7 if seedlings are pale. "
                   "Use 40-mesh insect-proof net over nursery to prevent TYLCV infection.",
        "is_critical": 1,
    },
    {
        "id": 19, "crop_id": 5, "month": 11,
        "activity": "Hardening off and transplanting",
        "details": "Reduce watering 5 days before transplanting (hardening). "
                   "Transplant at 4-5 weeks when seedlings are 15-20cm tall. "
                   "Transplant in late afternoon or on cloudy day. "
                   "Water immediately and daily for first week. "
                   "Install silver reflective mulch to repel whitefly. "
                   "Space 60cm x 40cm. Insert stakes at transplanting.",
        "is_critical": 1,
    },
    {
        "id": 20, "crop_id": 5, "month": 12,
        "activity": "Pruning, training, and flowering care",
        "details": "For indeterminate varieties (Mongal): pinch lateral shoots below first flower cluster. "
                   "Tie main stem to stake at 2-3 nodes. "
                   "Apply NPK high-K fertilizer at flower opening. "
                   "Inspect daily for Helicoverpa moths and TYLCV symptoms. "
                   "Remove any TYLCV-showing plants immediately — they are a virus source.",
        "is_critical": 1,
    },
    {
        "id": 21, "crop_id": 5, "month": 1,
        "activity": "Fruit development and harvest beginning",
        "details": "Apply K2SO4 fertilizer for fruit quality. Monitor fruit borer entry holes. "
                   "Begin harvest at breaker stage (first color flush) for market transport. "
                   "Harvest 3x per week during peak production. "
                   "Sort: grade A (intact, >80g) for fresh market; grade B for processing; cull for home use. "
                   "Cool fruits in shade immediately after harvest.",
        "is_critical": 1,
    },
    {
        "id": 22, "crop_id": 5, "month": 2,
        "activity": "Peak harvest and market logistics",
        "details": "Peak production period. Harvest every 2-3 days. "
                   "Coordinate with market sellers or cooperative for transport. "
                   "Tomato price typically drops mid-February as regional supply peaks. "
                   "Consider processing excess into tomato paste, sun-dried tomatoes, or tomato powder. "
                   "Solar drying trays can process 20 kg fresh per tray per day.",
        "is_critical": 0,
    },
    {
        "id": 23, "crop_id": 5, "month": 3,
        "activity": "End of season and field cleanup",
        "details": "Final harvest by March 15 before heat stress causes flower drop. "
                   "Remove all plant material and burn (reduces Helicoverpa pupae and TYLCV inoculum). "
                   "Deep plough to bury remaining soil pupae. "
                   "Record yields, input costs, and market prices for season review.",
        "is_critical": 0,
    },
]

# ============================================================
# STORAGE_GUIDELINES
# Cassava (crop_id 1), Rice (crop_id 2), Tomato (crop_id 5)
# ============================================================

STORAGE_GUIDELINES = [
    # --- Cassava (2 methods) ---
    {
        "id": 1,
        "crop_id": 1,
        "method": "In-ground storage (leave in field)",
        "optimal_temp_c": "ambient (25-35)",
        "moisture_target_pct": None,  # soil moisture maintained naturally
        "max_duration_months": 6,
        "pest_risks": "Termite damage to roots increases after month 12. "
                      "Variegated grasshopper defoliation weakens roots. "
                      "Over-mature roots become woody and pithy.",
        "quality_indicators": "Roots remain firm when pressed. Skin intact. "
                              "Harvest immediately if roots crack or show soft spots.",
        "local_materials": "No materials needed — the field is the storage. "
                           "Mark harvested rows to avoid re-digging.",
    },
    {
        "id": 2,
        "crop_id": 1,
        "method": "Processed product storage (gari / attieke)",
        "optimal_temp_c": "25-30",
        "moisture_target_pct": 10.0,
        "max_duration_months": 6,
        "pest_risks": "Weevils and moisture cause clumping and mold in poorly-sealed containers. "
                      "Grain borer (Prostephanus truncatus) can attack dry gari.",
        "quality_indicators": "Free-flowing granules, no clumping, no off smell, cream-white color. "
                              "If gari turns yellow or smells musty, dry immediately in sun.",
        "local_materials": "Woven plastic or jute sacks, sealed with cord. "
                           "Elevate on wooden pallets 30cm from ground. "
                           "Ash or neem leaves mixed with gari extends shelf life. "
                           "Traditional ceramic pots with tight lids for small quantities.",
    },
    # --- Rice (2 methods) ---
    {
        "id": 3,
        "crop_id": 2,
        "method": "Bag storage on raised platform",
        "optimal_temp_c": "25-32",
        "moisture_target_pct": 14.0,
        "max_duration_months": 8,
        "pest_risks": "Rice weevil (Sitophilus oryzae), rice moth (Corcyra cephalonica), "
                      "larger grain borer if harvest contaminated at field. "
                      "Mold and heating if moisture above 14%.",
        "quality_indicators": "White to light golden grain, no discoloration. "
                              "Grain breaks cleanly, no soft or hollow kernels. "
                              "No musty or sour odor. Moisture: test by biting — clean crack at 14%.",
        "local_materials": "Jute sacks (50 kg), wooden raised platforms (elevated 50cm from earth floor). "
                           "Wood ash mixed at 1% by weight deters weevils. "
                           "PICS triple-layer bags (available ANCAR): hermetic seal, no pesticide needed.",
    },
    {
        "id": 4,
        "crop_id": 2,
        "method": "Traditional granary (grenier familial)",
        "optimal_temp_c": "ambient",
        "moisture_target_pct": 14.0,
        "max_duration_months": 12,
        "pest_risks": "Rat damage (Mastomys natalensis) — most significant loss cause in traditional granaries. "
                      "Weevils, flour beetles. Fire risk if granary walls are dry grass.",
        "quality_indicators": "Same as bag storage. Inspect stored rice monthly — "
                              "sieve 500g sample, check for live insects and frass.",
        "local_materials": "Traditional raised wooden granary (sur pilotis) with smooth metal rat guards "
                           "on legs. Mud-plastered walls reduce weevil entry. "
                           "Neem leaves (Azadirachta indica) layered with paddy deter insects. "
                           "Seal cracks in granary walls before loading.",
    },
    # --- Tomato (2 methods) ---
    {
        "id": 5,
        "crop_id": 5,
        "method": "Fresh storage in shade (short-term market)",
        "optimal_temp_c": "18-22",
        "moisture_target_pct": None,
        "max_duration_months": 0,  # days, not months — max 5-7 days
        "pest_risks": "Fruit fly (Ceratitis capitata) lays eggs in ripe fruit. "
                      "Botrytis gray mold in humid storage. "
                      "Physical bruising causes rapid bacterial rot.",
        "quality_indicators": "Firm to slight give, bright uniform color, no cracks or soft spots, "
                              "fresh green calyx. Discard any fruit with stem-end rot (black) immediately.",
        "local_materials": "Ventilated wooden crates lined with dry banana leaves. "
                           "Store single layer deep. Dry, cool, shaded room or tukul. "
                           "Do not store with onions or ethylene-producing fruits (mangoes). "
                           "For 1-3 day transport: wrap individually in newspaper.",
    },
    {
        "id": 6,
        "crop_id": 5,
        "method": "Sun-drying (tomato powder and dried slices)",
        "optimal_temp_c": "35-50 (solar dryer interior)",
        "moisture_target_pct": 8.0,
        "max_duration_months": 6,
        "pest_risks": "Fly contamination during open-air drying. "
                      "Mold rehydration if stored in humid conditions. "
                      "Color loss if not dried quickly enough.",
        "quality_indicators": "Dark red, leathery texture, not brittle. "
                              "Bends without cracking (not yet over-dried). "
                              "No white mold specks. Sweet-acidic concentrated tomato smell.",
        "local_materials": "Solar dryer: wooden frame, wire mesh tray, transparent polythene cover "
                           "(locally made for ~5,000 XOF). Alternative: raised wire mesh on roof. "
                           "Store dried product in sealed glass jars or airtight plastic containers. "
                           "Add a small silica gel packet if available to prevent moisture reabsorption.",
    },
]

# ============================================================
# SOIL_REQUIREMENTS (1 per crop, all 5 crops)
# ============================================================

SOIL_REQUIREMENTS = [
    {
        "id": 1,
        "crop_id": 1,  # cassava
        "ph_min": 5.5,
        "ph_max": 6.5,
        "preferred_texture": "Sandy loam to loam. Tolerates poor, light-textured soils better "
                             "than most crops. Avoids heavy clay.",
        "drainage_needs": "Well-drained essential — cannot tolerate waterlogging. "
                          "Root rots occur within 48h of standing water. "
                          "Mound or ridge planting on flat terrain.",
        "amendments_needed": json.dumps([
            "Lime: 1-2 t/ha if pH < 5.5 (common in ferralitic Casamance soils)",
            "Compost: 5-10 t/ha improves sandy soil water retention",
            "Rock phosphate: 200 kg/ha if P-deficient (red ferralitic soils)",
        ]),
        "preparation_notes": (
            "Minimum tillage sufficient if soil not compacted. "
            "Deep ploughing (30cm) beneficial on first-year plots with previous hardpan. "
            "Ridging (height 30cm) recommended on slopes for erosion control. "
            "Avoid cultivating when soil is waterlogged — causes compaction."
        ),
    },
    {
        "id": 2,
        "crop_id": 2,  # rice
        "ph_min": 5.0,
        "ph_max": 7.0,
        "preferred_texture": "Clay to clay-loam for flooded paddy. "
                             "Sandy-loam acceptable for upland NERICA varieties.",
        "drainage_needs": "Flooded paddy (lowland): maintain 5-10cm water throughout growing season. "
                          "Upland NERICA: well-drained but moisture-retentive. "
                          "Mangrove rice: acid-sulfate soil management required (desalinization bunds).",
        "amendments_needed": json.dumps([
            "Lime: 500 kg/ha if pH < 4.5 (acid sulfate soils in mangrove areas)",
            "Compost or green manure: incorporated before flooding improves flooded soil fertility",
            "Zinc sulphate: 25 kg/ha if zinc deficiency symptoms (interveinal chlorosis on young leaves)",
        ]),
        "preparation_notes": (
            "Lowland paddy: plough and puddle (wet tillage) to destroy weeds and seal soil pores. "
            "Puddling reduces water percolation, maintains flood. "
            "Upland: till to 20cm, no puddling. "
            "Mangrove: construct bunds and desalinize by rain leaching for 1-2 seasons before cultivation."
        ),
    },
    {
        "id": 3,
        "crop_id": 3,  # maize
        "ph_min": 5.5,
        "ph_max": 7.5,
        "preferred_texture": "Sandy loam to clay loam. Moderate texture optimal. "
                             "Avoids pure sand (nutrient leaching) and heavy clay (poor drainage).",
        "drainage_needs": "Well-drained. Waterlogging at seedling stage causes severe stunting. "
                          "Avoid low-lying areas and poorly-drained bas-fonds. "
                          "On flat terrain, plant on slight ridges.",
        "amendments_needed": json.dumps([
            "Lime: 1 t/ha if pH < 5.5 — maize very sensitive to aluminum toxicity below pH 5.0",
            "Compost: 3-5 t/ha on sandy soils, broadcast before ploughing",
            "Zinc: 10 kg ZnSO4/ha if deficiency history (whitish striping on young leaves)",
        ]),
        "preparation_notes": (
            "Primary tillage: plough or deep-hoe to 25-30cm before onset of rains. "
            "Secondary tillage: disc harrow or hand-hoe to break clods. "
            "Form planting rows N-S orientation for optimal sunlight. "
            "On slopes, contour ridges across slope to reduce erosion."
        ),
    },
    {
        "id": 4,
        "crop_id": 4,  # groundnut
        "ph_min": 5.5,
        "ph_max": 7.0,
        "preferred_texture": "Sandy loam to light loam. Sandy texture essential for pod penetration "
                             "into soil and for easy harvest without breaking pegs. "
                             "Clay soils cause pod rot and harvest losses.",
        "drainage_needs": "Good drainage essential. Pod rot increases significantly if soil stays "
                          "saturated more than 24h. Slightly raised beds improve pod recovery at harvest.",
        "amendments_needed": json.dumps([
            "Gypsum (calcium sulphate): 300 kg/ha applied at flowering for calcium in pod zone",
            "Lime: 500 kg/ha if pH < 5.5 — supports Rhizobium nodulation",
            "Compost: 2-3 t/ha maximum — avoid excessive N which suppresses nitrogen fixation",
            "Rhizobium inoculant: peat-based, coat seeds before planting if available",
        ]),
        "preparation_notes": (
            "Plough to 25cm to allow root and peg penetration. "
            "Do not over-compact — groundnut pegs must penetrate soil to form pods. "
            "Fine seedbed recommended: break all clods to <2cm. "
            "Do not apply fresh uncomposted manure — promotes aflatoxin-producing Aspergillus."
        ),
    },
    {
        "id": 5,
        "crop_id": 5,  # tomato
        "ph_min": 6.0,
        "ph_max": 6.8,
        "preferred_texture": "Sandy loam to loam. Good water-holding capacity with drainage. "
                             "Heavy clay causes blossom end rot and increases Ralstonia wilt pressure.",
        "drainage_needs": "Excellent drainage required. Raised beds (30cm) standard practice "
                          "in Casamance dry-season gardens. Root rot occurs within 24h of waterlogging.",
        "amendments_needed": json.dumps([
            "Lime (dolomite preferred): 1-2 t/ha if pH < 6.0",
            "Compost: 10 t/ha incorporated — essential for moisture retention in dry season",
            "Calcium: 300 kg gypsum/ha or 200 kg calcium nitrate/ha — prevents blossom end rot",
            "Soil solarization: cover with clear polythene 4 weeks before transplanting in fields "
            "with Ralstonia wilt history",
        ]),
        "preparation_notes": (
            "Form raised beds 1m wide, 30cm high, with 40cm irrigation furrows between beds. "
            "Bed formation allows good root aeration and drainage. "
            "In Ralstonia wilt-prone soils: solarize soil (clear polythene, 4 weeks full sun) "
            "to pasteurize top 20cm. This is most effective Ralstonia management strategy. "
            "Apply compost, lime, and phosphate during bed formation and incorporate to 20cm."
        ),
    },
]
