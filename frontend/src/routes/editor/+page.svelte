<script lang="ts">
  /**
   * Editor admin view — phase 2 scaffold.
   *
   * Establishes the three-column shell and confirms the API client works from
   * this route too. Drag-and-drop placement, the tile modal and optimistic
   * mutations land in phase 4.
   */
  import { onMount } from 'svelte';
  import { api, ApiError } from '$lib/services/api';
  import { CATEGORY_TOKENS, categoryPalette, GRID } from '$lib/theme';
  import { tileIcon, tileLabel } from '$lib/types';
  import type { Action, Category, Page, Profile, TileSlot } from '$lib/types';

  let profiles = $state<Profile[]>([]);
  let profile = $state<Profile | null>(null);
  let pages = $state<Page[]>([]);
  let activePageId = $state<string | null>(null);
  let slots = $state<TileSlot[]>([]);
  let categories = $state<Category[]>([]);
  let actions = $state<Action[]>([]);
  let error = $state<string | null>(null);

  const activePage = $derived(pages.find((p) => p.id === activePageId) ?? null);
  // Catalog order follows the canonical token order (Stream, PC, Games,
  // Meeting, Media), not the backend's alphabetical sort.
  const byCategory = $derived(
    [...categories]
      .sort(
        (a, b) =>
          CATEGORY_TOKENS.indexOf(a.color as never) -
          CATEGORY_TOKENS.indexOf(b.color as never)
      )
      .map((c) => ({
        category: c,
        items: actions.filter((a) => a.category_id === c.id)
      }))
  );

  onMount(load);

  async function load() {
    try {
      profiles = await api.listProfiles();
      profile = profiles.find((p) => p.active) ?? profiles[0] ?? null;
      [categories, actions] = await Promise.all([
        api.listCategories(),
        api.listActions()
      ]);
      if (profile) {
        pages = await api.listPages(profile.id);
        activePageId = pages[0]?.id ?? null;
        if (activePageId) slots = await api.listTiles(activePageId);
      }
      error = null;
    } catch (cause) {
      error = cause instanceof ApiError ? cause.message : String(cause);
    }
  }

  async function selectPage(id: string) {
    activePageId = id;
    slots = await api.listTiles(id);
  }
</script>

<svelte:head><title>Nest Deck · Editor</title></svelte:head>

<div class="hidden h-screen place-items-center p-8 text-center max-[1023px]:grid">
  <p class="text-body text-surface-muted">
    L'éditeur nécessite une fenêtre d'au moins 1024px de large.
  </p>
</div>

<div class="grid h-screen grid-cols-[280px_1fr_320px] max-[1023px]:hidden">
  <!-- Left: profile + pages ---------------------------------------------- -->
  <aside class="flex flex-col gap-4 overflow-y-auto border-r border-black/5 p-5">
    <div class="flex items-center gap-3">
      <span class="grid size-11 place-items-center rounded-pill bg-cat-pc text-cat-pc-accent-deep">
        <i class="ph ph-{profile?.icon ?? 'house'} text-2xl" aria-hidden="true"></i>
      </span>
      <div class="min-w-0">
        <p class="truncate text-page-heading">{profile?.name ?? '—'}</p>
        <p class="text-label text-surface-muted">
          {profiles.length} profil{profiles.length > 1 ? 's' : ''}
        </p>
      </div>
    </div>

    <h2 class="text-label uppercase tracking-wide text-surface-muted">Pages</h2>
    <ul class="flex flex-col gap-1">
      {#each pages as page (page.id)}
        {@const pal = categoryPalette(page.color)}
        <li>
          <button
            type="button"
            onclick={() => selectPage(page.id)}
            class="flex h-11 w-full items-center gap-3 rounded-2xl px-3 text-left text-body transition-colors duration-150 hover:bg-black/5"
            style={page.id === activePageId ? `background: ${pal.bg}; color: ${pal.text}` : ''}
          >
            <span class="size-3 shrink-0 rounded-pill" style="background: {pal.accent}"></span>
            <span class="truncate">{page.name}</span>
          </button>
        </li>
      {/each}
    </ul>
  </aside>

  <!-- Center: editable grid ----------------------------------------------- -->
  <main class="flex min-w-0 flex-col gap-4 overflow-y-auto p-page">
    <header class="flex items-baseline justify-between">
      <h1 class="text-page-heading">{activePage?.name ?? 'Aucune page'}</h1>
      {#if error}
        <p class="text-label text-cat-stream-accent-deep">{error}</p>
      {/if}
    </header>

    <div
      class="grid aspect-[1280/660] w-full gap-grid rounded-container bg-black/[0.02] p-6"
      style="grid-template-columns: repeat({GRID.cols}, 1fr); grid-template-rows: repeat({GRID.rows}, 1fr)"
    >
      {#each slots as slot (`${slot.row}-${slot.col}`)}
        {@const pal = categoryPalette(activePage?.color)}
        {#if slot.tile}
          <div
            class="flex flex-col items-center justify-center gap-1 rounded-tile px-2 text-center shadow-rest"
            style="background: {pal.bg}; color: {pal.text}"
          >
            <i
              class="ph-duotone ph-{tileIcon(slot.tile)} text-3xl leading-none"
              style="color: {pal.accentDeep}"
              aria-hidden="true"
            ></i>
            <span class="text-label">{tileLabel(slot.tile)}</span>
          </div>
        {:else}
          <div class="grid place-items-center rounded-tile border-2 border-dashed border-black/10">
            <i class="ph ph-plus text-2xl text-surface-muted opacity-40" aria-hidden="true"></i>
          </div>
        {/if}
      {/each}
    </div>
  </main>

  <!-- Right: action catalog ------------------------------------------------ -->
  <aside class="flex flex-col gap-4 overflow-y-auto border-l border-black/5 p-5">
    <h2 class="text-label uppercase tracking-wide text-surface-muted">
      Catalogue · {actions.length} actions
    </h2>
    {#each byCategory as group (group.category.id)}
      {@const pal = categoryPalette(group.category.color)}
      <section class="flex flex-col gap-2">
        <h3 class="flex items-center gap-2 text-body font-semibold">
          <span class="size-3 rounded-pill" style="background: {pal.accent}"></span>
          {group.category.name}
        </h3>
        <ul class="flex flex-col gap-1">
          {#each group.items as action (action.id)}
            <li
              class="flex h-11 items-center gap-3 rounded-2xl px-3 text-body"
              style="background: {pal.bg}; color: {pal.text}"
            >
              <i class="ph-duotone ph-{action.icon} text-xl" aria-hidden="true"></i>
              <span class="truncate">{action.label}</span>
            </li>
          {/each}
        </ul>
      </section>
    {/each}
  </aside>
</div>
