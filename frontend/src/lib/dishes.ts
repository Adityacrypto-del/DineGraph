// Photos for the dishes on the default menu (Unsplash, served with CORS so the
// morph gallery can upload them to WebGL). Dishes added by staff fall back to a
// general food photo.

const unsplash = (id: string, w: number, h: number) =>
  `https://images.unsplash.com/photo-${id}?w=${w}&h=${h}&q=80&auto=format&fit=crop`;

const PHOTOS: Record<string, string> = {
  "margherita pizza": "1574071318508-1cdbab80d002",
  "paneer butter masala": "1631452180519-c014fe946bc7",
  "veg biryani": "1589302168068-964664d93dc0",
  "chicken burger": "1568901346375-23c9450c58cd",
  "pasta alfredo": "1645112411341-6c4fd023714a",
  "masala dosa": "1668236543090-82eba5ee5976",
  "gulab jamun": "1666190092159-3171cf0fbb12",
  "cold coffee": "1461023058943-07fcbe16d735",
};

const FALLBACKS = [
  "1504674900247-0877df9cc836",
  "1540189549336-e6e99c3679fe",
  "1555939594-58d7cb561ad1",
  "1512621776951-a57141f2eefd",
  "1546069901-ba9599a7e63c",
];

function photoId(dish: string) {
  const key = dish.trim().toLowerCase();
  if (PHOTOS[key]) return PHOTOS[key];
  let hash = 0;
  for (const c of key) hash = (hash * 31 + c.charCodeAt(0)) | 0;
  return FALLBACKS[Math.abs(hash) % FALLBACKS.length];
}

export const dishPhoto = (dish: string, w = 1400, h = 900) => unsplash(photoId(dish), w, h);
export const dishThumb = (dish: string) => unsplash(photoId(dish), 160, 120);

// Extra kitchen and table shots that pad out the hero corridor.
export const AMBIENT_PHOTOS = [
  "1414235077428-338989a2e8c0",
  "1556910103-1c02745aae4d",
  "1565557623262-b51c2513a641",
  "1517248135467-4c7edcad34c4",
  "1585937421612-70a008356fbe",
  "1563379091339-03b21ab4a4f8",
].map((id) => unsplash(id, 540, 750));

export const PORTRAIT = (dish: string) => unsplash(photoId(dish), 540, 750);

// Wide room and kitchen shots for the page banners.
const SCENES = {
  dining: "1414235077428-338989a2e8c0",
  kitchen: "1556910103-1c02745aae4d",
  room: "1517248135467-4c7edcad34c4",
  plates: "1565557623262-b51c2513a641",
};
export type Scene = keyof typeof SCENES;
export const scenePhoto = (scene: Scene, w = 1800, h = 720) => unsplash(SCENES[scene], w, h);
