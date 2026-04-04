"""Seed data for the Casamance Agriculture Knowledge Pack.

Factually accurate agricultural data for the Casamance region of Senegal.
5 crops, 15 diseases, 30+ treatments, 12 months of climate data.

All data structured to match the SQLite schema in schema_sqlite.py.
JSON fields (common_names, materials_needed) are stored as JSON strings.
"""

import json

# ============================================================
# CROPS (5)
# ============================================================

CROPS = [
    {
        "id": 1,
        "name": "cassava",
        "scientific_name": "Manihot esculenta",
        "family": "Euphorbiaceae",
        "growing_season": "Year-round; main planting June-August with rains",
        "water_needs_mm_per_week": 25.0,
        "drought_tolerance": "high",
        "region_suitability": "Well-suited to Casamance tropical savanna; tolerates poor soils",
        "planting_notes": "Plant stem cuttings 20-25cm long at 45° angle. Spacing 1m x 1m. "
                          "Use certified disease-free cuttings from ISRA or local extension service.",
        "harvest_notes": "Harvest 8-18 months after planting depending on variety. "
                         "Leaves edible from 3 months. Tubers must be processed within 48h of harvest.",
    },
    {
        "id": 2,
        "name": "rice",
        "scientific_name": "Oryza sativa / Oryza glaberrima",
        "family": "Poaceae",
        "growing_season": "Wet season: June-November. Lowland and mangrove rice in Casamance.",
        "water_needs_mm_per_week": 50.0,
        "drought_tolerance": "low",
        "region_suitability": "Casamance is Senegal's main rice-growing region. "
                              "Lowland valleys and mangrove swamps ideal for paddy rice.",
        "planting_notes": "Nursery sowing in June, transplant at 3-4 weeks. "
                          "NERICA varieties (New Rice for Africa) recommended for upland areas. "
                          "Spacing 20x20cm for transplanted rice.",
        "harvest_notes": "Harvest when 80% of grains are golden. "
                         "Cut, bundle, and thresh within 24h. Sun-dry to 14% moisture.",
    },
    {
        "id": 3,
        "name": "maize",
        "scientific_name": "Zea mays",
        "family": "Poaceae",
        "growing_season": "Main season: June-September with rains. Short cycle varieties (90 days).",
        "water_needs_mm_per_week": 40.0,
        "drought_tolerance": "medium",
        "region_suitability": "Grows well in Casamance ferralitic soils. "
                              "Intercrop with cassava or groundnut common practice.",
        "planting_notes": "Direct sowing at first reliable rains (mid-June). "
                          "2 seeds per hole, spacing 75x25cm. "
                          "Apply compost or manure at planting. Thin to 1 plant per hole at 2 weeks.",
        "harvest_notes": "Harvest when husks are dry and kernels dent when pressed. "
                         "Dry on cob in well-ventilated storage. Shell after drying to 13% moisture.",
    },
    {
        "id": 4,
        "name": "groundnut",
        "scientific_name": "Arachis hypogaea",
        "family": "Fabaceae",
        "growing_season": "Wet season: June-October. 90-120 day cycle.",
        "water_needs_mm_per_week": 30.0,
        "drought_tolerance": "medium",
        "region_suitability": "Major cash crop in Casamance. Sandy-loam soils preferred. "
                              "Fixes nitrogen — excellent rotation crop with cereals.",
        "planting_notes": "Sow shelled seeds 5cm deep after first rains. "
                          "Spacing 40x15cm. Inoculate with Rhizobium if available. "
                          "Do not use seeds from previous rosette-infected plants.",
        "harvest_notes": "Harvest when leaves yellow and inner shell darkens. "
                         "Lift with hoe, dry inverted in field for 3-5 days. "
                         "Store in jute sacks in dry, ventilated area. Monitor for aflatoxin.",
    },
    {
        "id": 5,
        "name": "tomato",
        "scientific_name": "Solanum lycopersicum",
        "family": "Solanaceae",
        "growing_season": "Dry season: November-May (irrigated). Some wet season production.",
        "water_needs_mm_per_week": 35.0,
        "drought_tolerance": "low",
        "region_suitability": "Grown in Casamance gardens and peri-urban areas. "
                              "Requires irrigation in dry season. High market value.",
        "planting_notes": "Start in nursery, transplant at 4-5 weeks (15-20cm tall). "
                          "Spacing 60x40cm. Stake or cage for support. "
                          "Mulch to conserve moisture and reduce soil splash.",
        "harvest_notes": "Harvest at breaker stage (first color change) for market. "
                         "Handle carefully to avoid bruising. Highly perishable — "
                         "sell or process within 3-5 days.",
    },
]

# ============================================================
# DISEASES (15)
# ============================================================

