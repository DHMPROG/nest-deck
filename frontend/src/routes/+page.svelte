<script lang="ts">
  /**
   * Deck kiosk view — 1280x800, no scroll, touch only.
   *
   * Header (80px) · grid (flex) · status bar (60px).
   */
  import { onMount, onDestroy } from 'svelte';
  import { fade } from 'svelte/transition';
  import HeartbeatKeepAlive from '$lib/components/deck/HeartbeatKeepAlive.svelte';
  import PageTabs from '$lib/components/deck/PageTabs.svelte';
  import StatusBar from '$lib/components/deck/StatusBar.svelte';
  import TileGrid from '$lib/components/deck/TileGrid.svelte';
  import { deck } from '$lib/stores/profile.svelte';
  import { editMode } from '$lib/stores/editMode.svelte';
  import { categoryPalette, tokens } from '$lib/theme';

  let clock = $state(formatTime(new Date()));
  let showProfiles = $state(false);

  const palette = $derived(categoryPalette(deck.activePage?.color));

  function formatTime(date: Date): string {
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }

  let timer: ReturnType<typeof setInterval>;

  let disconnectLive: (() => void) | null = null;

  onMount(() => {
    timer = setInterval(() => (clock = formatTime(new Date())), 1000);
    void deck.load();
    // Live sync: an edit in the Editor lands here without a reload.
    disconnectLive = deck.connectLive();
  });

  onDestroy(() => {
    clearInterval(timer);
    disconnectLive?.();
  });

  /**
   * Tapping genuinely empty space leaves wiggle mode (iOS behaviour).
   *
   * `pointerup` bubbles, so we must ignore releases that land on a tile or any
   * control — otherwise the very release that ends the 500ms long press would
   * turn edit mode straight back off.
   */
  function onBackgroundPointerUp(event: PointerEvent) {
    if (!editMode.active) return;
    const target = event.target as HTMLElement | null;
    if (target?.closest('button, a, input')) return;
    editMode.exit();
  }

  function onKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') editMode.exit();
    if (event.key === 'ArrowRight') void deck.nextPage();
    if (event.key === 'ArrowLeft') void deck.previousPage();
  }
</script>

<svelte:head><title>Nest Deck</title></svelte:head>
<svelte:window onkeydown={onKeydown} />

<HeartbeatKeepAlive />

<!-- Tapping the background leaves wiggle mode; Escape does the same for
     keyboard users, so this handler is a touch convenience only. -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="kiosk flex h-screen w-screen flex-col overflow-hidden"
  onpointerup={onBackgroundPointerUp}
>
  <!-- Header --------------------------------------------------------------- -->
  <header class="flex h-20 shrink-0 items-center justify-between px-page">
    <div class="relative flex min-w-0 items-center gap-3">
      <button
        type="button"
        class="flex h-11 min-w-11 items-center gap-3 rounded-pill pr-4"
        onpointerup={(e) => {
          e.stopPropagation();
          showProfiles = !showProfiles;
        }}
        aria-haspopup="menu"
        aria-expanded={showProfiles}
      >
        <span
          class="grid size-11 shrink-0 place-items-center rounded-pill"
          style="background: {palette.bg}; color: {palette.accentDeep}"
        >
          <i class="ph ph-{deck.profile?.icon ?? 'house'} text-2xl" aria-hidden="true"></i>
        </span>
        <span class="truncate text-page-heading">{deck.profile?.name ?? '—'}</span>
      </button>

      {#if showProfiles}
        <ul
          class="absolute top-14 left-0 z-20 flex min-w-56 flex-col gap-1 rounded-container bg-app-surface p-2 shadow-hover"
          transition:fade={{ duration: 120 }}
          role="menu"
        >
          {#each deck.profiles as candidate (candidate.id)}
            <li>
              <button
                type="button"
                class="flex h-11 w-full items-center gap-3 rounded-2xl px-3 text-left text-body"
                style={candidate.active ? `background: ${palette.bg}; color: ${palette.text}` : ''}
                onpointerup={(e) => {
                  e.stopPropagation();
                  showProfiles = false;
                  if (!candidate.active) void deck.activateProfile(candidate.id);
                }}
                role="menuitem"
              >
                <i class="ph ph-{candidate.icon}" aria-hidden="true"></i>
                <span class="truncate">{candidate.name}</span>
                {#if candidate.active}
                  <i class="ph ph-check ml-auto" aria-hidden="true"></i>
                {/if}
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    </div>

    <PageTabs />

    <div class="flex items-center gap-3">
      {#if editMode.active}
        <!-- Save and leave wiggle mode. -->
        <button
          type="button"
          class="flex h-11 items-center gap-2 rounded-pill px-4 text-label"
          style="background: {palette.accent}; color: white"
          onpointerup={(e) => {
            e.stopPropagation();
            editMode.exit();
          }}
        >
          <i class="ph ph-x" aria-hidden="true"></i>
          <span>Terminé</span>
        </button>
      {:else}
        <span
          class="size-2.5 rounded-pill"
          style="background: {deck.online ? tokens.category.meeting.accent : tokens.category.stream.accent}"
          title={deck.online ? 'backend en ligne' : 'backend hors ligne'}
        ></span>
        <span class="tabular-nums text-page-heading">{clock}</span>
      {/if}
    </div>
  </header>

  <!-- Grid ----------------------------------------------------------------- -->
  <TileGrid />

  <!-- Status bar ------------------------------------------------------------ -->
  <StatusBar />
</div>

<!-- Editor shortcut for the desktop admin. -->
<a
  href="/editor"
  target="_blank"
  rel="noopener"
  class="fixed right-3 bottom-3 grid size-11 place-items-center rounded-pill text-app-muted opacity-40"
  aria-label="Ouvrir l'éditeur"
>
  <i class="ph ph-gear text-xl" aria-hidden="true"></i>
</a>
