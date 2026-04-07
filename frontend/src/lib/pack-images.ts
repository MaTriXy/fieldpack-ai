/** Maps known pack IDs to their bundled cover images. */
const PACK_COVERS: Record<string, { card: string; hero: string }> = {
  casamance_agriculture: {
    card: '/images/packs/casamance-farming.jpg',
    hero: '/images/packs/casamance-landscape.jpg',
  },
}

/** Fallback images for packs without a known cover. */
const DEFAULT_IMAGES = [
  '/images/packs/default-1.jpg',
  '/images/packs/default-2.jpg',
  '/images/packs/default-3.jpg',
  '/images/packs/default-4.jpg',
  '/images/packs/default-5.jpg',
]

/** Simple hash of a string to pick a stable fallback index. */
function stableHash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

/** Get the card thumbnail image for a pack. */
export function getPackCardImage(packId: string): string {
  return PACK_COVERS[packId]?.card ?? DEFAULT_IMAGES[stableHash(packId) % DEFAULT_IMAGES.length]
}

/** Get the hero banner image for a pack. */
export function getPackHeroImage(packId: string): string {
  return PACK_COVERS[packId]?.hero ?? DEFAULT_IMAGES[stableHash(packId) % DEFAULT_IMAGES.length]
}