DISEASES = [
    # --- Cassava (4 diseases) ---
    {
        "id": 1,
        "name": "Cassava Mosaic Disease",
        "common_names": json.dumps(["CMD", "mosaïque du manioc", "cassava mosaic"]),
        "type": "viral",
        "symptoms_text": (
            "Yellow-green mosaic patterns on leaves, especially young leaves. "
            "Leaf curling, distortion, and reduced leaf size. Stunted plant growth. "
            "Severe infections cause small, deformed tubers and up to 50-70% yield loss. "
            "Symptoms most visible during vigorous growth."
        ),
        "visual_markers": (
            "Irregular yellow and green patches on leaf surface forming mosaic pattern. "
            "Leaves may curl downward or become misshapen. Leaf size noticeably smaller "
            "than healthy plants. Young leaves at shoot tips most affected. "
            "Entire plant may appear stunted compared to healthy neighbors."
        ),
        "severity_scale": "high",
        "spread_mechanism": "Whitefly (Bemisia tabaci) transmission. Infected stem cuttings.",
        "prevention_notes": (
            "Plant CMD-resistant varieties (TME 419, IITA-TMS-IBA30572). "
            "Use certified disease-free cuttings. Remove and burn infected plants early. "
            "Control whitefly with neem oil spray. Intercrop with maize to reduce whitefly density."
        ),
    },
    {
        "id": 2,
        "name": "Cassava Brown Streak Disease",
        "common_names": json.dumps(["CBSD", "brown streak", "stries brunes du manioc"]),
        "type": "viral",
        "symptoms_text": (
            "Yellow or necrotic vein banding on mature leaves. Brown, dry, corky rot "
            "inside tubers — often not visible until harvest. Stem lesions appear as "
            "brown-purple streaks. Tuber necrosis makes roots unmarketable. "
            "Yield losses up to 70% in severe cases."
        ),
        "visual_markers": (
            "Yellow patches along leaf veins, creating feather-like pattern on mature leaves. "
            "Brown-purple streaks running along stems. When tubers are cut open, brown corky "
            "patches visible in the white flesh. Tuber skin may crack. "
            "Symptoms often subtle on leaves — tuber damage only found at harvest."
        ),
        "severity_scale": "critical",
        "spread_mechanism": "Whitefly (Bemisia tabaci). Infected cuttings. Cannot spread through soil.",
        "prevention_notes": (
            "Plant CBSD-tolerant varieties. Source cuttings from disease-free mother plants. "
            "Inspect tubers at harvest — do not replant from infected stock. "
            "Rogue infected plants immediately. Control whitefly populations."
        ),
    },
    {
        "id": 3,
        "name": "Cassava Bacterial Blight",
        "common_names": json.dumps(["CBB", "brûlure bactérienne du manioc"]),
        "type": "bacterial",
        "symptoms_text": (
            "Angular, water-soaked leaf spots that turn brown. Wilting of shoot tips. "
            "Gum exudate on stems (white or amber beads). Dieback of branches from tips. "
            "In severe cases, complete defoliation. Yield loss 20-80% depending on severity."
        ),
        "visual_markers": (
            "Angular brown spots on leaves, often with yellow halo. Spots may merge causing "
            "large brown dead areas. White or amber gummy droplets on stems, especially "
            "near nodes. Shoot tips wilt and droop. Stem cross-section shows brown "
            "discoloration of vascular tissue."
        ),
        "severity_scale": "high",
        "spread_mechanism": "Rain splash. Contaminated tools. Infected stem cuttings. Wounds.",
        "prevention_notes": (
            "Use disease-free planting material. Disinfect cutting tools with bleach between plants. "
            "Avoid working in fields when wet. Rotate cassava with non-host crops for 1-2 seasons. "
            "Apply copper-based bactericide preventatively during rainy season."
        ),
    },
    {
        "id": 4,
        "name": "Cassava Anthracnose",
        "common_names": json.dumps(["anthracnose du manioc", "cassava dieback"]),
        "type": "fungal",
        "symptoms_text": (
            "Cankers on stems — sunken, dark lesions that girdle branches. "
            "Dieback of shoot tips and young branches. Leaf spots with dark margins. "
            "In humid conditions, pink spore masses visible on cankers. "
            "Can kill young plants; older plants lose branches but survive."
        ),
        "visual_markers": (
            "Dark sunken oval cankers on stems, often at nodes or wound sites. "
            "Dead shoot tips with dry, shriveled leaves still attached. "
            "Small dark spots on leaves with concentric rings. "
            "Pink-orange spore masses on canker surfaces during wet weather."
        ),
        "severity_scale": "medium",
        "spread_mechanism": "Rain splash. Infected cuttings. Favored by high humidity and wounds.",
        "prevention_notes": (
            "Use healthy planting material. Prune and burn affected branches. "
            "Avoid planting in poorly drained areas. Space plants for air circulation. "
            "Apply copper fungicide during early rainy season."
        ),
    },
    # --- Rice (3 diseases) ---
    {
        "id": 5,
        "name": "Rice Blast",
        "common_names": json.dumps(["blast du riz", "pyriculariose", "rice blast fungus"]),
        "type": "fungal",
        "symptoms_text": (
            "Diamond-shaped or elliptical spots on leaves with gray-white centers "
            "and dark brown borders. Neck rot at panicle base causing white heads "
            "(empty grains). Node blast causes dark lesions on stem nodes. "
            "Can destroy entire crop if neck blast occurs."
        ),
        "visual_markers": (
            "Eye-shaped or diamond leaf spots 1-2cm long with pointed ends. "
            "Centers gray to white, borders dark brown to reddish. Spots enlarge and "
            "merge in humid conditions. Panicle neck turns brown-black and bends — "
            "grains above the infection are white and empty. Nodes show dark brown bands."
        ),
        "severity_scale": "critical",
        "spread_mechanism": "Airborne spores. Favored by high nitrogen, dense planting, humid weather.",
        "prevention_notes": (
            "Use blast-resistant varieties (NERICA 1, NERICA 4, SAHEL 108). "
            "Avoid excessive nitrogen fertilizer. Ensure good spacing for air circulation. "
            "Burn rice straw after harvest. Apply tricyclazole or copper fungicide at booting stage."
        ),
    },
    {
        "id": 6,
        "name": "Bacterial Leaf Blight of Rice",
        "common_names": json.dumps(["BLB", "flétrissement bactérien du riz"]),
        "type": "bacterial",
        "symptoms_text": (
            "Water-soaked lesions starting from leaf tips or margins, expanding downward. "
            "Lesions turn yellow then grayish-white as they dry. Entire leaves may wilt "
            "and die in severe cases. Milky bacterial ooze visible on cut lesions in morning."
        ),
        "visual_markers": (
            "Long yellowish-white streaks along leaf edges starting from the tip. "
            "Lesions have wavy margins. Leaves turn straw-colored as infection progresses. "
            "In early morning, tiny milky-white droplets of bacterial ooze visible "
            "on cut leaf surfaces. Severely infected fields appear scorched."
        ),
        "severity_scale": "high",
        "spread_mechanism": "Wind-driven rain. Floodwater. Infected seeds. Wounds from storms.",
        "prevention_notes": (
            "Plant resistant varieties. Use balanced fertilization — avoid excess nitrogen. "
            "Drain fields periodically. Avoid field-to-field water flow. "
            "Do not work in fields when wet. Remove crop residues after harvest."
        ),
    },
    {
        "id": 7,
        "name": "Rice Yellow Mottle Virus",
        "common_names": json.dumps(["RYMV", "virus de la panachure jaune du riz"]),
        "type": "viral",
        "symptoms_text": (
            "Yellow to orange discoloration of leaves starting from center and spreading outward. "
            "Mottling pattern with alternating green and yellow streaks. Stunted growth. "
            "Reduced tillering. Panicles partially or fully empty. "
            "Yield loss 25-100% depending on timing of infection."
        ),
        "visual_markers": (
            "Bright yellow-orange mottling on leaves, especially mid-section. "
            "Leaves may show parallel yellow and green streaks along veins. "
            "Plants visibly shorter than healthy neighbors. Fewer tillers. "
            "Panicles small with many unfilled, whitish grains."
        ),
        "severity_scale": "high",
        "spread_mechanism": "Chrysomelid beetles (Chaetocnema pulla). Contact between plants. Contaminated tools.",
        "prevention_notes": (
            "Plant RYMV-resistant varieties (WITA 4, Gigante). "
            "Control beetle vectors with neem-based insecticide. "
            "Avoid transplanting seedlings from infected nurseries. "
            "Remove wild rice grasses near fields (reservoir hosts)."
        ),
    },
    # --- Maize (3 diseases) ---
    {
        "id": 8,
        "name": "Maize Streak Virus",
        "common_names": json.dumps(["MSV", "striure du maïs"]),
        "type": "viral",
        "symptoms_text": (
            "Narrow chlorotic (yellow) streaks along leaf veins. Streaks are broken, "
            "not continuous — give a dashed-line appearance. Severe infection causes "
            "yellowing of entire leaf. Stunted growth and poor cob formation. "
            "Young plants most susceptible — infection before 3 weeks is devastating."
        ),
        "visual_markers": (
            "Fine, broken yellow streaks running parallel to leaf veins. "
            "Streaks typically 1-3mm wide and 1-10cm long. Pattern is distinctly "
            "linear along the veins, not blotchy. Leaves may become entirely yellow "
            "in severe cases. Plants shorter than healthy neighbors with thin stalks."
        ),
        "severity_scale": "high",
        "spread_mechanism": "Leafhopper (Cicadulina mbila). Not seed-transmitted.",
        "prevention_notes": (
            "Plant MSV-tolerant varieties. Early planting at onset of rains reduces "
            "leafhopper pressure. Remove volunteer maize and grass weeds near fields. "
            "Intercrop with non-host crops. Apply imidacloprid seed treatment if available."
        ),
    },
    {
        "id": 9,
        "name": "Northern Corn Leaf Blight",
        "common_names": json.dumps(["NCLB", "helminthosporiose du maïs", "turcicum leaf blight"]),
        "type": "fungal",
        "symptoms_text": (
            "Long, elliptical, grayish-green to tan lesions on leaves (5-15cm). "
            "Lesions start on lower leaves and progress upward. In humid conditions, "
            "dark gray-green spore masses visible on lesion surface. "
            "Severe infection causes premature leaf death reducing grain fill."
        ),
        "visual_markers": (
            "Cigar-shaped gray-tan leaf spots 5-15cm long and 1-3cm wide. "
            "Spots appear watersoaked at first, then dry to tan with dark borders. "
            "Often start on lower leaves. In morning dew, lesion surface shows "
            "dark olive-gray fuzzy spore growth. Multiple spots can merge, killing entire leaves."
        ),
        "severity_scale": "medium",
        "spread_mechanism": "Airborne spores. Survives on crop debris. Favored by cool nights and heavy dew.",
        "prevention_notes": (
            "Plant resistant hybrids. Rotate with non-cereals for at least 1 year. "
            "Bury or burn crop residues. Avoid late planting when disease pressure peaks. "
            "Apply mancozeb or copper fungicide if lesions appear before tasseling."
        ),
    },
    {
        "id": 10,
        "name": "Maize Smut",
        "common_names": json.dumps(["charbon du maïs", "common smut", "corn smut"]),
        "type": "fungal",
        "symptoms_text": (
            "Large, tumor-like galls on ears, tassels, stalks, and leaves. "
            "Galls start as small white swellings, enlarge and fill with black "
            "powdery spores. Galls on ears replace kernels. Individual galls can "
            "reach 15cm diameter. More common after hail or mechanical damage."
        ),
        "visual_markers": (
            "Unmistakable large whitish-gray swollen galls (tumors) on any above-ground "
            "plant part. Galls have a shiny membrane that eventually ruptures, releasing "
            "masses of dark brown-black powdery spores. Most dramatic on ears where "
            "galls replace normal kernels. Galls on tassels distort the flower structure."
        ),
        "severity_scale": "low",
        "spread_mechanism": "Soilborne and airborne spores. Enters through wounds. Favored by drought stress.",
        "prevention_notes": (
            "Avoid mechanical damage to plants. Manage drought stress with mulching. "
            "Remove and bury galls before they rupture and release spores. "
            "Rotate crops. No chemical control is practical."
        ),
    },
    # --- Groundnut (3 diseases) ---
    {
        "id": 11,
        "name": "Groundnut Rosette Disease",
        "common_names": json.dumps(["rosette de l'arachide", "groundnut rosette"]),
        "type": "viral",
        "symptoms_text": (
            "Severe stunting of plants. Leaves become small, curled, and form a rosette "
            "(bunched cluster) at the top. Chlorotic (yellow) or green mosaic patterns. "
            "Two forms: chlorotic rosette (yellow leaves) and green rosette (dark green, "
            "curled leaves). Plants produce no or very few pods."
        ),
        "visual_markers": (
            "Dramatically stunted plants — often less than half the height of healthy neighbors. "
            "Leaves are small, bunched together in tight clusters at branch tips. "
            "Chlorotic form: leaves bright yellow-green with mosaic. "
            "Green form: leaves dark green, severely curled and distorted. "
            "No pods or very small pods at harvest."
        ),
        "severity_scale": "critical",
        "spread_mechanism": "Aphid (Aphis craccivora) transmission. Requires co-infection by 3 viral agents.",
        "prevention_notes": (
            "Plant rosette-resistant varieties (ICG 12991, ICGV-IS 96894). "
            "Early planting at recommended density reduces aphid colonization. "
            "Do not plant late — late-planted groundnut has highest rosette risk. "
            "Remove infected plants immediately. Apply neem oil for aphid control."
        ),
    },
    {
        "id": 12,
        "name": "Early Leaf Spot of Groundnut",
        "common_names": json.dumps(["cercosporiose précoce", "early leaf spot", "Cercospora arachidicola"]),
        "type": "fungal",
        "symptoms_text": (
            "Dark brown circular spots on upper leaf surface, 1-10mm diameter. "
            "Spots have a lighter brown center with dark brown margin. "
            "Yellow halo around spots. Spots on lower leaf surface are lighter. "
            "Severe infection causes premature defoliation and 50% yield loss."
        ),
        "visual_markers": (
            "Round to irregular dark brown spots on the upper side of leaves. "
            "Each spot has a visible lighter center and dark ring border. "
            "Spots surrounded by a yellow halo. On the underside of the leaf, "
            "spots appear lighter brown. Spots appear first on lower, older leaves. "
            "Heavy infection — leaves turn yellow, dry up, and fall off."
        ),
        "severity_scale": "medium",
        "spread_mechanism": "Airborne spores. Rain splash. Survives on crop debris. Favored by warm humid weather.",
        "prevention_notes": (
            "Rotate groundnut with cereals (2-3 year rotation). "
            "Bury crop residues after harvest. Space plants adequately. "
            "Apply mancozeb or chlorothalonil at first sign of spots. "
            "Use tolerant varieties where available."
        ),
    },
    {
        "id": 13,
        "name": "Late Leaf Spot of Groundnut",
        "common_names": json.dumps(["cercosporiose tardive", "late leaf spot", "Phaeoisariopsis personata"]),
        "type": "fungal",
        "symptoms_text": (
            "Dark brown to black circular spots, smaller than early leaf spot (1-6mm). "
            "Spots rough-textured on lower leaf surface where spores form. "
            "No or minimal yellow halo — distinguishes from early leaf spot. "
            "Appears later in the season. Causes severe defoliation and yield loss 20-60%."
        ),
        "visual_markers": (
            "Small, nearly black circular spots more visible on the lower leaf surface. "
            "Spots appear rough or velvety underneath due to spore production. "
            "Upper surface spots are smoother and dark brown. Little or no yellow halo. "
            "Appears 4-6 weeks after early leaf spot. Combined with early leaf spot, "
            "can cause complete defoliation."
        ),
        "severity_scale": "medium",
        "spread_mechanism": "Airborne spores. Crop debris. Often occurs together with early leaf spot.",
        "prevention_notes": (
            "Same management as early leaf spot. Rotate crops. Bury residues. "
            "Fungicide application most critical at 45-60 days after planting. "
            "Combined management of both leaf spots gives best results."
        ),
    },
    # --- Tomato (2 diseases) ---
    {
        "id": 14,
        "name": "Tomato Yellow Leaf Curl Virus",
        "common_names": json.dumps(["TYLCV", "enroulement jaune", "tomato leaf curl"]),
        "type": "viral",
        "symptoms_text": (
            "Severe upward curling and cupping of leaves. Leaves become small and yellowed, "
            "especially along margins. Stunted growth with shortened internodes giving "
            "bushy appearance. Flowers drop without setting fruit. "
            "Plants infected early produce no marketable fruit."
        ),
        "visual_markers": (
            "Leaves curl upward and inward, forming cup shapes. "
            "Leaf margins turn yellow while centers remain green. "
            "Plants are severely stunted — bushy, compact growth. "
            "Flowers may be present but fall without forming fruit. "
            "New growth is small, thick, and rubbery-textured."
        ),
        "severity_scale": "critical",
        "spread_mechanism": "Whitefly (Bemisia tabaci). Not mechanically transmitted or seed-borne.",
        "prevention_notes": (
            "Plant TYLCV-resistant varieties. Use whitefly-proof netting in nurseries. "
            "Apply neem oil or reflective silver mulch to repel whiteflies. "
            "Remove and destroy infected plants immediately. "
            "Avoid planting near old tomato or pepper fields with whitefly populations."
        ),
    },
    {
        "id": 15,
        "name": "Bacterial Wilt of Tomato",
        "common_names": json.dumps(["flétrissement bactérien", "Ralstonia wilt", "tomato wilt"]),
        "type": "bacterial",
        "symptoms_text": (
            "Rapid wilting of entire plant without yellowing first. "
            "Lower leaves may wilt first but entire plant collapses within days. "
            "Stem cross-section shows brown discoloration of vascular tissue. "
            "When cut stem is placed in water, milky bacterial ooze streams out. "
            "Plants die quickly — no recovery possible once wilting starts."
        ),
        "visual_markers": (
            "Plant wilts suddenly even when soil is moist. "
            "Leaves remain green while wilting — not yellowed. "
            "Cut the stem near the base — inside is brown instead of white/green. "
            "Place cut stem end in a glass of clear water — within minutes, "
            "milky white threads stream down from the cut (bacterial ooze test). "
            "Roots may appear healthy externally."
        ),
        "severity_scale": "critical",
        "spread_mechanism": "Soilborne bacterium (Ralstonia solanacearum). Enters through roots/wounds. "
                            "Spread by contaminated tools, irrigation water, and infested soil.",
        "prevention_notes": (
            "No cure once infected — prevention is everything. "
            "Rotate with non-solanaceous crops for 3+ years. "
            "Use raised beds for drainage. Solarize soil before planting. "
            "Disinfect tools. Graft onto resistant rootstock (Hawaii 7996). "
            "Add lime to raise soil pH above 6.5."
        ),
    },
]

