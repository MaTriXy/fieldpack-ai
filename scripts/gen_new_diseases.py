"""Generate new disease knowledge chunks for the Casamance agriculture pack.

Produces scripts/data/new_diseases.json containing 52 chunks (4 per disease)
covering 13 new diseases (disease_id 16-28) for tomato, groundnut, maize,
rice, millet, and cassava.

Output format matches ChromaDB injection expectations:
  { id, collection, metadata, document }

Run with:
  ./venv/Scripts/python.exe scripts/gen_new_diseases.py
"""

import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Chunk definitions
# Each entry is (disease_id, slug, disease_name, crop, d_type, severity,
#                symptoms_parent, symptoms_child,
#                prevention_parent, prevention_child)
# ---------------------------------------------------------------------------

DISEASES = [
    # ==================================================================
    # TOMATO -- 3 new diseases (IDs 16-18)
    # ==================================================================
    {
        "disease_id": 16,
        "slug": "early_blight_of_tom",
        "disease_name": "Early Blight of Tomato",
        "crop": "tomato",
        "type": "fungal",
        "severity": "high",
        "symptoms_parent": (
            "Early Blight of Tomato is a highly severe fungal disease caused by Alternaria solani, "
            "widespread across tomato-growing zones in Casamance. The disease first appears on the "
            "oldest, lowest leaves as small dark brown to black spots that enlarge and develop "
            "distinct concentric rings, creating a characteristic target or bullseye pattern. "
            "Yellowing halos typically surround the lesions. As the disease advances upward through "
            "the canopy, affected leaves wither and drop, exposing fruit to sunscald. Stem lesions "
            "may appear as dark, sunken, elongated streaks near the soil line. Fruit can develop "
            "dark, firm, sunken areas near the calyx end, making them unmarketable.\n\n"
            "Visually, look for the concentric ring pattern on brown leaf spots -- this bullseye "
            "appearance is the defining diagnostic feature. Spots start on lower older leaves first "
            "and progress upward. Affected tissue has a dry, papery texture. Severe defoliation "
            "on the lower half of the plant while upper growth looks temporarily healthy is common.\n\n"
            "The fungus spreads by wind-dispersed conidia and rain splash from infected plant "
            "debris that persists in the soil between seasons. Warm temperatures of 24-29 degrees C "
            "combined with alternating wet and dry periods create ideal infection conditions. In "
            "Casamance, the transition from the wet season to the cool dry season in October-November "
            "represents the highest-risk window for early blight outbreaks."
        ),
        "symptoms_child": (
            "My tomato plant has brown spots on the lower leaves with ring patterns that look like "
            "a target or bullseye. The leaves around the spots are turning yellow and some are falling "
            "off. I can also see dark sunken spots on some of the fruit near the stem. The problem "
            "started on the bottom leaves and is moving upward. What disease is this and what should I do?"
        ),
        "prevention_parent": (
            "To prevent Early Blight of Tomato, practice crop rotation by not planting tomatoes or "
            "other solanaceous crops -- peppers, eggplant, potato -- in the same plot for at least "
            "2 to 3 seasons. Remove and destroy all infected plant debris after harvest; do not "
            "compost it, as the fungus survives in organic matter. Source certified disease-free "
            "seedlings from a reliable nursery rather than saving seed from affected plants.\n\n"
            "Maintain adequate plant spacing of 60 to 80 cm between plants to promote air circulation "
            "and reduce leaf wetness duration. Stake or cage plants to keep foliage off the soil. "
            "Apply mulch around the base to prevent rain splash carrying spores from the soil onto "
            "lower leaves. Water at the base of plants rather than overhead; drip irrigation is "
            "strongly preferred. Remove and bury the lowest 2 to 3 leaves once plants are established.\n\n"
            "In Casamance, begin preventive copper-based fungicide sprays -- copper oxychloride or "
            "Bordeaux mixture -- before symptoms appear, especially if early blight damaged the field "
            "in previous seasons. Spray every 10 to 14 days during the wet season and when conditions "
            "are humid. NEEM-based sprays provide a low-cost organic alternative with moderate efficacy. "
            "Varieties with partial resistance such as Roma VF are preferable where available."
        ),
        "prevention_child": (
            "How do I prevent early blight on my tomato plants? What crop rotation should I use to "
            "avoid tomato fungal diseases? How can I stop the brown bullseye spots from appearing "
            "on tomato leaves? What spacing and watering practices reduce early blight risk? "
            "Is there an organic treatment for early blight of tomato?"
        ),
    },
    {
        "disease_id": 17,
        "slug": "late_blight_of_toma",
        "disease_name": "Late Blight of Tomato",
        "crop": "tomato",
        "type": "fungal",
        "severity": "high",
        "symptoms_parent": (
            "Late Blight of Tomato is one of the most destructive diseases of tomato worldwide, "
            "caused by the oomycete pathogen Phytophthora infestans. In Casamance it is most "
            "dangerous during the cool, humid nights of the dry-season harmattan period and at "
            "the tail end of the rainy season when temperatures drop and fog is common. Symptoms "
            "begin as pale green, water-soaked spots on leaves that quickly expand, turning brown "
            "to purplish-black. In humid conditions, a characteristic white to grayish cottony "
            "sporulation -- the pathogen's sporangiophores -- is visible on the underside of "
            "affected leaves in early morning. Entire leaflets can be killed within 2 to 3 days "
            "under favorable conditions.\n\n"
            "Stem lesions appear as dark brown to black, greasy-looking streaks that can girdle "
            "the stem and cause plant collapse. Fruit infection produces firm, brown, greasy-surfaced "
            "lesions that are typically bronze-brown in color with a distinct irregular margin; "
            "internal tissue turns dark brown throughout. Infected fruit rots completely within days.\n\n"
            "The pathogen spreads with extraordinary speed through windborne sporangia, especially "
            "in cool (15-20 degrees C), wet conditions with leaf wetness periods exceeding 10 hours. "
            "A single infected plant can spread the disease to an entire field within a week under "
            "ideal conditions. The disease does not overwinter in crop debris in tropical climates "
            "but re-enters fields from infected seed, transplants, or windborne inoculum from "
            "neighboring areas."
        ),
        "symptoms_child": (
            "My tomato plants are dying very fast -- brown-black patches are spreading across the "
            "leaves and stems, and I see a white fuzzy mold on the underside of leaves in the morning. "
            "The fruit is turning brown and rotting quickly. The whole plant looks like it is collapsing. "
            "What is this fast-spreading tomato disease and how do I stop it?"
        ),
        "prevention_parent": (
            "Late blight management requires a combination of resistant varieties, strict cultural "
            "practices, and timely fungicide application because the disease can destroy an entire "
            "field in days once established. Use certified disease-free transplants and inspect "
            "seedlings carefully before planting. Avoid planting in low-lying areas with poor air "
            "drainage where cool, humid air pools at night. Plant with wide spacing -- at least "
            "70 cm between plants -- to improve airflow.\n\n"
            "Water only in the morning so leaves dry before nightfall; overhead irrigation at "
            "evening creates the extended leaf wetness that triggers infection. Remove and destroy "
            "any infected plant material immediately -- do not leave debris in the field. Monitor "
            "fields daily during the cool humid periods in Casamance from November to February.\n\n"
            "Fungicide protection is essential once risk is high. Copper-based products such as "
            "Bordeaux mixture or copper hydroxide are effective protectants but must be applied "
            "before infection occurs. Systemic fungicides containing mancozeb or chlorothalonil "
            "provide stronger protection. In areas with a history of late blight, begin protective "
            "sprays at transplanting and continue on a 7 to 10 day schedule during high-risk "
            "weather. Where available, partially resistant varieties such as Mountain Magic or "
            "TYLC-tolerant lines reduce risk significantly."
        ),
        "prevention_child": (
            "How do I protect my tomatoes from late blight? My neighbor's tomatoes got a disease "
            "that spread to everyone in one week -- how do I prevent that? What fungicide stops "
            "the white mold and black rot on tomato leaves and fruit? How do I know if the weather "
            "is risky for late blight in Casamance?"
        ),
    },
    {
        "disease_id": 18,
        "slug": "fusarium_wilt_of_to",
        "disease_name": "Fusarium Wilt of Tomato",
        "crop": "tomato",
        "type": "fungal",
        "severity": "high",
        "symptoms_parent": (
            "Fusarium Wilt of Tomato is a soilborne fungal disease caused by Fusarium oxysporum "
            "f. sp. lycopersici that persists indefinitely in contaminated soil. It is a vascular "
            "disease -- the pathogen infects roots and colonizes the water-conducting xylem vessels, "
            "blocking water transport. Symptoms typically appear when plants begin to fruit and "
            "stress increases. The first sign is yellowing of leaves on one side of a plant or on "
            "one branch only, creating an asymmetric yellowing pattern that helps distinguish it "
            "from other wilts. Affected leaves droop and wilt during the heat of the day but may "
            "partially recover at night. As the disease advances, wilting becomes permanent.\n\n"
            "The most diagnostic feature is revealed when you cut the main stem near the base: "
            "the vascular tissue shows a characteristic brown-to-reddish-brown discoloration "
            "inside the stem, running upward from the roots. This internal staining is visible "
            "as a streak or ring of brown tissue just inside the outer stem layer. The external "
            "stem surface typically remains green and symptom-free until late stages.\n\n"
            "In Casamance's sandy soils, which warm rapidly and drain quickly, Fusarium wilt is "
            "particularly problematic because the pathogen thrives in warm soil (24-28 degrees C) "
            "and infected soil remains infectious for many years. The fungus enters through roots "
            "and spreads through the soil via infected plant debris, equipment, irrigation water, "
            "and contaminated transplant roots."
        ),
        "symptoms_child": (
            "My tomato plant is wilting on one side only -- one branch or set of leaves is yellow "
            "and drooping but the other side looks okay. When I cut the stem near the bottom I can "
            "see a brown streak inside. The plant collapses even when I water it. What is causing "
            "one-sided wilting in my tomato and can it spread to other plants?"
        ),
        "prevention_parent": (
            "Fusarium wilt has no chemical cure once a plant is infected -- management must be "
            "preventive. The single most effective tool is using resistant varieties: tomato "
            "varieties carrying Fusarium wilt resistance are labeled with 'F' in their name, "
            "such as Roma VF, Heinz 1370, or locally adapted ISRA varieties. Always choose "
            "resistant varieties in fields with a history of the disease.\n\n"
            "Practice long crop rotations of 4 to 6 years without tomatoes or other solanaceous "
            "crops in infected fields. Avoid introducing the pathogen into new fields by using "
            "healthy transplants, sanitizing transplanting tools, and preventing irrigation water "
            "from flowing from infected to clean areas. Remove and burn infected plants immediately "
            "when symptoms appear -- do not compost them.\n\n"
            "In Casamance, soil solarization during the hot dry season offers a practical "
            "low-cost option: cover moist soil with clear plastic sheeting for 4 to 6 weeks "
            "during June-August when soil temperatures under plastic can reach 55-60 degrees C, "
            "enough to kill Fusarium propagules in the top 15 cm. After removing infected plants, "
            "drench the hole and surrounding soil with a 1% bleach solution before refilling. "
            "Adding organic compost from non-solanaceous materials improves soil biological "
            "suppression of the pathogen over time."
        ),
        "prevention_child": (
            "How do I prevent Fusarium wilt from killing my tomato plants? What tomato varieties "
            "are resistant to Fusarium wilt in Senegal? My soil has Fusarium wilt -- how long "
            "before I can plant tomatoes again? Can I treat the soil to kill the tomato wilt fungus? "
            "How do I stop wilt disease spreading to healthy tomato plants?"
        ),
    },
    # ==================================================================
    # GROUNDNUT -- 2 new diseases (IDs 19-20)
    # ==================================================================
    {
        "disease_id": 19,
        "slug": "aflatoxin_contam_gro",
        "disease_name": "Aflatoxin Contamination of Groundnut",
        "crop": "groundnut",
        "type": "fungal",
        "severity": "high",
        "symptoms_parent": (
            "Aflatoxin contamination of groundnut is caused by the mold Aspergillus flavus and "
            "related species that colonize groundnut pods and kernels, producing highly toxic and "
            "carcinogenic aflatoxin compounds. Unlike most plant diseases, aflatoxin contamination "
            "is an invisible food safety hazard -- the mold can be present at dangerous levels "
            "without obvious symptoms. However, visible signs of infection include a yellow-green "
            "to olive-green powdery mold on the surface of pods, kernels, or stored grain. "
            "Infected kernels may appear shriveled, discolored, or have a chalky texture. "
            "Heavily molded pods or kernels emit a distinctive musty odor.\n\n"
            "The risk is greatest when groundnut plants experience drought stress during pod "
            "filling (the last 4 to 6 weeks before harvest), followed by late-season rains that "
            "raise humidity just before harvest. In Casamance, erratic rainfall at the end of the "
            "rainy season in September-October creates exactly this high-risk pattern. Soil "
            "insects that damage pods, delayed harvest, and poor drying conditions after harvest "
            "all dramatically increase contamination levels.\n\n"
            "Aflatoxins cannot be seen, smelled reliably, or destroyed by cooking -- they are "
            "heat-stable toxins. Consuming aflatoxin-contaminated groundnuts causes acute liver "
            "toxicity at high doses and chronic liver cancer risk at lower chronic exposures. "
            "Children and malnourished individuals are most vulnerable. This makes aflatoxin one "
            "of the most important food safety hazards for groundnut-producing families in Casamance."
        ),
        "symptoms_child": (
            "My stored groundnuts have a green or yellowish mold on some of the kernels and a "
            "musty smell. Some kernels look shriveled or discolored. Are my groundnuts safe to "
            "eat or sell? How do I know if groundnuts have aflatoxin? What does Aspergillus mold "
            "look like on groundnuts?"
        ),
        "prevention_parent": (
            "Preventing aflatoxin contamination requires action across the entire production chain "
            "from field through storage. In the field, the highest-impact intervention is ensuring "
            "adequate soil moisture during pod filling -- the last 4 to 6 weeks before harvest. "
            "Where irrigation is possible, supplemental watering during this critical window "
            "significantly reduces contamination. Early planting to match rainfall patterns, "
            "and using drought-tolerant varieties such as Fleur 11 or JL 24 adapted to Casamance, "
            "both reduce drought-stress risk during pod fill.\n\n"
            "Harvest at optimal maturity -- do not delay harvest hoping for higher yield, as "
            "post-maturity delay sharply increases mold entry through aging pods. Shell and dry "
            "groundnuts quickly to below 8% moisture content before storage: spread pods in "
            "thin layers on clean raised drying platforms under direct sun, turning frequently. "
            "Never dry on bare soil. In Casamance's humid climate, achieving safe moisture in "
            "large lots can take 7 to 10 days of good drying weather.\n\n"
            "Store in clean, dry, well-ventilated structures. Hermetic storage using airtight "
            "bags such as triple-layer GrainPro bags or PICS bags prevents moisture re-absorption "
            "and oxygen deprivation inhibits mold growth. Sort and remove all damaged, shriveled, "
            "or discolored kernels before storage. Never mix old-season groundnuts with new "
            "harvest. The Purdue Improved Crop Storage (PICS) bag system has been validated for "
            "West Africa and is available through agricultural extension services in Senegal."
        ),
        "prevention_child": (
            "How do I prevent aflatoxin in my groundnuts? When should I harvest groundnuts to "
            "avoid mold contamination? How do I dry groundnuts properly after harvest to prevent "
            "aflatoxin? What storage bags or methods protect groundnuts from Aspergillus mold? "
            "Are my groundnuts safe if some have green mold?"
        ),
    },
    {
        "disease_id": 20,
        "slug": "groundnut_rust",
        "disease_name": "Groundnut Rust",
        "crop": "groundnut",
        "type": "fungal",
        "severity": "medium",
        "symptoms_parent": (
            "Groundnut Rust is a moderately severe fungal disease caused by Puccinia arachidis, "
            "an obligate rust pathogen that affects groundnut crops across sub-Saharan Africa "
            "including Casamance. Rust appears first on the lower surface of leaves as small "
            "orange-brown to rust-colored pustules -- these are the uredia containing masses "
            "of orange urediniospores. As infections coalesce, entire leaflets become covered "
            "with the characteristic rusty-orange powder. The upper leaf surface shows pale "
            "yellow spots corresponding to the pustules below. Heavily infected leaves turn "
            "yellow and drop prematurely, reducing photosynthetic capacity and pod fill.\n\n"
            "The distinctive diagnostic feature is the bright orange powdery masses on the "
            "underside of leaves: if you rub your finger across an infected leaf, it picks up "
            "orange powder. This distinguishes rust from leaf spots, which have more discrete "
            "lesions without the powdery spore masses. Rust often appears in the field from "
            "August to October in Casamance as the rainy season progresses.\n\n"
            "The pathogen spreads explosively via windborne urediniospores that travel long "
            "distances. A single infected plant can produce millions of spores. Warm temperatures "
            "of 20-28 degrees C with high humidity and leaf wetness periods of 6 or more hours "
            "favor infection. Yield losses of 15 to 50 percent are possible under severe "
            "epidemics when infection occurs before pod-filling stage."
        ),
        "symptoms_child": (
            "My groundnut leaves have orange or rust-colored powder on the underside and pale "
            "yellow spots on top. The leaves are turning yellow and falling off early. When I "
            "touch the orange spots, a rusty powder rubs off on my fingers. What disease causes "
            "orange powder under groundnut leaves?"
        ),
        "prevention_parent": (
            "Managing groundnut rust relies primarily on growing resistant or tolerant varieties "
            "combined with early planting to avoid peak rust pressure. In Casamance, ICRISAT and "
            "ISRA Senegal have identified varieties with good rust tolerance including Fleur 11, "
            "which is widely grown in the region. Early planting at the onset of the rains in "
            "June-July allows pod filling to complete before rust pressure peaks in September-October.\n\n"
            "When rust is detected early, applying sulfur-based fungicides or mancozeb provides "
            "effective control. A protective spray schedule every 14 days from when the crop "
            "first shows susceptible leaf area (around 30 days after planting) through late "
            "pod fill is effective. Triazole fungicides such as triadimefon provide both "
            "protective and curative action against rust if available locally.\n\n"
            "Cultural measures that reduce humidity in the canopy also help: avoid excessive "
            "plant density, ensure good soil drainage, and avoid late-season irrigation that "
            "prolongs leaf wetness. Remove crop residues after harvest to reduce the green "
            "bridge for rust spores, though windborne spread means this has limited effect "
            "alone. Record-keeping on when rust first appears each season helps predict "
            "future outbreak timing for preventive spray planning."
        ),
        "prevention_child": (
            "How do I prevent rust disease on my groundnuts? What groundnut varieties are "
            "resistant to rust in Senegal? What spray can I use against orange rust on "
            "groundnut leaves? When does groundnut rust normally appear in Casamance?"
        ),
    },
    # ==================================================================
    # MAIZE -- 2 new diseases (IDs 21-22)
    # ==================================================================
    {
        "disease_id": 21,
        "slug": "maize_lethal_necrosi",
        "disease_name": "Maize Lethal Necrosis",
        "crop": "maize",
        "type": "viral",
        "severity": "high",
        "symptoms_parent": (
            "Maize Lethal Necrosis (MLN) is a highly destructive viral complex caused by the "
            "synergistic interaction of Maize Chlorotic Mottle Virus (MCMV) and a potyvirus, "
            "most often Sugarcane Mosaic Virus (SCMV) or Wheat Streak Mosaic Virus. The "
            "combination of both viruses causes far more severe damage than either alone. "
            "MLN has devastated maize production in East Africa since 2011 and has spread "
            "toward West Africa, making it an emerging threat to Casamance farmers.\n\n"
            "Symptoms begin as yellowing starting from leaf tips and margins of young inner "
            "leaves, progressing to chlorotic mottling and streaking. Severe cases show "
            "necrosis -- dead brown tissue -- spreading from leaf tips inward, eventually "
            "killing all leaves. The ear fails to fill, producing few or no grains, or the "
            "cob is completely barren. In young plants infected early, the growing point dies "
            "and the entire plant collapses. A diagnostic field observation: when multiple "
            "plants in a cluster all show yellowing and necrosis together, with no viable "
            "grain formation, MLN should be suspected.\n\n"
            "MCMV is transmitted by thrips (Frankliniella williamsi), corn rootworms, and "
            "possibly other vectors. SCMV is transmitted by aphids in a nonpersistent manner. "
            "The viruses also spread through infected seed, making seed sourcing critical. "
            "High thrips and aphid populations during dry conditions favor rapid spread "
            "through a field."
        ),
        "symptoms_child": (
            "My maize plants have yellow-brown dying leaves starting from the tips, and the "
            "cobs are empty with no grain. Several plants in a patch are all dying at the same "
            "time. The inner young leaves are yellowing and turning brown and the plants look "
            "like they are collapsing. What disease kills maize plants and prevents grain from "
            "forming?"
        ),
        "prevention_parent": (
            "There is no cure for Maize Lethal Necrosis once a plant is infected, so prevention "
            "is critical. The most important measure is using MLN-tolerant or resistant hybrid "
            "seed: CIMMYT and national programs have released tolerant varieties including WEMA "
            "hybrids and open-pollinated varieties such as SEEDCO SC403 and DK8031. Use certified "
            "seed from reputable sources to avoid planting MCMV-infected seed, as the virus can "
            "be seed-transmitted.\n\n"
            "Control vector insects to slow spread: manage thrips and aphid populations with "
            "appropriate insecticides at early crop stages, or use neem-based sprays as an "
            "organic alternative. Avoid planting maize near already-infected fields. Rogue "
            "(remove and destroy) infected plants as soon as symptoms appear to reduce inoculum "
            "sources. Do not leave crop debris in the field; plow or burn residues promptly "
            "after harvest.\n\n"
            "Practice crop rotation: break the disease cycle by planting a non-host crop such "
            "as groundnut, cowpea, or cassava in rotation with maize. Avoid ratoon cropping "
            "(allowing maize to regrow from stumps) as the old material serves as a virus "
            "reservoir. Early planting at the onset of rains gives maize plants the opportunity "
            "to reach pollination before peak insect vector pressure."
        ),
        "prevention_child": (
            "How do I prevent Maize Lethal Necrosis from destroying my maize crop? What maize "
            "varieties are resistant to MLN virus in West Africa? How do I control thrips and "
            "aphids that spread maize virus diseases? My whole maize plot is dying -- is it "
            "MLN and what should I do?"
        ),
    },
    {
        "disease_id": 22,
        "slug": "fall_armyworm_maize",
        "disease_name": "Fall Armyworm Damage on Maize",
        "crop": "maize",
        "type": "pest",
        "severity": "high",
        "symptoms_parent": (
            "Fall Armyworm (Spodoptera frugiperda) is an invasive pest from the Americas that "
            "has caused catastrophic maize yield losses across Africa since its arrival on the "
            "continent in 2016. It reached Senegal and the Casamance region by 2017 and has "
            "since become one of the most important threats to smallholder maize farmers. "
            "The caterpillar larvae are the damaging stage, feeding voraciously on maize "
            "leaves, stems, and ear tissue.\n\n"
            "Early instar larvae cause characteristic 'window paning' damage -- they scrape "
            "leaf surfaces leaving thin, papery, translucent patches. Older larvae consume "
            "entire leaf tissue leaving irregular holes. The most diagnostic sign is frass: "
            "the caterpillar's wet, sawdust-like greenish-brown excrement found in the "
            "whorl and at feeding sites, often before the caterpillar itself is spotted. "
            "Larvae frequently feed deep within the maize whorl, creating a 'dead heart' "
            "effect where the central growing leaf dies and turns brown while outer leaves "
            "remain green. Late instar larvae, which are the most destructive, reach 3 to "
            "4 cm in length and have a distinctive inverted Y-shape on the front of the "
            "head and four black spots forming a square on the second-to-last body segment.\n\n"
            "Damage is most severe during the vegetative stage -- V3 to V8 -- when whorl "
            "feeding can kill the growing point. Ear damage also occurs when larvae tunnel "
            "into the silk and cob. A single larva can destroy a young plant entirely and "
            "then move to neighboring plants, earning the 'armyworm' name from the way "
            "larvae march through fields in high-density infestations."
        ),
        "symptoms_child": (
            "My maize plants have holes in the leaves, the center whorl is full of brown "
            "sawdust-like frass, and the inner leaves are dying or have translucent papery "
            "patches. I can see large caterpillars with a Y mark on the head hiding inside "
            "the whorl. The damage is spreading fast to neighboring plants. Is this fall "
            "armyworm and how do I stop it?"
        ),
        "prevention_parent": (
            "Fall armyworm management in Casamance requires early detection and rapid response "
            "because populations build and spread quickly. Scout fields twice a week from "
            "emergence: check 10 plants per 100 square meters, looking for frass in the whorl, "
            "window-pane leaf damage, or larvae. Act when 20 percent or more of plants are infested "
            "during the vegetative stage, or when 10 percent of plants show whorl infestation.\n\n"
            "Biological controls effective in Casamance include applying a suspension of "
            "Bacillus thuringiensis var. kurstaki (Bt) directly into the whorl -- this kills "
            "young larvae with no harm to beneficial insects. Spinosad, derived from a soil "
            "bacterium, is another organic-approved option. Traditional approaches include "
            "applying wood ash or sand mixed with a small amount of salt directly into the "
            "whorl to desiccate young larvae. Encourage natural enemies: parasitic wasps, "
            "ground beetles, and birds all prey on fall armyworm and are supported by "
            "maintaining field borders and reducing broad-spectrum insecticide use.\n\n"
            "When chemical control is necessary, lambda-cyhalothrin and emamectin benzoate are "
            "registered and effective. Apply early in the day or at dusk when larvae are active. "
            "Target the whorl rather than spraying the whole plant. Early planting -- within "
            "the first two weeks of the rains -- allows maize to reach a more tolerant stage "
            "before peak armyworm pressure. Push-pull intercropping with Desmodium and Napier "
            "grass borders is a validated low-cost FAO-recommended strategy."
        ),
        "prevention_child": (
            "How do I get rid of fall armyworm caterpillars in my maize? My maize whorl is "
            "full of brown frass and the center leaves are dying -- is this armyworm? What "
            "can I spray on maize to kill fall armyworm? Is there an organic way to control "
            "armyworm without chemicals? How do I scout my field for fall armyworm?"
        ),
    },
    # ==================================================================
    # RICE -- 2 new diseases (IDs 23-24)
    # ==================================================================
    {
        "disease_id": 23,
        "slug": "rice_brown_spot",
        "disease_name": "Rice Brown Spot",
        "crop": "rice",
        "type": "fungal",
        "severity": "medium",
        "symptoms_parent": (
            "Rice Brown Spot is a moderately severe fungal disease caused by Bipolaris oryzae "
            "(formerly Helminthosporium oryzae) that affects rice at all growth stages from "
            "seedling to grain filling. It is strongly associated with nutrient-deficient soils, "
            "particularly potassium and silicon deficiency, making it especially relevant for "
            "smallholder farmers in Casamance who often lack access to balanced fertilization.\n\n"
            "Symptoms on leaves appear as small, circular to oval brown spots with a light brown "
            "or grey center and a distinct dark brown border. Spots on older leaves are often "
            "surrounded by a yellow halo. Lesions can coalesce under high disease pressure, "
            "causing large areas of leaf to die and turn brown. On seedlings, brown spot causes "
            "damping off or stunted seedlings with extensive leaf spotting. On grain, the disease "
            "causes 'black kernel' or 'pecky rice' -- infected glumes turn dark brown to black, "
            "and infected kernels are shrunken, chalky, and discolored, significantly reducing "
            "milling quality and market value.\n\n"
            "In Casamance, brown spot is most common on lowland rice grown in infertile soils "
            "with inadequate drainage. The pathogen spreads through airborne conidia and is also "
            "seedborne. Temperatures of 25-30 degrees C with high humidity and prolonged leaf "
            "wetness favor the disease. Stressed plants with poor nutrition are dramatically "
            "more susceptible than well-nourished rice."
        ),
        "symptoms_child": (
            "My rice plants have brown oval spots with lighter centers on the leaves. The spots "
            "have a dark brown edge and some have a yellow ring around them. Some of my grain "
            "heads are turning black and the kernels look shrunken and discolored. The plants "
            "look generally weak and pale. What disease causes brown spots and black grain in "
            "rice?"
        ),
        "prevention_parent": (
            "The most effective long-term prevention of Rice Brown Spot is correcting soil "
            "nutrition deficiencies that predispose plants to infection. Potassium fertilization "
            "is particularly important: apply potassium chloride (muriate of potash) at 30 to "
            "60 kg K2O per hectare at transplanting. Silicon, abundant in rice hull compost "
            "and some volcanic soils, strengthens cell walls and reduces disease entry. "
            "Balanced nitrogen application is critical -- excessive nitrogen without adequate "
            "potassium increases susceptibility.\n\n"
            "Use certified disease-free or hot-water-treated seed to eliminate seedborne "
            "inoculum: soak seed in hot water at 52 degrees C for 10 minutes, or treat with "
            "Trichoderma-based biocontrol agents. Practice seed selection -- discard all "
            "discolored or shrunken seed before planting. Improve field drainage in lowland "
            "plots: stagnant water combined with nutrient stress creates ideal brown spot "
            "conditions common in some Casamance rice paddies.\n\n"
            "When disease pressure is high, copper-based fungicides or mancozeb applied at "
            "tillering and again at flag leaf stage provide adequate protection. AfricaRice "
            "recommends WARDA improved varieties such as NERICA-L series for lowland Casamance "
            "conditions, which have moderate brown spot tolerance. Regular foliar feeding "
            "with potassium silicate solution is used by some extension services as both "
            "a preventive and corrective measure."
        ),
        "prevention_child": (
            "How do I prevent brown spots on my rice plants? Why does my rice get brown spot "
            "disease every season? What fertilizer helps prevent rice brown spot? How do I "
            "treat rice seed before planting to avoid brown spot? My rice grain is turning "
            "black and chalky -- is this brown spot?"
        ),
    },
    {
        "disease_id": 24,
        "slug": "rice_sheath_blight",
        "disease_name": "Rice Sheath Blight",
        "crop": "rice",
        "type": "fungal",
        "severity": "medium",
        "symptoms_parent": (
            "Rice Sheath Blight is caused by Rhizoctonia solani AG1-IA, a soilborne fungal "
            "pathogen that is one of the most yield-limiting rice diseases worldwide and a "
            "significant problem in intensively managed irrigated rice in Casamance. The "
            "disease is strongly associated with high nitrogen fertilization and dense "
            "planting, conditions that create a humid canopy microclimate favorable for "
            "the pathogen.\n\n"
            "Symptoms begin on the leaf sheath close to the water line -- the part of the "
            "plant at or just above the soil surface -- as oval to irregular greenish-grey "
            "water-soaked lesions. These expand into large, irregular lesions with a "
            "greyish-white center and a brown to dark brown irregular margin. Under humid "
            "conditions, white cottony mycelium of the fungus is visible at the margins of "
            "active lesions. The disease progresses upward from the sheath to the leaf blade, "
            "and in severe cases advances to the flag leaf and panicle. Infected panicles "
            "produce poorly filled grain. Round, brown to black sclerotia -- resting bodies "
            "about the size of a mustard seed -- form on infected tissue and fall into the "
            "soil or water, where they persist for years.\n\n"
            "The pathogen survives as sclerotia in the soil and in crop debris. Sclerotia "
            "float on irrigation water and can infect plants they contact. The disease is "
            "most severe in densely planted fields with high nitrogen under warm, humid "
            "conditions during tillering to grain fill."
        ),
        "symptoms_child": (
            "My rice plants have large grey-white irregular patches on the sheaths near the "
            "water line, with brown or dark edges. The patches are spreading upward to the "
            "leaves and some plants have white fluffy mold at the lesion edge. I can see "
            "small round brown seeds on the infected tissue. What is the grey-white sheath "
            "disease on my rice plants?"
        ),
        "prevention_parent": (
            "Preventing Rice Sheath Blight centers on avoiding the dense, highly fertilized "
            "canopy conditions the pathogen thrives in. Reduce plant density: transplant at "
            "wider spacings of 20 by 20 cm rather than crowded rows. Split nitrogen "
            "application -- applying the full dose at once creates a flush of lush vegetative "
            "growth that raises canopy humidity and disease risk. Apply nitrogen in three "
            "equal splits at transplanting, tillering, and panicle initiation.\n\n"
            "Drain fields periodically during the vegetative stage -- alternating wet and dry "
            "conditions (AWD technique) disrupts the water-surface sclerotia dispersal mechanism "
            "and reduces humidity. Remove floating sclerotia from irrigation channels when "
            "visible. Do not transplant seedlings taken from sheath-blight-infected nurseries.\n\n"
            "Biological control using Trichoderma harzianum applied to the soil at transplanting, "
            "or seed treatment with Pseudomonas fluorescens, is practiced by extension-supported "
            "farmers in Casamance as an organic management option. When chemical control is "
            "needed, validamycin is the most effective fungicide specifically registered against "
            "Rhizoctonia in rice; hexaconazole and propiconazole also provide effective control. "
            "AfricaRice lowland varieties in the NERICA-L series show some tolerance to sheath "
            "blight compared to traditional varieties."
        ),
        "prevention_child": (
            "How do I prevent sheath blight on my rice? My rice has grey patches spreading "
            "from the bottom sheaths upward -- what is it? What fungicide controls sheath "
            "blight in rice? Does plant spacing and fertilizer amount affect sheath blight? "
            "How do I manage the small round brown seeds that cause rice sheath blight?"
        ),
    },
    # ==================================================================
    # MILLET -- 3 new diseases (IDs 25-27) -- NEW CROP
    # ==================================================================
    {
        "disease_id": 25,
        "slug": "downy_mildew_of_mil",
        "disease_name": "Downy Mildew of Millet",
        "crop": "millet",
        "type": "fungal",
        "severity": "high",
        "symptoms_parent": (
            "Downy Mildew of Millet, also known as Green Ear disease, is a highly severe "
            "oomycete disease caused by Sclerospora graminicola and is the most economically "
            "important disease of pearl millet (Pennisetum glaucum) in the Sahel and Casamance "
            "region of Senegal. Under severe epidemics it can destroy 30 to 100 percent of "
            "susceptible crops. The pathogen is both soilborne (surviving as oospores for years) "
            "and airborne (spreading via sporangia), making it extremely persistent once a "
            "field is infected.\n\n"
            "The most striking and economically damaging symptom is the transformation of the "
            "grain head into a mass of leafy green shoots -- this is the 'green ear' or 'phyllody' "
            "symptom where floral parts revert to vegetative structures, producing completely "
            "sterile green shoots instead of grain. Infected plants produce no yield at all. "
            "Earlier in infection, systemically infected seedlings show a characteristic downy "
            "white sporulation on the underside of lower leaves, with corresponding pale green "
            "or yellow striping on the upper leaf surface. Infected plants are often stunted "
            "with excessive tillering. Locally infected mature leaves show yellow-green patches "
            "on the upper surface with dense white downy sporulation below.\n\n"
            "In Casamance, primary infection comes from soilborne oospores that germinate when "
            "the first rains arrive in May-June. Secondary spread during the season is through "
            "airborne sporangia produced on infected plants, rapidly infecting neighboring "
            "susceptible plants. Cool, humid nights with temperatures around 20-25 degrees C "
            "and morning dew are ideal for sporulation and secondary infection."
        ),
        "symptoms_child": (
            "My millet plants have white fuzzy powder on the undersides of the lower leaves "
            "with yellow-green stripes on top. Some plants have no grain head at all -- instead "
            "there are leafy green shoots where the grain should be. The affected plants are "
            "short and bushy with lots of side shoots but no grain. What disease turns millet "
            "grain heads into green shoots and makes white powder on the leaves?"
        ),
        "prevention_parent": (
            "Managing Downy Mildew of Millet requires an integrated approach because the pathogen "
            "persists for decades as soilborne oospores. The single most effective measure is "
            "planting resistant varieties: ICRISAT and ISRA Senegal have released downy mildew "
            "resistant pearl millet varieties specifically bred for the Sahel-Casamance region, "
            "including SOSAT-C88, HKP, and ICMV IS 89305. These resistant varieties should be "
            "the first choice for any field with a history of green ear disease.\n\n"
            "Metalaxyl or mefenoxam seed treatment is highly effective at protecting emerging "
            "seedlings from the soilborne oospore infection that causes systemic disease: "
            "treat seed at 6 grams active ingredient per kilogram of seed before planting. "
            "This treatment is low-cost and provides several weeks of protection during the "
            "most critical early growth stage. The seed treatment does not protect against "
            "secondary airborne infection but prevents the most economically damaging systemic "
            "infection that causes green ear.\n\n"
            "Rogue infected plants immediately when green ear symptoms first appear -- remove "
            "and burn them before sporulation adds to the inoculum burden. Practice field "
            "sanitation: plow crop residues under promptly after harvest to bury oospores "
            "deeper in the soil. Avoid planting millet in the same field for more than two "
            "consecutive seasons in heavily infected fields; a season of cowpea, groundnut, "
            "or sesame breaks the cycle. Do not save seed from fields where green ear was "
            "present."
        ),
        "prevention_child": (
            "How do I prevent green ear disease (downy mildew) in my millet? What millet "
            "varieties are resistant to downy mildew in Senegal? How do I treat millet seed "
            "to prevent the white mold disease? My millet has no grain -- just green shoots "
            "at the top. How do I stop this from spreading to other plants? Should I pull "
            "out infected millet plants?"
        ),
    },
    {
        "disease_id": 26,
        "slug": "millet_head_smut",
        "disease_name": "Millet Head Smut",
        "crop": "millet",
        "type": "fungal",
        "severity": "medium",
        "symptoms_parent": (
            "Millet Head Smut is caused by Moesziomyces penicillariae (formerly Tolyposporium "
            "penicillariae), a moderately severe smut disease of pearl millet that is "
            "widely distributed across West Africa including Casamance. The disease is not "
            "visible until the crop reaches the heading stage, which makes early-season "
            "detection impossible without molecular tools.\n\n"
            "At heading, infected spikelets are replaced by sori -- masses of the smut fungus -- "
            "that initially appear as ovoid, pale greyish-green swellings that rupture and "
            "release a mass of dark olive-brown to black powdery teliospores at maturity. "
            "Infected heads may have individual spikelets or clusters of spikelets replaced "
            "by smut sori, or in severe cases the entire head may be a mass of smut spores. "
            "Smutted sori are usually slightly larger than healthy grain and are soft before "
            "rupture. After the sori burst, only an empty or papery structure remains among "
            "healthy grain. Yield loss depends on what proportion of spikelets are infected, "
            "ranging from minor (a few sori per head) to severe (100 percent of heads affected "
            "in susceptible varieties under high inoculum pressure).\n\n"
            "The teliospores contaminate soil and seed at harvest. They germinate at the time "
            "of flowering and infect developing florets. Teliospores survive in soil for "
            "several years and are spread by wind, rain, harvesting equipment, and contaminated "
            "seed."
        ),
        "symptoms_child": (
            "My millet grain heads have swollen greenish lumps instead of normal grain. When I "
            "squeeze them they are soft and some have burst open releasing dark brown-black "
            "powder. The smutted lumps are scattered among some normal grain or in some plants "
            "the whole head is affected. What disease causes swollen smutty heads on millet "
            "instead of normal grain?"
        ),
        "prevention_parent": (
            "Head smut prevention in millet is primarily achieved through seed treatment and "
            "variety selection. Systemic fungicide seed treatments are highly effective: "
            "carboxin plus thiram (as Vitavax 200) or thiram alone applied at 3 grams per "
            "kilogram of seed thoroughly coats the seed surface and provides protection "
            "against smut spore germination at flowering. Metalaxyl seed dressing also "
            "provides good control. These seed treatments are inexpensive relative to the "
            "yield loss they prevent.\n\n"
            "Use smut-tolerant varieties: ICRISAT has screened many West African pearl millet "
            "varieties for head smut resistance. Varieties in the SOSAT and HKP series show "
            "better tolerance than traditional tall varieties. Avoid saving seed from any "
            "field where smut was observed -- even seed that looks clean may carry surface-"
            "contaminating teliospores. If using saved seed, treat it before planting.\n\n"
            "At harvest, collect and burn smutted heads separately to prevent teliospores "
            "from contaminating the threshing floor and returning to the field on crop "
            "residues or equipment. Avoid threshing smutted and healthy crop together. "
            "Crop rotation with non-grass crops (groundnut, cowpea, cassava) for one to "
            "two seasons reduces soil inoculum levels. Clean threshing equipment between "
            "fields to prevent mechanical spread of teliospores."
        ),
        "prevention_child": (
            "How do I prevent smut disease on millet grain heads? What seed treatment "
            "protects millet from head smut? Can I use saved millet seed if my field had "
            "smut last season? How do I get rid of the smut spores in my soil? What millet "
            "varieties are resistant to head smut in West Africa?"
        ),
    },
    {
        "disease_id": 27,
        "slug": "millet_ergot",
        "disease_name": "Millet Ergot",
        "crop": "millet",
        "type": "fungal",
        "severity": "medium",
        "symptoms_parent": (
            "Millet Ergot is caused by Claviceps fusiformis, a moderately severe fungal disease "
            "that attacks pearl millet florets during flowering and replaces the grain with "
            "compact fungal structures. The disease is a significant problem in Casamance and "
            "across the Sahel, especially during years with high humidity or cool temperatures "
            "at flowering time, which extend the period during which florets are susceptible.\n\n"
            "The most visible early symptom is the exudation of a sticky, cream to amber-colored "
            "honeydew liquid from infected florets during and shortly after flowering. This "
            "honeydew -- actually a conidial suspension produced by the pathogen -- can be seen "
            "as droplets or dried smears on the panicle. Insects, particularly bees, flies, and "
            "ants, are attracted to the honeydew and serve as vectors carrying conidia between "
            "plants. As the season progresses, infected spikelets develop into hard, elongated, "
            "curved, dark grey-black sclerotia -- the ergot bodies -- that protrude from the "
            "glumes and replace normal grain. Ergot bodies are 0.5 to 1 cm long and immediately "
            "recognizable as they replace individual kernels in the grain head.\n\n"
            "Ergot bodies contain toxic alkaloids that cause ergotism in humans and animals: "
            "symptoms include convulsions, burning sensations, gangrene of extremities, and in "
            "severe cases death. This food safety dimension makes ergot a public health concern "
            "as well as a crop loss issue. Ergot bodies are released from the grain head at "
            "harvest and contaminate threshing floors and soil, where they serve as primary "
            "inoculum for the following season."
        ),
        "symptoms_child": (
            "My millet grain heads are dripping a sticky liquid at flowering time and attracting "
            "lots of insects. Later I can see dark curved hard pieces mixed in with the grain "
            "instead of normal kernels. Are these dark hard pieces in my millet safe to eat? "
            "What causes sticky liquid on millet flowers and black curved hard lumps in the "
            "grain head?"
        ),
        "prevention_parent": (
            "Managing Millet Ergot requires attention to both the crop loss and the food "
            "safety hazard. For crop protection, the most effective field measures are early "
            "planting to avoid the extended flowering period that coincides with high humidity "
            "in August-September in Casamance, and using short-duration varieties that flower "
            "and complete grain fill quickly before peak ergot risk. Varieties with tightly "
            "enclosed florets (chasmogamous flowering) are inherently more susceptible than "
            "those with faster, more compact flowering.\n\n"
            "Crop rotation and field hygiene are important to reduce soil-surface ergot body "
            "inoculum: deep-plowing after harvest buries sclerotia below the germination "
            "depth. Do not use millet for two consecutive seasons in heavily infected fields. "
            "Avoid planting in low-lying areas prone to morning fog or extended leaf wetness "
            "at flowering time.\n\n"
            "At harvest, winnow the threshed grain vigorously -- ergot bodies are lighter "
            "than grain and are removed by wind winnowing. Sieve through an appropriately "
            "sized mesh to physically separate remaining ergot bodies. Do not consume or "
            "feed to animals any grain lot with more than 0.1 percent ergot body contamination "
            "by weight -- this is the safety threshold. Sunlight exposure to the honeydew "
            "droplets helps by drying them and reducing insect-mediated spread within the "
            "crop. No fully resistant varieties are available commercially, but varieties "
            "with moderate tolerance exist in ICRISAT germplasm collections."
        ),
        "prevention_child": (
            "Are the black hard pieces in my millet grain dangerous to eat? How do I separate "
            "ergot from millet grain after harvest? How do I prevent the sticky liquid and dark "
            "lumps from appearing in my millet? What can I do to stop ergot disease in millet? "
            "How much ergot is safe in millet grain for eating or selling?"
        ),
    },
    # ==================================================================
    # CASSAVA -- 1 new disease (ID 28)
    # ==================================================================
    {
        "disease_id": 28,
        "slug": "cassava_root_rot",
        "disease_name": "Cassava Root Rot",
        "crop": "cassava",
        "type": "fungal",
        "severity": "medium",
        "symptoms_parent": (
            "Cassava Root Rot is a moderately severe disease complex caused primarily by "
            "Phytophthora spp. and Fusarium spp., often acting together or separately "
            "depending on soil conditions. It is the most important storage root disease "
            "of cassava in West Africa and is particularly damaging in Casamance's lowland "
            "and valley-bottom fields that experience seasonal waterlogging, as prolonged "
            "soil saturation creates ideal conditions for Phytophthora infection.\n\n"
            "Above-ground symptoms include wilting and yellowing of leaves, often "
            "beginning on one or a few branches, followed by collapse of the canopy. "
            "Stem bases may show brown water-soaked lesions at soil level. However, "
            "the primary and diagnostic symptoms are found in the storage roots: "
            "infected roots show dark brown to black internal discoloration that "
            "progresses from the outer cortex inward, sometimes leaving only a central "
            "healthy core in early stages. Advanced infections cause complete internal "
            "browning with a wet, soft rot of the flesh; a sour or fermented odor "
            "accompanies advanced wet rot. Fusarium-dominated infections tend to produce "
            "a drier, more fibrous internal browning, while Phytophthora causes a wetter, "
            "darker rot. Affected roots are unpalatable and toxic due to increased "
            "cyanogenic glucoside levels in stressed cassava.\n\n"
            "The disease develops silently underground and may only be discovered at harvest. "
            "Losses in waterlogged fields can reach 50 to 100 percent of the root crop. "
            "Warm, waterlogged soils above 28 degrees C combined with rapidly fluctuating "
            "wet-dry cycles are most favorable. Soil-infesting Phytophthora propagules can "
            "persist for many seasons."
        ),
        "symptoms_child": (
            "My cassava plant is wilting and the leaves are yellowing even though I have "
            "watered it. When I dig up the roots they are brown or black inside and some "
            "have a bad smell. The root flesh is discolored when I cut it open. Are these "
            "cassava roots safe to eat? What disease causes cassava roots to rot in the ground?"
        ),
        "prevention_parent": (
            "Preventing Cassava Root Rot centers on drainage management and variety selection "
            "because once Phytophthora or Fusarium are established in the soil they persist "
            "for long periods. Never plant cassava in fields prone to waterlogging or standing "
            "water for more than 2 to 3 days. In lowland Casamance plots, plant cassava on "
            "raised ridges or mounds (30 to 40 cm height) to ensure roots develop in the "
            "well-drained upper soil layer even when seasonal rains are heavy. Improve "
            "drainage channels in valley-bottom fields before planting.\n\n"
            "Use disease-free planting stakes: inspect cuttings for stem base discoloration "
            "before planting, as stem-base Fusarium infections in cuttings introduce the "
            "pathogen to new fields. Dipping cuttings in a 1% copper fungicide solution "
            "before planting provides protection against Phytophthora. Varieties differ in "
            "susceptibility: IITA improved varieties such as TMS 30572, TMS 98/0505, and "
            "those released by ISRA Senegal tend to have better root health than traditional "
            "varieties in high-risk conditions. Avoid early harvest of young roots; roots "
            "are most susceptible between 6 and 12 months.\n\n"
            "At harvest, harvest promptly once roots reach maturity rather than leaving "
            "them in the ground for extended periods, as roots deteriorate rapidly after "
            "physiological maturity and become more susceptible to infection. After removing "
            "infected plants, do not replant cassava in that spot for at least 2 seasons. "
            "Process or dry harvested roots quickly -- cassava roots begin fermenting within "
            "48 to 72 hours of harvest even without root rot pathogens."
        ),
        "prevention_child": (
            "How do I prevent cassava root rot? Why are my cassava roots brown inside when "
            "I harvest them? Can I eat cassava roots that are brown or black inside? How do "
            "I plant cassava in wet or flooded areas without root rot? What cassava varieties "
            "are resistant to root rot in Senegal?"
        ),
    },
]


