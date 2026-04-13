/**
 * Shared agricultural facts shown during loading states.
 * Used by ThinkingBubble (field chat) and AgentProgressPage (mission pipeline).
 */

export interface FieldFact {
  icon: string
  text: string
}

export const FIELD_FACTS: FieldFact[] = [
  // Staple crops
  { icon: '🌾', text: 'Cassava feeds over 500 million people across Africa every day' },
  { icon: '🌽', text: 'Maize is the most widely grown crop in sub-Saharan Africa' },
  { icon: '🍚', text: 'West Africa produces over 19 million tonnes of rice per year' },
  { icon: '🥜', text: 'Groundnuts fix nitrogen in the soil, benefiting the next crop rotation' },
  { icon: '🫘', text: 'Cowpeas can grow in poor soils and tolerate drought better than most legumes' },
  { icon: '🍠', text: 'Orange-fleshed sweet potato is rich in vitamin A and grows in 3-4 months' },
  { icon: '🌾', text: 'Sorghum and millet can survive where rainfall is below 500mm per year' },
  { icon: '🫛', text: 'Pigeon pea roots can break through compacted soil layers up to 2 meters deep' },
  // Soil & water
  { icon: '🧪', text: 'You can test soil pH with litmus strips from any pharmacy' },
  { icon: '💧', text: 'Mulching with crop residues can reduce water evaporation by up to 70%' },
  { icon: '🌱', text: 'Intercropping legumes with cereals naturally adds nitrogen to the soil' },
  { icon: '🌿', text: 'Cover crops reduce soil erosion by up to 90% during heavy rains' },
  { icon: '🪨', text: 'Contour stone bunds slow rainwater runoff and reduce erosion on slopes' },
  { icon: '💧', text: 'Half-moon water harvesting pits can triple millet yields in the Sahel' },
  { icon: '🧱', text: 'Zai pits \u2014 small planting holes with compost \u2014 restore degraded Sahel land' },
  // Pests & disease
  { icon: '🐛', text: 'Neem leaf extract is a natural pesticide used across West Africa' },
  { icon: '🐔', text: 'Free-range chickens can eat up to 80 armyworms per hour in maize fields' },
  { icon: '🦗', text: 'A single healthy bat can eat up to 1,000 mosquitoes per hour' },
  { icon: '🍅', text: 'You can test for tomato bacterial wilt by placing a cut stem in clear water' },
  { icon: '🐜', text: 'Push-pull farming uses Napier grass to trap stem borers away from maize' },
  { icon: '🌼', text: 'Planting marigolds between vegetable rows repels root-knot nematodes' },
  { icon: '🦟', text: 'Rice paddies with alternating wet-dry cycles reduce mosquito breeding by 60%' },
  { icon: '🪲', text: 'Lady beetles are natural aphid predators \u2014 one can eat 50 aphids a day' },
  // Post-harvest & storage
  { icon: '🌡️', text: 'Grain stored above 14% moisture can develop dangerous aflatoxin mould' },
  { icon: '☀️', text: 'Solar drying on raised racks prevents grain spoilage after harvest' },
  { icon: '🏺', text: 'Hermetic (airtight) grain bags can protect stored grain without chemicals' },
  { icon: '🧂', text: 'Mixing wood ash into stored beans repels weevils naturally' },
  { icon: '📦', text: 'Africa loses up to 40% of harvested food due to poor post-harvest handling' },
  // Climate & seasons
  { icon: '🌍', text: 'The Sahel rainy season has shifted later by 2-3 weeks over the past 30 years' },
  { icon: '🌧️', text: 'Most of West Africa receives 80% of its annual rainfall in just 4 months' },
  { icon: '🌤️', text: 'Agroforestry trees provide shade that can lower soil temperature by 5-8\u00B0C' },
  { icon: '🌊', text: 'Mangrove restoration in coastal West Africa protects rice paddies from salt intrusion' },
  // Techniques & innovation
  { icon: '🐄', text: 'Composting cow manure for 3 weeks kills most weed seeds and pathogens' },
  { icon: '🐟', text: 'Rice-fish farming in flooded paddies provides protein and controls weeds' },
  { icon: '🌳', text: 'Farmer-managed natural regeneration has re-greened 5 million hectares in the Sahel' },
  { icon: '🐝', text: 'Beehive fences in East Africa protect farms from elephants and produce honey' },
  { icon: '🧑\u200D🌾', text: 'Seed fairs help farmers access diverse local varieties adapted to their climate' },
  { icon: '🔬', text: 'Simple seed float tests \u2014 discard seeds that float \u2014 improve germination rates' },
  { icon: '🪴', text: 'Grafting local rootstock with improved varieties gives disease resistance and better yield' },
  { icon: '🐐', text: 'Integrating small ruminants with crops turns crop residues into manure and income' },
]
