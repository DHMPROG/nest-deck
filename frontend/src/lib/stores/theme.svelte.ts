/**
 * Light / dark theme, driven by `data-theme` on <html> and persisted so it
 * sticks across reloads (and the 9-minute Deck refresh). Falls back to the OS
 * preference the first time.
 */

type Mode = 'light' | 'dark';

const KEY = 'nest-deck-theme';

class Theme {
  mode = $state<Mode>('light');

  /** Read the saved (or OS) preference and apply it. Call once on mount. */
  init() {
    if (typeof window === 'undefined') return;
    const saved = localStorage.getItem(KEY) as Mode | null;
    this.mode =
      saved ??
      (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    this.#apply();
  }

  toggle() {
    this.mode = this.mode === 'dark' ? 'light' : 'dark';
    if (typeof window !== 'undefined') localStorage.setItem(KEY, this.mode);
    this.#apply();
  }

  #apply() {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', this.mode);
    }
  }
}

export const theme = new Theme();
