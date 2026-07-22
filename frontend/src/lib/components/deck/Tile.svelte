<script lang="ts">
  import { Spring } from 'svelte/motion';
  import { api } from '$lib/services/api';
  import * as sound from '$lib/services/sound';
  import { editMode } from '$lib/stores/editMode.svelte';
  import { status } from '$lib/stores/status.svelte';
  import { tileIcon, tileLabel } from '$lib/types';
  import type { TileSlot } from '$lib/types';
  import type { tokens } from '$lib/theme';

  interface Props {
    slot: TileSlot;
    index: number;
    palette: (typeof tokens)['category'][keyof (typeof tokens)['category']];
    /** Edit mode: the ✕ badge was tapped. */
    onremove?: (slot: TileSlot) => void;
    /** An empty slot was tapped: pick the action that fills it. */
    onchoose?: (slot: TileSlot) => void;
    /** Denser grid: shrink the icon and text so a 6x6 stays legible. */
    compact?: boolean;
  }

  let { slot, index, palette, onremove, onchoose, compact = false }: Props = $props();

  type Phase = 'idle' | 'pending' | 'ok' | 'error';
  let phase = $state<Phase>('idle');

  const LONG_PRESS_MS = 500;
  const MOVE_TOLERANCE = 12;

  const reduced =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Spec: scale to 0.94 on press, back to 1 on release.
  const scale = new Spring(1, { stiffness: 0.4, damping: 0.25 });

  let holdTimer: ReturnType<typeof setTimeout> | null = null;
  let start = { x: 0, y: 0 };
  let moved = false;

  function press(event: PointerEvent) {
    moved = false;
    start = { x: event.clientX, y: event.clientY };
    if (!reduced) scale.target = 0.94;

    holdTimer = setTimeout(() => {
      holdTimer = null;
      if (moved) return;
      sound.enterEdit();
      editMode.enter();
    }, LONG_PRESS_MS);
  }

  function track(event: PointerEvent) {
    if (moved) return;
    const dx = Math.abs(event.clientX - start.x);
    const dy = Math.abs(event.clientY - start.y);
    if (dx > MOVE_TOLERANCE || dy > MOVE_TOLERANCE) {
      // A swipe or a drag — not a tap.
      moved = true;
      cancelHold();
      scale.target = 1;
    }
  }

  function cancelHold() {
    if (holdTimer) clearTimeout(holdTimer);
    holdTimer = null;
  }

  function release() {
    // `holdTimer` is still pending on a quick tap, and null once the 500ms
    // long press has already fired.
    const wasTap = holdTimer !== null;
    cancelHold();
    scale.target = 1;
    if (moved) return;

    if (!slot.tile) {
      // Adding is a normal action — no need to be in edit mode first.
      if (wasTap) onchoose?.(slot);
      return;
    }

    // On a filled tile, edit mode means dragging and the ✕ badge. Changing what
    // a tile does is an Editor job — the Hub has no keyboard to configure one.
    if (editMode.active) return;
    if (wasTap) void fire();
  }

  function abort() {
    cancelHold();
    scale.target = 1;
  }

  function remove(event: PointerEvent) {
    // Must not bubble: the background handler would leave edit mode.
    event.stopPropagation();
    onremove?.(slot);
  }

  /** A quick overshoot-and-settle pop, so a success feels physically confirmed. */
  function pop() {
    if (reduced) return;
    scale.set(1.06, { instant: true });
    scale.target = 1;
  }

  async function fire() {
    const tile = slot.tile;
    if (!tile || phase === 'pending') return;

    sound.click();
    phase = 'pending';
    // Stay pressed in while the action is in flight — the held button *is* the
    // "sending" indicator, so there's no spinner loop.
    if (!reduced) scale.target = 0.96;
    const label = tileLabel(slot.tile);

    try {
      const result = await api.fire(tile.id);
      phase = result.status === 'ok' ? 'ok' : 'error';
      status.report(label, result.message, result.status === 'ok' ? 'ok' : 'error');
      if (result.status === 'ok') {
        sound.success();
        pop();
      } else {
        sound.failure();
        if (!reduced) scale.target = 1;
      }
    } catch (cause) {
      phase = 'error';
      status.report(label, cause instanceof Error ? cause.message : 'failed', 'error');
      sound.failure();
      if (!reduced) scale.target = 1;
    }

    setTimeout(() => (phase = 'idle'), 420);
  }
</script>

<!-- The cell is the unit svelte-dnd-action drags, so the ✕ badge travels with
     the tile instead of being left behind. -->
<div
  class="cell tile-in"
  class:wiggle={editMode.active}
  class:compact
  style="--i: {index}; --bg: {palette.bg}; --text: {palette.text}; --accent: {palette.accent}; --accent-deep: {palette.accentDeep}"
