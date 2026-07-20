/**
 * Design tokens — the single source of truth for colour in this app.
 *
 * No hex literal may appear anywhere else in the codebase: `tailwind.config.ts`
 * imports this file and turns it into utilities (`bg-cat-stream`,
 * `text-cat-stream-accent`, `shadow-rest`, `rounded-tile`, ...).
 */

export const tokens = {
  category: {
    stream: { bg: '#FFE5E4', accent: '#FF3B30', accentDeep: '#C4271E', text: '#4A0F0A' },
    pc: { bg: '#E1F3FF', accent: '#007AFF', accentDeep: '#0051D5', text: '#0A2540' },
    games: { bg: '#FFE4F1', accent: '#FF2D92', accentDeep: '#C71F73', text: '#4A0E2C' },
    meeting: { bg: '#E3F9E9', accent: '#34C759', accentDeep: '#248A3D', text: '#0F3A1A' },
    media: { bg: '#F3E5FF', accent: '#AF52DE', accentDeep: '#7D2FA8', text: '#2E0F4A' }
  },
  surface: {
    bgDay: '#FAF9F7',
    bgNight: '#1C1C1E',
    tileDay: '#FFFFFF',
    tileNight: '#2C2C2E',
    textDay: '#1C1C1E',
    textNight: '#F2F2F7',
    muted: '#8E8E93'
  },
  shadow: {
    rest: '0 1px 2px rgb(0 0 0 / 0.06), 0 4px 12px rgb(0 0 0 / 0.06)',
    hover: '0 4px 12px rgb(0 0 0 / 0.08), 0 12px 32px rgb(0 0 0 / 0.08)',
    pressed: 'inset 0 2px 4px rgb(0 0 0 / 0.12)'
  },
  radius: { tile: '24px', container: '32px', pill: '999px' }
} as const;

/** The five semantic categories. Pages and categories both key off these. */
export type CategoryToken = keyof typeof tokens.category;

export const CATEGORY_TOKENS = Object.keys(tokens.category) as CategoryToken[];

/** Narrow an arbitrary backend string to a known token, falling back to `pc`. */
export function asCategoryToken(value: string | null | undefined): CategoryToken {
  return value !== null && value !== undefined && value in tokens.category
    ? (value as CategoryToken)
    : 'pc';
}

/** Palette for a category, safe against unknown values coming from the API. */
export function categoryPalette(value: string | null | undefined) {
  return tokens.category[asCategoryToken(value)];
}

/**
 * Grid geometry, mirrored from the backend (`models.GRID_ROWS` / `GRID_COLS`).
 * The Deck is always 5 columns x 3 rows on a 1280x800 panel.
 */
export const GRID = { rows: 3, cols: 5, slots: 15 } as const;
