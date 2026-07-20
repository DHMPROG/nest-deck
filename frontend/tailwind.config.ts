import type { Config } from 'tailwindcss';
import { tokens } from './src/lib/theme';

/**
 * Tailwind 4 loads this via `@config` in `app.css`. Every colour here is
 * derived from `theme.ts` — never hardcode a hex in this file.
 *
 * Each category exposes `DEFAULT` (the pastel background) plus `accent`,
 * `accentDeep` and `text`, which yields `bg-cat-stream`,
 * `text-cat-stream-accent`, `border-cat-games-accent-deep`, etc.
 */
const category = Object.fromEntries(
  Object.entries(tokens.category).map(([name, palette]) => [
    name,
    {
      DEFAULT: palette.bg,
      bg: palette.bg,
      accent: palette.accent,
      'accent-deep': palette.accentDeep,
      text: palette.text
    }
  ])
);

export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        cat: category,
        surface: {
          day: tokens.surface.bgDay,
          night: tokens.surface.bgNight,
          'tile-day': tokens.surface.tileDay,
          'tile-night': tokens.surface.tileNight,
          'text-day': tokens.surface.textDay,
          'text-night': tokens.surface.textNight,
          muted: tokens.surface.muted
        }
      },
      boxShadow: {
        rest: tokens.shadow.rest,
        hover: tokens.shadow.hover,
        pressed: tokens.shadow.pressed
      },
      borderRadius: {
        tile: tokens.radius.tile,
        container: tokens.radius.container,
        pill: tokens.radius.pill
      },
      fontFamily: {
        sans: ['Manrope Variable', 'Manrope', 'system-ui', 'sans-serif']
      },
      fontSize: {
        // Type scale from the spec.
        'tile-title': ['18px', { lineHeight: '1.25', fontWeight: '700' }],
        'tile-subtitle': ['13px', { lineHeight: '1.3', fontWeight: '500' }],
        'page-heading': ['22px', { lineHeight: '1.25', fontWeight: '700' }],
        body: ['15px', { lineHeight: '1.5', fontWeight: '400' }],
        label: ['12px', { lineHeight: '1.4', fontWeight: '500' }]
      },
      spacing: {
        grid: '24px',
        page: '32px'
      }
    }
  }
} satisfies Config;