# ============================================================
# CROP-DISEASE relationships (many-to-many)
# ============================================================

CROP_DISEASES = [
    # Cassava diseases
    {"crop_id": 1, "disease_id": 1, "susceptibility": "high"},    # CMD
    {"crop_id": 1, "disease_id": 2, "susceptibility": "high"},    # CBSD
    {"crop_id": 1, "disease_id": 3, "susceptibility": "medium"},  # CBB
    {"crop_id": 1, "disease_id": 4, "susceptibility": "medium"},  # Anthracnose
    # Rice diseases
    {"crop_id": 2, "disease_id": 5, "susceptibility": "high"},    # Blast
    {"crop_id": 2, "disease_id": 6, "susceptibility": "high"},    # BLB
    {"crop_id": 2, "disease_id": 7, "susceptibility": "high"},    # RYMV
    # Maize diseases
    {"crop_id": 3, "disease_id": 8, "susceptibility": "high"},    # MSV
    {"crop_id": 3, "disease_id": 9, "susceptibility": "medium"},  # NCLB
    {"crop_id": 3, "disease_id": 10, "susceptibility": "low"},    # Smut
    # Groundnut diseases
    {"crop_id": 4, "disease_id": 11, "susceptibility": "high"},   # Rosette
    {"crop_id": 4, "disease_id": 12, "susceptibility": "high"},   # Early leaf spot
    {"crop_id": 4, "disease_id": 13, "susceptibility": "high"},   # Late leaf spot
    # Tomato diseases
    {"crop_id": 5, "disease_id": 14, "susceptibility": "high"},   # TYLCV
    {"crop_id": 5, "disease_id": 15, "susceptibility": "high"},   # Bacterial wilt
]

