/**
 * Status bar feedback. Holds the last action result and fades back to the
 * ambient (clock / wifi) state after 2.5s.
 */

export type Tone = 'ok' | 'error';

export interface Toast {
  id: number;
  text: string;
  tone: Tone;
}

const LINGER_MS = 2500;

class StatusState {
  current = $state<Toast | null>(null);

  #seq = 0;
  #timer: ReturnType<typeof setTimeout> | null = null;

  show(text: string, tone: Tone) {
    if (this.#timer) clearTimeout(this.#timer);
    this.current = { id: ++this.#seq, text, tone };
    this.#timer = setTimeout(() => {
      this.current = null;
      this.#timer = null;
    }, LINGER_MS);
  }

  /** "Go Live · sent" / "OBS · offline" */
  report(label: string, message: string, tone: Tone) {
    this.show(`${label} · ${message}`, tone);
  }

  clear() {
    if (this.#timer) clearTimeout(this.#timer);
    this.#timer = null;
    this.current = null;
  }
}

export const status = new StatusState();
