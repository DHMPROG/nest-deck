<script lang="ts">
  /**
   * Deck kiosk view — phase 2 scaffold.
   *
   * Renders the real profile / pages / tiles from the backend so the API client
   * is exercised end to end. Tap-to-fire, long-press wiggle, drag reorder and
   * swipe between pages land in phase 3.
   */
  import { onMount, onDestroy } from 'svelte';
  import { api, ApiError } from '$lib/services/api';
  import { categoryPalette, GRID } from '$lib/theme';
  import { tileIcon, tileLabel } from '$lib/types';
  import type { Page, Profile, TileSlot } from '$lib/types';

  let profile = $state<Profile | null>(null);
  let pages = $state<Page[]>([]);
  let activePageId = $state<string | null>(null);
  let slots = $state<TileSlot[]>([]);
  let online = $state(false);
  let error = $state<string | null>(null);
  let clock = $state(formatTime(new Date()));

  const activePage = $derived(pages.find((p) => p.id === activePageId) ?? null);
  const palette = $derived(categoryPalette(activePage?.color));
  const filled = $derived(slots.filter((s) => s.tile).length);

  function formatTime(date: Date): string {
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }

  let timer: ReturnType<typeof setInterval>;

  onMount(async () => {
    timer = setInterval(() => (clock = formatTime(new Date())), 1000);
    await load();
  });

  onDestroy(() => clearInterval(timer));

  async function load() {
    try {
      const profiles = await api.listProfiles();
      profile = profiles.find((p) => p.active) ?? profiles[0] ?? null;
      if (!profile) {
        error = 'no profile on the backend';
        online = true;
        return;
      }
      pages = await api.listPages(profile.id);
      activePageId = pages[0]?.id ?? null;
      if (activePageId) slots = await api.listTiles(activePageId);
      online = true;
      error = null;
    } catch (cause) {
      online = false;
      error = cause instanceof ApiError ? cause.message : String(cause);
    }
  }

  async function selectPage(id: string) {
    activePageId = id;
    try {
      slots = await api.listTiles(id);
      error = null;
    } catch (cause) {
      error = cause instanceof ApiError ? cause.message : String(cause);
    }
  }
</script>

<svelte:head><title>Nest Deck</title></svelte:head>

<div
  class="kiosk flex h-screen w-screen flex-col overflow-hidden"
  style="--accent: {palette.accent}; --accent-deep: {palette.accentDeep}; --cat-bg: {palette.bg}; --cat-text: {palette.text}"
>
  <!-- Header ------------------------------------------------------------- -->
  <header class="flex h-20 shrink-0 items-center justify-between px-page">
    <div class="flex min-w-0 items-center gap-3">
      <span
        class="grid size-11 place-items-center rounded-pill"
        style="background: var(--cat-bg); color: var(--accent-deep)"
      >
        <i class="ph ph-{profile?.icon ?? 'house'} text-2xl" aria-hidden="true"></i>
      </span>
      <span class="truncate text-page-heading">{profile?.name ?? '—'}</span>
    </div>

    <nav class="flex items-center gap-2" aria-label="Pages">
      {#each pages as page (page.id)}
        {@const pal = categoryPalette(page.color)}
        {@const isActive = page.id === activePageId}
        <button
          type="button"
          onclick={() => selectPage(page.id)}
          aria-current={isActive ? 'page' : undefined}
          class="flex h-11 min-w-11 items-center gap-2 rounded-pill border-2 px-4 text-label transition-[background-color,border-color,color] duration-200"
          style="
            border-color: {isActive ? pal.accent : 'transparent'};
            background: {isActive ? pal.bg : 'transparent'};
            color: {isActive ? pal.text : 'var(--muted, #8E8E93)'}"
        >
          <i class="ph ph-{page.icon} text-lg" aria-hidden="true"></i>
          <span>{page.name}</span>
        </button>
      {/each}
    </nav>

    <div class="flex items-center gap-3 text-surface-muted">
      <span
        class="size-2.5 rounded-pill"
        style="background: {online ? '#34C759' : '#FF3B30'}"
        title={online ? 'backend online' : 'backend offline'}
      ></span>
      <span class="tabular-nums text-page-heading text-surface-text-day">{clock}</span>
    </div>
  </header>

  <!-- Grid --------------------------------------------------------------- -->
  <main
    class="grid min-h-0 flex-1 gap-grid px-page"
    style="grid-template-columns: repeat({GRID.cols}, 1fr); grid-template-rows: repeat({GRID.rows}, 1fr)"
  >
    {#each slots as slot, i (`${slot.row}-${slot.col}`)}
      {#if slot.tile}
        <div
          class="tile-in flex flex-col items-center justify-center gap-2 rounded-tile px-3 text-center shadow-rest"
          style="--i: {i}; background: var(--cat-bg); color: var(--cat-text)"
        >
          <i
            class="ph-duotone ph-{tileIcon(slot.tile)} text-[64px] leading-none"
            style="color: var(--accent-deep)"
            aria-hidden="true"
          ></i>
          <span class="text-tile-title">{tileLabel(slot.tile)}</span>
          <span class="text-tile-subtitle text-surface-muted"
            >{slot.tile.action?.type ?? ''}</span
          >
        </div>
      {:else}
        <div
          class="tile-in grid place-items-center rounded-tile border-2 border-dashed"
          style="--i: {i}; border-color: color-mix(in srgb, var(--accent) 25%, transparent)"
        >
          <i
            class="ph ph-plus text-4xl text-surface-muted opacity-40"
            aria-hidden="true"
          ></i>
        </div>
      {/if}
    {/each}
  </main>

  <!-- Status bar --------------------------------------------------------- -->
  <footer class="flex h-[60px] shrink-0 items-center justify-center">
    <p
      class="flex h-10 items-center gap-2 rounded-pill px-5 text-label shadow-rest"
      style="background: {error ? '#FFE5E4' : 'var(--cat-bg)'}; color: {error
        ? '#C4271E'
        : 'var(--cat-text)'}"
    >
      {#if error}
        <i class="ph ph-warning-circle" aria-hidden="true"></i>
        <span>{error}</span>
      {:else}
        <i class="ph ph-check-circle" aria-hidden="true"></i>
        <span>{activePage?.name ?? '—'} · {filled}/{GRID.slots} tuiles</span>
      {/if}
    </p>
  </footer>
</div>