# ============================================================
# TREATMENTS (2+ per disease = 32 total)
# ============================================================

TREATMENTS = [
    # --- CMD treatments ---
    {
        "id": 1, "disease_id": 1, "method": "Resistant variety replacement",
        "description": "Remove infected plants and replant with CMD-resistant varieties TME 419 or IITA-TMS-IBA30572. Source clean cuttings from ISRA Ziguinchor or local agricultural extension office.",
        "materials_needed": json.dumps(["CMD-resistant stem cuttings", "hoe for removal"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Resistant cuttings available through ISRA and NGO distribution programs in Casamance",
        "effectiveness": "high", "application_timing": "Replace at next planting season",
        "safety_notes": "Burn removed infected plants — do not compost.",
    },
    {
        "id": 2, "disease_id": 1, "method": "Neem oil whitefly control",
        "description": "Prepare neem oil spray to control whitefly vectors. Collect 500g neem seeds, crush and soak in 10L water overnight. Strain through cloth. Add a few drops of liquid soap as surfactant. Spray on leaf undersides every 7-10 days.",
        "materials_needed": json.dumps(["neem seeds (500g)", "water (10L)", "cloth for straining", "liquid soap", "sprayer"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Neem trees (Azadirachta indica) abundant throughout Casamance",
        "effectiveness": "medium", "application_timing": "Every 7-10 days during growing season. Start when whiteflies first appear.",
        "safety_notes": "Spray in early morning or late evening to avoid leaf burn. Safe for humans and animals.",
    },
    # --- CBSD treatments ---
    {
        "id": 3, "disease_id": 2, "method": "Roguing and clean seed system",
        "description": "Remove and destroy all plants showing CBSD leaf symptoms. At harvest, inspect every tuber — do not save cuttings from plants with necrotic tubers. Establish a clean seed plot with inspected mother plants.",
        "materials_needed": json.dumps(["marking stakes", "machete", "fire materials for burning"]),
        "difficulty": "medium", "is_organic": True,
        "local_availability": "All materials locally available",
        "effectiveness": "high", "application_timing": "Inspect monthly. Remove symptomatic plants immediately.",
        "safety_notes": "Burn removed plants at field edge. Wash hands after handling infected material.",
    },
    {
        "id": 4, "disease_id": 2, "method": "Whitefly management with intercropping",
        "description": "Intercrop cassava with maize, sorghum, or legumes. The taller companion crops physically block whitefly movement and create shade that whiteflies avoid. Plant companion crop 2-3 weeks before cassava.",
        "materials_needed": json.dumps(["maize or sorghum seed", "legume seed (cowpea or groundnut)"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Companion crop seeds widely available in local markets",
        "effectiveness": "medium", "application_timing": "At planting time. Plan field layout before season.",
        "safety_notes": "None. Companion crops also provide food and income.",
    },
    # --- CBB treatments ---
    {
        "id": 5, "disease_id": 3, "method": "Copper-based bactericide spray",
        "description": "Apply copper hydroxide (Kocide) or Bordeaux mixture (1% copper sulfate + lime) as preventative spray. Apply before rainy season onset and repeat every 14 days during wet weather.",
        "materials_needed": json.dumps(["copper sulfate (100g)", "quicklime (100g)", "water (10L)", "sprayer"]),
        "difficulty": "medium", "is_organic": False,
        "local_availability": "Copper sulfate available at agricultural supply shops in Ziguinchor",
        "effectiveness": "medium", "application_timing": "Preventative: apply before rains. Repeat every 14 days in wet season.",
        "safety_notes": "Wear gloves when mixing. Avoid spraying near water sources. Do not exceed recommended concentration.",
    },
    {
        "id": 6, "disease_id": 3, "method": "Sanitation and tool hygiene",
        "description": "Disinfect all cutting tools with 10% bleach solution between plants. Remove and burn infected branches. Avoid working in cassava fields when foliage is wet. Practice crop rotation with non-cassava crops for 2 seasons.",
        "materials_needed": json.dumps(["bleach (Javel)", "water", "container for disinfectant", "machete"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Bleach widely available at any market",
        "effectiveness": "medium", "application_timing": "Ongoing — every time tools are used in the field.",
        "safety_notes": "Dilute bleach properly. Rinse tools after disinfection to prevent corrosion.",
    },
    # --- Anthracnose treatments ---
    {
        "id": 7, "disease_id": 4, "method": "Pruning and copper fungicide",
        "description": "Prune infected branches 20cm below visible cankers. Apply copper fungicide to cut surfaces. Remove prunings from field and burn. Improve air circulation by widening plant spacing.",
        "materials_needed": json.dumps(["pruning saw or machete", "copper fungicide paste", "fire materials"]),
        "difficulty": "easy", "is_organic": False,
        "local_availability": "Copper paste from agricultural supply shops",
        "effectiveness": "medium", "application_timing": "Prune during dry weather. Apply copper immediately to cuts.",
        "safety_notes": "Sterilize pruning tools between plants with bleach.",
    },
    {
        "id": 8, "disease_id": 4, "method": "Wood ash treatment",
        "description": "Apply wood ash paste to canker wounds after pruning. Mix wood ash with small amount of water to form paste. Pack into wound. Ash is alkaline and inhibits fungal growth.",
        "materials_needed": json.dumps(["wood ash", "water", "container for mixing"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Wood ash freely available from cooking fires",
        "effectiveness": "low", "application_timing": "Apply immediately after pruning infected branches.",
        "safety_notes": "Avoid contact with eyes. Wash hands after application.",
    },
    # --- Rice Blast treatments ---
    {
        "id": 9, "disease_id": 5, "method": "Resistant varieties and nitrogen management",
        "description": "Replace susceptible varieties with blast-resistant NERICA 1, NERICA 4, or SAHEL 108. Reduce nitrogen fertilizer by 30% — high nitrogen increases blast susceptibility. Apply nitrogen in split doses rather than all at once.",
        "materials_needed": json.dumps(["blast-resistant rice seed", "reduced nitrogen fertilizer"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "NERICA seeds available through AfricaRice, ISRA, and NGO seed programs",
        "effectiveness": "high", "application_timing": "Implement at planting. Adjust fertilizer plan for the season.",
        "safety_notes": "None.",
    },
    {
        "id": 10, "disease_id": 5, "method": "Copper fungicide at booting stage",
        "description": "Apply copper oxychloride spray when rice reaches booting stage (panicle forming inside flag leaf). This prevents neck blast which is the most destructive phase. Repeat once more at heading.",
        "materials_needed": json.dumps(["copper oxychloride", "water", "knapsack sprayer"]),
        "difficulty": "medium", "is_organic": False,
        "local_availability": "Available at agricultural input shops in Ziguinchor and Kolda",
        "effectiveness": "medium", "application_timing": "At booting and heading stages — timing is critical.",
        "safety_notes": "Wear protective clothing. Follow label rates. Observe pre-harvest interval.",
    },
    # --- BLB treatments ---
    {
        "id": 11, "disease_id": 6, "method": "Field drainage and balanced nutrition",
        "description": "Ensure proper field drainage — BLB thrives in waterlogged conditions. Reduce nitrogen and increase potassium in fertilizer mix. Drain fields for 3-5 days at tillering stage.",
        "materials_needed": json.dumps(["drainage channels", "potassium fertilizer (KCl or wood ash)"]),
        "difficulty": "medium", "is_organic": True,
        "local_availability": "Wood ash as potassium source is freely available",
        "effectiveness": "medium", "application_timing": "Manage water throughout the growing season.",
        "safety_notes": "None.",
    },
    {
        "id": 12, "disease_id": 6, "method": "Copper bactericide application",
        "description": "Apply copper hydroxide spray at first sign of lesions. Most effective as preventive before symptoms spread. Apply every 10-14 days during wet weather.",
        "materials_needed": json.dumps(["copper hydroxide", "water", "sprayer"]),
        "difficulty": "medium", "is_organic": False,
        "local_availability": "Available at agricultural supply shops",
        "effectiveness": "low", "application_timing": "At first symptoms or preventatively in known problem fields.",
        "safety_notes": "Limited effectiveness once infection is established. Prevention is key.",
    },
    # --- RYMV treatments ---
    {
        "id": 13, "disease_id": 7, "method": "Resistant varieties and vector control",
        "description": "Plant RYMV-resistant varieties WITA 4 or Gigante. Control Chrysomelid beetle vectors with neem seed extract spray. Remove infected plants to prevent field spread.",
        "materials_needed": json.dumps(["resistant rice seed", "neem seeds for spray"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "WITA 4 seed available through AfricaRice and ISRA programs",
        "effectiveness": "high", "application_timing": "At planting (variety choice) and throughout season (vector control).",
        "safety_notes": "None.",
    },
    {
        "id": 14, "disease_id": 7, "method": "Wild grass host removal",
        "description": "Remove wild rice species and grasses (Oryza barthii, Oryza longistaminata) within 50m of rice fields. These serve as virus reservoirs between seasons. Cut and burn or bury deeply.",
        "materials_needed": json.dumps(["machete", "hoe"]),
        "difficulty": "hard", "is_organic": True,
        "local_availability": "Labor-intensive but no external inputs needed",
        "effectiveness": "medium", "application_timing": "Before planting season. Maintain throughout.",
        "safety_notes": "Be aware of beneficial wild species — only remove known reservoir hosts.",
    },
    # --- MSV treatments ---
    {
        "id": 15, "disease_id": 8, "method": "Early planting and tolerant varieties",
        "description": "Plant maize at the very start of the rainy season (mid-June in Casamance). Leafhopper populations build up later — early-planted maize escapes peak vector pressure. Use MSV-tolerant varieties.",
        "materials_needed": json.dumps(["MSV-tolerant maize seed", "land preparation tools"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Improved maize varieties available through ISRA and seed dealers",
        "effectiveness": "high", "application_timing": "Plant within first 2 weeks of reliable rains.",
        "safety_notes": "None.",
    },
    {
        "id": 16, "disease_id": 8, "method": "Neem-based leafhopper control",
        "description": "Spray neem seed extract on young maize plants (first 4 weeks) to repel leafhoppers. Prepare as for whitefly control. Focus on young seedlings which are most vulnerable.",
        "materials_needed": json.dumps(["neem seeds", "water", "sprayer", "soap"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Neem trees abundant in Casamance",
        "effectiveness": "medium", "application_timing": "Weekly from emergence to 4 weeks. Most critical period.",
        "safety_notes": "Safe for humans and livestock.",
    },
    # --- NCLB treatments ---
    {
        "id": 17, "disease_id": 9, "method": "Crop rotation and residue management",
        "description": "Rotate maize with groundnut, cowpea, or cassava for at least 1 year. After harvest, collect and burn or deeply bury maize stalks and leaves — the fungus survives on crop debris.",
        "materials_needed": json.dumps(["alternative crop seeds", "hoe for residue burial"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "No external inputs needed",
        "effectiveness": "medium", "application_timing": "Plan rotation before planting season. Manage residues after harvest.",
        "safety_notes": "None.",
    },
    {
        "id": 18, "disease_id": 9, "method": "Mancozeb fungicide spray",
        "description": "Apply mancozeb (Dithane M-45) at first sign of lesions. Spray every 10-14 days if conditions remain humid. Most important to protect leaves above the ear for grain fill.",
        "materials_needed": json.dumps(["mancozeb (Dithane M-45)", "water", "knapsack sprayer"]),
        "difficulty": "medium", "is_organic": False,
        "local_availability": "Available at agricultural input dealers in Ziguinchor",
        "effectiveness": "medium", "application_timing": "At first sign of lesions. Repeat every 10-14 days.",
        "safety_notes": "Wear gloves and mask during application. 14-day pre-harvest interval.",
    },
    # --- Maize Smut treatments ---
    {
        "id": 19, "disease_id": 10, "method": "Gall removal and field sanitation",
        "description": "Remove galls by hand before they mature and burst open (while still firm and whitish). Place in bag and burn or bury deeply. Reducing spore spread is the main management strategy.",
        "materials_needed": json.dumps(["bags for collection", "gloves"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "No external inputs needed",
        "effectiveness": "medium", "application_timing": "Check fields weekly. Remove galls while still white/firm.",
        "safety_notes": "Wear gloves. Handle gently to avoid bursting. Note: young galls are edible in some cultures (huitlacoche).",
    },
    {
        "id": 20, "disease_id": 10, "method": "Wound prevention and stress reduction",
        "description": "Minimize plant wounds by careful weeding. Apply mulch to maintain soil moisture and reduce drought stress which predisposes plants to smut. Avoid cultivation damage to roots.",
        "materials_needed": json.dumps(["mulch material (straw, grass)", "careful hand weeding tools"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Mulch materials freely available",
        "effectiveness": "low", "application_timing": "Throughout growing season. Mulch at planting.",
        "safety_notes": "None.",
    },
    # --- Groundnut Rosette treatments ---
    {
        "id": 21, "disease_id": 11, "method": "Resistant varieties and early planting",
        "description": "Plant rosette-resistant varieties ICG 12991 or ICGV-IS 96894. Plant early at recommended density (40x15cm). Late planting dramatically increases rosette risk. Dense stands reduce aphid colonization.",
        "materials_needed": json.dumps(["rosette-resistant groundnut seed"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Resistant varieties available through ICRISAT and ISRA distribution programs",
        "effectiveness": "high", "application_timing": "At planting — variety and timing decisions before season.",
        "safety_notes": "None.",
    },
    {
        "id": 22, "disease_id": 11, "method": "Neem-based aphid control",
        "description": "Spray neem seed kernel extract to control aphid vectors. Prepare concentrated extract: 50g crushed neem kernels per liter of water, soaked overnight, strained. Spray weekly on leaf undersides.",
        "materials_needed": json.dumps(["neem seed kernels (50g/L)", "water", "cloth strainer", "sprayer"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Neem kernels abundant in Casamance",
        "effectiveness": "medium", "application_timing": "Start 2 weeks after emergence. Weekly applications.",
        "safety_notes": "Spray in morning or evening. Avoid contact with eyes.",
    },
    # --- Early Leaf Spot treatments ---
    {
        "id": 23, "disease_id": 12, "method": "Crop rotation and residue burial",
        "description": "Rotate groundnut with cereals (millet, sorghum, maize) for 2-3 years. Bury groundnut residues by plowing after harvest. This removes the main source of initial spore infection.",
        "materials_needed": json.dumps(["rotation crop seeds", "plow or hoe for residue burial"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "No external inputs needed",
        "effectiveness": "medium", "application_timing": "Plan rotation before season. Bury residues immediately after harvest.",
        "safety_notes": "None.",
    },
    {
        "id": 24, "disease_id": 12, "method": "Groundnut leaf spot fungicide",
        "description": "Apply mancozeb or chlorothalonil at 45 days after planting and repeat at 60 and 75 days. Three sprays cover the critical infection period. Most cost-effective disease management for groundnut.",
        "materials_needed": json.dumps(["mancozeb or chlorothalonil", "water", "sprayer"]),
        "difficulty": "medium", "is_organic": False,
        "local_availability": "Available at agricultural input shops",
        "effectiveness": "high", "application_timing": "45, 60, and 75 days after planting — 3 spray schedule.",
        "safety_notes": "Follow label instructions. Wear protective equipment.",
    },
    # --- Late Leaf Spot treatments ---
    {
        "id": 25, "disease_id": 13, "method": "Combined leaf spot management",
        "description": "Manage both early and late leaf spot together — the fungicide schedule at 45-60-75 days covers both. Add one extra spray at 90 days if late leaf spot pressure is high and harvest is still 3+ weeks away.",
        "materials_needed": json.dumps(["mancozeb", "water", "sprayer"]),
        "difficulty": "medium", "is_organic": False,
        "local_availability": "Same as early leaf spot treatment",
        "effectiveness": "high", "application_timing": "45, 60, 75, and optionally 90 days after planting.",
        "safety_notes": "Same as early leaf spot. Do not exceed 4 applications per season.",
    },
    {
        "id": 26, "disease_id": 13, "method": "Wood ash foliar application",
        "description": "Dust groundnut leaves with fine wood ash in early morning when dew is present. Ash sticks to wet leaves and creates an alkaline surface unfavorable to fungi. Repeat after rain. Traditional method.",
        "materials_needed": json.dumps(["fine wood ash", "cloth bag for dusting"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Freely available from cooking fires",
        "effectiveness": "low", "application_timing": "Early morning when leaves are wet. Repeat after each rain.",
        "safety_notes": "Avoid inhaling ash dust. Use cloth over nose.",
    },
    # --- TYLCV treatments ---
    {
        "id": 27, "disease_id": 14, "method": "Whitefly exclusion and resistant varieties",
        "description": "Use insect-proof netting (50-mesh) over nursery beds. Transplant healthy seedlings. Choose TYLCV-resistant varieties. Apply reflective silver-colored mulch to repel whiteflies.",
        "materials_needed": json.dumps(["50-mesh insect netting", "resistant tomato seed", "silver mulch or aluminum foil strips"]),
        "difficulty": "medium", "is_organic": True,
        "local_availability": "Insect netting from agricultural supply shops. Silver mulch may need to be ordered.",
        "effectiveness": "high", "application_timing": "Set up netting before sowing nursery. Mulch at transplant.",
        "safety_notes": "None.",
    },
    {
        "id": 28, "disease_id": 14, "method": "Neem oil and yellow sticky traps",
        "description": "Apply neem oil spray for whitefly control (same preparation as for cassava). Install yellow sticky traps between plants — whiteflies are attracted to yellow. Monitor traps to assess population levels.",
        "materials_needed": json.dumps(["neem oil or neem seeds", "yellow plastic sheets", "motor oil or petroleum jelly", "stakes"]),
        "difficulty": "easy", "is_organic": True,
        "local_availability": "Neem abundant. Yellow plastic from market bags can be used.",
        "effectiveness": "medium", "application_timing": "From transplant through fruiting. Replace traps when full.",
        "safety_notes": "Position traps at canopy height. Safe around food crops.",
    },
    # --- Bacterial Wilt treatments ---
    {
        "id": 29, "disease_id": 15, "method": "Soil solarization and rotation",
        "description": "Before planting, cover moist soil with clear plastic sheeting for 4-6 weeks during hot season. Solar heating kills bacteria in top 15cm. Rotate tomatoes with non-solanaceous crops (cereals, legumes) for 3+ years.",
        "materials_needed": json.dumps(["clear plastic sheeting", "rocks or soil to anchor edges"]),
        "difficulty": "medium", "is_organic": True,
        "local_availability": "Plastic sheeting available at hardware shops",
        "effectiveness": "medium", "application_timing": "During hot dry season before planting (March-May in Casamance).",
        "safety_notes": "Remove plastic before planting. Dispose of plastic properly.",
    },
    {
        "id": 30, "disease_id": 15, "method": "Raised beds and lime application",
        "description": "Grow tomatoes on raised beds (20-30cm high) for improved drainage — bacterial wilt is worse in waterlogged soil. Apply agricultural lime to raise soil pH above 6.5. The bacterium is less virulent in alkaline conditions.",
        "materials_needed": json.dumps(["agricultural lime", "hoe for bed preparation", "pH test strips"]),
        "difficulty": "medium", "is_organic": True,
        "local_availability": "Agricultural lime from input dealers. pH strips from pharmacies.",
        "effectiveness": "medium", "application_timing": "Prepare beds and apply lime 2-3 weeks before transplanting.",
        "safety_notes": "Wear gloves when handling lime. Do not over-lime — excessive pH harms plants.",
    },
    {
        "id": 31, "disease_id": 15, "method": "Grafting onto resistant rootstock",
        "description": "Graft susceptible tomato varieties onto Ralstonia-resistant rootstock (Hawaii 7996 or EG-203). The resistant roots prevent bacterial entry while the desired variety produces fruit. Highly effective but requires grafting skill.",
        "materials_needed": json.dumps(["resistant rootstock seeds (Hawaii 7996)", "grafting clips", "razor blade", "humidity chamber"]),
        "difficulty": "hard", "is_organic": True,
        "local_availability": "Rootstock seeds may need to be ordered through AVRDC/WorldVeg. Grafting clips from agricultural suppliers.",
        "effectiveness": "high", "application_timing": "Graft in nursery when seedlings have 2-3 true leaves.",
        "safety_notes": "Use sterile blade. Maintain high humidity after grafting for 7-10 days.",
    },
]

# ============================================================
# CLIMATE DATA (12 months for Casamance)
# ============================================================

CLIMATE = [
    {"id": 1, "region": "Casamance", "month": 1, "rainfall_mm": 0.5, "temperature_avg_c": 25.0, "humidity_pct": 40.0, "drought_risk": "severe", "notes": "Dry season. Harmattan winds. Irrigation needed for dry-season crops."},
    {"id": 2, "region": "Casamance", "month": 2, "rainfall_mm": 0.2, "temperature_avg_c": 27.0, "humidity_pct": 35.0, "drought_risk": "severe", "notes": "Driest month. Hot. Prepare land for rainy season."},
    {"id": 3, "region": "Casamance", "month": 3, "rainfall_mm": 0.5, "temperature_avg_c": 29.0, "humidity_pct": 38.0, "drought_risk": "severe", "notes": "Hottest period begins. Soil solarization optimal now."},
    {"id": 4, "region": "Casamance", "month": 4, "rainfall_mm": 2.0, "temperature_avg_c": 30.0, "humidity_pct": 45.0, "drought_risk": "high", "notes": "Pre-rainy season. Occasional brief showers. Final land preparation."},
    {"id": 5, "region": "Casamance", "month": 5, "rainfall_mm": 30.0, "temperature_avg_c": 30.0, "humidity_pct": 55.0, "drought_risk": "medium", "notes": "Transition month. First scattered rains. Nursery preparation for rice."},
    {"id": 6, "region": "Casamance", "month": 6, "rainfall_mm": 130.0, "temperature_avg_c": 28.0, "humidity_pct": 70.0, "drought_risk": "low", "notes": "Rainy season begins. Main planting month for maize, groundnut, cassava."},
    {"id": 7, "region": "Casamance", "month": 7, "rainfall_mm": 250.0, "temperature_avg_c": 27.0, "humidity_pct": 80.0, "drought_risk": "low", "notes": "Heavy rains. Rice transplanting. High disease pressure. Monitor fields."},
    {"id": 8, "region": "Casamance", "month": 8, "rainfall_mm": 350.0, "temperature_avg_c": 26.5, "humidity_pct": 85.0, "drought_risk": "low", "notes": "Peak rainfall. Flooding risk in lowlands. Fungal diseases peak. Weed pressure high."},
    {"id": 9, "region": "Casamance", "month": 9, "rainfall_mm": 280.0, "temperature_avg_c": 27.0, "humidity_pct": 83.0, "drought_risk": "low", "notes": "Heavy rains continue. Rice heading and flowering. Critical pest monitoring."},
    {"id": 10, "region": "Casamance", "month": 10, "rainfall_mm": 120.0, "temperature_avg_c": 28.0, "humidity_pct": 75.0, "drought_risk": "low", "notes": "Rains taper off. Maize and groundnut harvest begins. Rice grain filling."},
    {"id": 11, "region": "Casamance", "month": 11, "rainfall_mm": 15.0, "temperature_avg_c": 27.0, "humidity_pct": 55.0, "drought_risk": "medium", "notes": "Dry season onset. Rice harvest. Post-harvest processing and storage."},
    {"id": 12, "region": "Casamance", "month": 12, "rainfall_mm": 1.0, "temperature_avg_c": 25.5, "humidity_pct": 42.0, "drought_risk": "high", "notes": "Dry season. Cassava can still be harvested. Dry-season vegetable gardens begin."},
]