# ---------------------------------------------------------------------------
# Chunk generation
# ---------------------------------------------------------------------------

def _make_chunk(
    disease_id: int,
    slug: str,
    disease_name: str,
    crop: str,
    d_type: str,
    severity: str,
    topic: str,
    chunk_type: str,
    document: str,
) -> dict:
    chunk_id = f"{slug}_{disease_id:03d}_{topic}_{chunk_type}"
    topic_id = f"{slug}_{disease_id:03d}_{topic}"
    return {
        "id": chunk_id,
        "collection": "disease_knowledge",
        "metadata": {
            "disease_id": str(disease_id),
            "type": d_type,
            "disease_name": disease_name,
            "chunk_type": chunk_type,
            "severity": severity,
            "crop": crop,
            "topic_id": topic_id,
        },
        "document": document,
    }


def generate_chunks(diseases: list[dict]) -> list[dict]:
    chunks = []
    for d in diseases:
        d_id = d["disease_id"]
        slug = d["slug"]
        name = d["disease_name"]
        crop = d["crop"]
        d_type = d["type"]
        severity = d["severity"]

        chunks.append(_make_chunk(
            d_id, slug, name, crop, d_type, severity,
            "symptoms", "parent", d["symptoms_parent"],
        ))
        chunks.append(_make_chunk(
            d_id, slug, name, crop, d_type, severity,
            "symptoms", "child", d["symptoms_child"],
        ))
        chunks.append(_make_chunk(
            d_id, slug, name, crop, d_type, severity,
            "prevention", "parent", d["prevention_parent"],
        ))
        chunks.append(_make_chunk(
            d_id, slug, name, crop, d_type, severity,
            "prevention", "child", d["prevention_child"],
        ))

    return chunks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "new_diseases.json"

    chunks = generate_chunks(DISEASES)

    with out_file.open("w", encoding="utf-8") as fh:
        json.dump(chunks, fh, indent=2, ensure_ascii=False)

    print(f"Written {len(chunks)} chunks to {out_file}")
    print()

    # Summary by disease
    print(f"{'ID':<4} {'Crop':<12} {'Disease':<38} {'Type':<8} {'Sev':<8} Chunks")
    print("-" * 80)
    for d in DISEASES:
        d_chunks = [c for c in chunks if c["metadata"]["disease_id"] == str(d["disease_id"])]
        print(
            f"{d['disease_id']:<4} "
            f"{d['crop']:<12} "
            f"{d['disease_name']:<38} "
            f"{d['type']:<8} "
            f"{d['severity']:<8} "
            f"{len(d_chunks)}"
        )

    print("-" * 80)
    print(f"Total diseases: {len(DISEASES)}")
    print(f"Total chunks: {len(chunks)}")
    print(f"  Parents: {sum(1 for c in chunks if c['metadata']['chunk_type'] == 'parent')}")
    print(f"  Children: {sum(1 for c in chunks if c['metadata']['chunk_type'] == 'child')}")

    crops = sorted({d["crop"] for d in DISEASES})
    print(f"\nCrops covered: {', '.join(crops)}")

    by_crop = {}
    for d in DISEASES:
        by_crop.setdefault(d["crop"], []).append(d["disease_name"])
    print("\nNew diseases by crop:")
    for crop, names in sorted(by_crop.items()):
        print(f"  {crop}: {len(names)} ({', '.join(names)})")


if __name__ == "__main__":
    main()
