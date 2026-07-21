/**
 * WebAudio click. Synthesised rather than shipped as an asset so the kiosk
 * has no extra file to load.
 *
 * The AudioContext is created lazily on the first gesture — browsers refuse to
 * start one before a user interaction.
 */

let ctx: AudioContext | null = null;

function context(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  if (!ctx) {
    const Ctor = window.AudioContext ?? (window as never as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
  }
  if (ctx.state === 'suspended') void ctx.resume();
  return ctx;
}

function blip(frequency: number, duration: number, peak: number) {
  const audio = context();
  if (!audio) return;

  const osc = audio.createOscillator();
  const gain = audio.createGain();
  const now = audio.currentTime;

  osc.type = 'sine';
  osc.frequency.setValueAtTime(frequency, now);

  // Fast attack, exponential decay — a tick, not a beep.
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(peak, now + 0.008);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

  osc.connect(gain).connect(audio.destination);
  osc.start(now);
  osc.stop(now + duration + 0.02);
}

/** Tile press. */
export const click = () => blip(880, 0.06, 0.08);

/** Action succeeded. */
export const success = () => blip(1320, 0.09, 0.06);

/** Action failed. */
export const failure = () => blip(220, 0.16, 0.09);

/** Entering wiggle mode. */
export const enterEdit = () => blip(660, 0.1, 0.05);