>
  {#if slot.tile}
    <button
      type="button"
      class="tile"
      class:is-ok={phase === 'ok'}
      class:is-error={phase === 'error'}
      class:is-pending={phase === 'pending'}
      style="transform: scale({scale.current})"
      onpointerdown={press}
      onpointermove={track}
      onpointerup={release}
      onpointercancel={abort}
      onpointerleave={abort}
      aria-label={tileLabel(slot.tile)}
    >
      <i class="ph-duotone ph-{tileIcon(slot.tile)} icon" aria-hidden="true"></i>
      <span class="text-tile-title">{tileLabel(slot.tile)}</span>
      <span class="text-tile-subtitle subtitle">{slot.tile.action?.type ?? ''}</span>
    </button>

    {#if editMode.active}
      <button
        type="button"
        class="badge"
        onpointerup={remove}
        aria-label="Retirer {tileLabel(slot.tile)}"
      >
        <i class="ph ph-x" aria-hidden="true"></i>
      </button>
    {/if}
  {:else}
    <button
      type="button"
      class="empty"
      class:addable={editMode.active}
      style="transform: scale({scale.current})"
      onpointerdown={press}
      onpointermove={track}
      onpointerup={release}
      onpointercancel={abort}
      onpointerleave={abort}
      aria-label="Ajouter une action"
    >
      <i class="ph ph-plus text-4xl" aria-hidden="true"></i>
    </button>
  {/if}
</div>

<style>
  .cell {
    position: relative;
    min-width: 0;
    min-height: 0;
    /* Stops the browser claiming the gesture before we classify it. */
    touch-action: none;
  }

  .tile,
  .empty {
    width: 100%;
    height: 100%;
    border-radius: var(--radius-tile, 24px);
    touch-action: none;
  }

  .tile {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0 0.75rem;
    text-align: center;
    background: var(--bg);
    color: var(--text);
    box-shadow:
      0 1px 2px rgb(0 0 0 / 0.06),
      0 4px 12px rgb(0 0 0 / 0.06);
    cursor: pointer;
    /* Shadow eases with the press; the scale itself is spring-driven in JS. */
    transition: box-shadow 140ms ease;
  }

  /* Held while an action is in flight: a real pressed-in button, no spinner. */
  .tile.is-pending {
    box-shadow: inset 0 2px 5px rgb(0 0 0 / 0.14);
  }
  .tile.is-pending .icon {
    opacity: 0.5;
    transition: opacity 120ms ease;
  }

  .icon {
    font-size: 64px;
    line-height: 1;
    color: var(--accent-deep);
  }

  /* 6x6 leaves roughly half the height per tile, so scale the contents down
     rather than letting the icon push the label out. */
  .compact .icon {
    font-size: 40px;
  }

  .compact .tile {
    gap: 0.25rem;
  }

  .compact :global(.text-tile-title) {
    font-size: 14px;
  }

  .compact .subtitle {
    display: none;
  }

  .subtitle {
    color: color-mix(in srgb, var(--text) 55%, transparent);
  }

  /* Tappable at all times — adding an action does not require edit mode. Kept
     visually quiet so a full page still reads as the primary content. */
  .empty {
    display: grid;
    place-items: center;
    border: 2px dashed color-mix(in srgb, var(--accent) 25%, transparent);
    color: var(--muted);
    opacity: 0.55;
    cursor: pointer;
  }

  .empty.addable {
    opacity: 1;
    border-style: solid;
    border-color: var(--accent);
    color: var(--accent-deep);
    background: var(--bg);
    cursor: pointer;
  }

  /* Delete badge, iOS-style, hanging off the top-left corner. */
  .badge {
    position: absolute;
    top: -8px;
    left: -8px;
    z-index: 2;
    display: grid;
    place-items: center;
    /* 32px visual, but the tap area is padded out to 44px below. */
    width: 32px;
    height: 32px;
    border-radius: 999px;
    background: #1c1c1e;
    color: #fff;
    font-size: 16px;
    box-shadow: 0 2px 6px rgb(0 0 0 / 0.3);
    cursor: pointer;
  }

  /* Meets the 44x44 minimum touch target without growing the visible dot. */
  .badge::after {
    content: '';
    position: absolute;
    inset: -6px;
    border-radius: 999px;
  }

  /* Success: a green ring blooms out once. */
  .is-ok {
    animation: ring-ok 420ms ease-out;
  }
  @keyframes ring-ok {
    from {
      box-shadow: 0 0 0 0 rgb(52 199 89 / 0.85);
    }
    to {
      box-shadow: 0 0 0 14px rgb(52 199 89 / 0);
    }
  }

  /* Error: a tight, damped shake with a red ring. */
  .is-error {
    animation: shake 380ms cubic-bezier(0.36, 0.07, 0.19, 0.97);
    box-shadow: 0 0 0 3px rgb(255 59 48 / 0.55);
  }
  @keyframes shake {
    0%,
    100% {
      translate: 0;
    }
    15% {
      translate: -5px;
    }
    30% {
      translate: 5px;
    }
    45% {
      translate: -3px;
    }
    60% {
      translate: 3px;
    }
    75% {
      translate: -1px;
    }
  }

  /* Edit mode wiggle. Kept — it's how the Hub signals "editable" — but each
     tile is phase-shifted by its index so the grid jiggles organically rather
     than in lockstep, and it eases smoothly. */
  .wiggle {
    animation: wiggle 260ms ease-in-out infinite alternate;
    animation-delay: calc(var(--i, 0) * -47ms);
  }
  @keyframes wiggle {
    from {
      rotate: -0.9deg;
      translate: 0 -0.5px;
    }
    to {
      rotate: 0.9deg;
      translate: 0 0.5px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .is-ok,
    .is-error,
    .wiggle {
      animation: none !important;
    }
    .is-error {
      box-shadow: 0 0 0 3px rgb(255 59 48 / 0.55);
    }
  }
</style>
