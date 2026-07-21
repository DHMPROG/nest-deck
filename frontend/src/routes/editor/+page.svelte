<script lang="ts">
  /**
   * Editor admin view — three columns, desktop only (min 1024px).
   *
   * Every edit is optimistic and persisted immediately; there is no save
   * button. Each mutation also pushes an inverse onto a 5-deep undo stack.
   */
  import { onDestroy, onMount } from 'svelte';
  import ActionCatalog from '$lib/components/editor/ActionCatalog.svelte';
  import ActionEditorModal from '$lib/components/editor/ActionEditorModal.svelte';
  import EditableGrid from '$lib/components/editor/EditableGrid.svelte';
  import PageList from '$lib/components/editor/PageList.svelte';
  import ProfileSwitcher from '$lib/components/editor/ProfileSwitcher.svelte';
  import TileEditorModal from '$lib/components/editor/TileEditorModal.svelte';
  import { api, ApiError } from '$lib/services/api';
  import { subscribeToEvents } from '$lib/services/sse';
  import { CATEGORY_TOKENS, categoryPalette, tokens } from '$lib/theme';
  import type { Action, Category, Page, Profile, TileSlot } from '$lib/types';

  let profiles = $state<Profile[]>([]);
  let profile = $state<Profile | null>(null);
  let pages = $state<Page[]>([]);
  let activePageId = $state<string | null>(null);
  let slots = $state<TileSlot[]>([]);
  let categories = $state<Category[]>([]);
  let actions = $state<Action[]>([]);

  let editingSlot = $state<TileSlot | null>(null);
  let livePreview = $state(false);
  let error = $state<string | null>(null);
  let notice = $state<string | null>(null);
  let importInput: HTMLInputElement | null = $state(null);

  const activePage = $derived(pages.find((p) => p.id === activePageId) ?? null);

  // -- undo ------------------------------------------------------------------
  interface UndoEntry {
    label: string;
    run: () => Promise<void>;
  }
  let undoStack = $state<UndoEntry[]>([]);

  function pushUndo(label: string, run: () => Promise<void>) {
    undoStack = [...undoStack, { label, run }].slice(-5);
  }

  async function undo() {
    const entry = undoStack.at(-1);
    if (!entry) return;
    undoStack = undoStack.slice(0, -1);
    await entry.run();
    flash(`Annulé : ${entry.label}`);
  }

  function flash(message: string) {
    notice = message;
    setTimeout(() => (notice = null), 2200);
  }

  function fail(cause: unknown) {
    error = cause instanceof ApiError ? cause.message : String(cause);
    setTimeout(() => (error = null), 4000);
  }

  // -- loading ---------------------------------------------------------------
  let disconnectLive: (() => void) | null = null;

  onMount(() => {
    void load();
    // The Deck can edit tiles too (wiggle mode on the Nest Hub), so the Editor
    // subscribes as well rather than only broadcasting. Echoes of our own
    // writes are harmless here: they just trigger a redundant refetch of state
    // the server already confirmed.
    disconnectLive = subscribeToEvents({
      tile_updated: ({ page_id }) => {
        if (page_id === activePageId) void loadTiles();
      },
      page_updated: () => void loadPages(),
      profile_updated: () => void load(),
      profile_activated: () => void load(),
      action_updated: async () => {
        actions = await api.listActions();
      },
      category_updated: async () => {
        categories = await api.listCategories();
      }
    });
  });

  onDestroy(() => disconnectLive?.());

  async function load() {
    try {
      profiles = await api.listProfiles();
      profile = profiles.find((p) => p.id === profile?.id) ?? profiles.find((p) => p.active) ?? profiles[0] ?? null;
      [categories, actions] = await Promise.all([api.listCategories(), api.listActions()]);
      await loadPages();
      error = null;
    } catch (cause) {
      fail(cause);
    }
  }

  async function loadPages() {
    if (!profile) {
      pages = [];
      slots = [];
      return;
    }
    pages = await api.listPages(profile.id);
    if (!pages.some((p) => p.id === activePageId)) activePageId = pages[0]?.id ?? null;
    await loadTiles();
  }

  async function loadTiles() {
    slots = activePageId ? await api.listTiles(activePageId) : [];
  }

  // -- tile mutations --------------------------------------------------------
  async function placeAction(slot: TileSlot, actionId: string) {
    const previous = slot.tile;
    try {
      await api.placeTile({
        page_id: activePageId!,
        row: slot.row,
        col: slot.col,
        action_id: actionId
      });
      await loadTiles();
      pushUndo('placement', async () => {
        if (previous?.action_id) {
          await api.placeTile({
            page_id: activePageId!,
            row: slot.row,
            col: slot.col,
            action_id: previous.action_id,
            custom_label: previous.custom_label,
            custom_icon: previous.custom_icon
          });
        } else {
          const current = slots.find((s) => s.row === slot.row && s.col === slot.col);
          if (current?.tile) await api.clearTile(current.tile.id);
        }
        await loadTiles();
      });
    } catch (cause) {
      fail(cause);
    }
  }

  async function removeTile(slot: TileSlot) {
    if (!slot.tile) return;
    const previous = slot.tile;
    try {
      await api.clearTile(previous.id);
      await loadTiles();
      pushUndo('suppression', async () => {
        if (previous.action_id) {
          await api.placeTile({
            page_id: activePageId!,
            row: slot.row,
            col: slot.col,
            action_id: previous.action_id,
            custom_label: previous.custom_label,
            custom_icon: previous.custom_icon
          });
        }
        await loadTiles();
      });
    } catch (cause) {
      fail(cause);
    }
  }

  async function duplicateTile(slot: TileSlot) {
    if (!slot.tile?.action_id) return;
    const target = slots.find((s) => !s.tile);
    if (!target) {
      flash('Aucun emplacement libre sur cette page.');
      return;
    }
    await placeAction(target, slot.tile.action_id);
  }

  /** One PATCH: the backend swaps atomically when the target is occupied. */
  async function swapSlots(fromIndex: number, toIndex: number) {
    const from = slots[fromIndex];
    const to = slots[toIndex];
    if (!from || !to || (!from.tile && !to.tile)) return;

    const mover = from.tile ?? to.tile!;
    const target = from.tile ? { row: to.row, col: to.col } : { row: from.row, col: from.col };
    const origin = from.tile ? { row: from.row, col: from.col } : { row: to.row, col: to.col };

    try {
      await api.updateTile(mover.id, target);
      await loadTiles();
      pushUndo('déplacement', async () => {
        await api.updateTile(mover.id, origin);
        await loadTiles();
      });
    } catch (cause) {
      fail(cause);
    }
  }

  async function saveTileEdit(patch: {
    action_id?: string;
    custom_label?: string | null;
    custom_icon?: string | null;
  }) {
    const slot = editingSlot;
    editingSlot = null;
    if (!slot?.tile) return;
    const previous = slot.tile;

    try {
      await api.updateTile(previous.id, patch);
      await loadTiles();
      pushUndo('modification', async () => {
        await api.updateTile(previous.id, {
          action_id: previous.action_id,
          custom_label: previous.custom_label,
          custom_icon: previous.custom_icon
        });
        await loadTiles();
      });
    } catch (cause) {
      fail(cause);
    }
  }

  // -- page mutations --------------------------------------------------------
  async function createPage(name: string, color: string) {
    try {
      const page = await api.createPage({ profile_id: profile!.id, name, color });
      await loadPages();
      activePageId = page.id;
      await loadTiles();
      pushUndo('nouvelle page', async () => {
        await api.deletePage(page.id);
        await loadPages();
      });
    } catch (cause) {
      fail(cause);
    }
  }

  async function deletePage(id: string) {
    // PageList already asks for a second click before calling this.
    if (!pages.some((p) => p.id === id)) return;
    try {
      await api.deletePage(id);
      await loadPages();
      // Recreating a page cannot restore its tiles, so this is not undoable.
      undoStack = [];
    } catch (cause) {
      fail(cause);
    }
  }

  async function reorderPage(id: string, position: number) {
    const before = pages.find((p) => p.id === id)?.position ?? 0;
    try {
      await api.movePage(id, position);
      await loadPages();
      pushUndo('réordonnancement', async () => {
        await api.movePage(id, before);
        await loadPages();
      });
    } catch (cause) {
      fail(cause);
    }
  }

  async function setPageColor(color: string) {
    if (!activePage) return;
    const before = activePage.color;
    try {
      await api.updatePage(activePage.id, { color });
      await loadPages();
      pushUndo('couleur', async () => {
        await api.updatePage(activePage.id, { color: before });
        await loadPages();
      });
    } catch (cause) {
      fail(cause);
    }
  }

  async function renamePage(name: string) {
    if (!activePage || !name.trim()) return;
    const before = activePage.name;
    try {
      await api.updatePage(activePage.id, { name: name.trim() });
      await loadPages();
      pushUndo('renommage', async () => {
        await api.updatePage(activePage.id, { name: before });
        await loadPages();
      });
    } catch (cause) {
      fail(cause);
    }
  }

  // -- profile mutations -----------------------------------------------------
  async function selectProfile(id: string) {
    profile = profiles.find((p) => p.id === id) ?? profile;
    activePageId = null;
    await loadPages();
  }

  async function createProfile(name: string) {
    try {
      const created = await api.createProfile({ name });
      profiles = await api.listProfiles();
      profile = created;
      activePageId = null;
      await loadPages();
    } catch (cause) {
      fail(cause);
    }
  }

  async function renameProfile(id: string, name: string) {
    try {
      await api.updateProfile(id, { name });
      profiles = await api.listProfiles();
      profile = profiles.find((p) => p.id === id) ?? profile;
    } catch (cause) {
      fail(cause);
    }
  }

  async function deleteProfile(id: string) {
    // ProfileSwitcher already asks for a second click before calling this.
    if (!profiles.some((p) => p.id === id)) return;
    try {
      await api.deleteProfile(id);
      profiles = await api.listProfiles();
      if (profile?.id === id) profile = profiles[0] ?? null;
      activePageId = null;
      await loadPages();
      undoStack = [];
    } catch (cause) {
      fail(cause);
    }
  }

  async function activateProfile() {
    if (!profile) return;
    try {
      await api.activateProfile(profile.id);
      profiles = await api.listProfiles();
      profile = profiles.find((p) => p.id === profile?.id) ?? profile;
      flash('Profil activé sur le Deck.');
    } catch (cause) {
      fail(cause);
    }
  }

  // -- custom actions --------------------------------------------------------
  let actionModalOpen = $state(false);
  let editingAction = $state<Action | null>(null);

  function openActionEditor(target: Action | null) {
    editingAction = target;
    actionModalOpen = true;
  }

  async function saveAction(
    payload: Parameters<typeof api.createAction>[0] & {
      newCategory?: { name: string; color: string };
    }
  ) {
    const target = editingAction;
    try {
      const { newCategory, ...body } = payload;
      if (newCategory) {
        // Create the category first, then file the action under it.
        const created = await api.createCategory(newCategory);
        body.category_id = created.id;
        categories = await api.listCategories();
      }
      if (target) await api.updateAction(target.id, body);
      else await api.createAction(body);
      actions = await api.listActions();
      actionModalOpen = false;
      editingAction = null;
      // A label or icon change is reflected on the tiles using it.
      await loadTiles();
      flash(target ? 'Action mise à jour.' : 'Action créée.');
    } catch (cause) {
      fail(cause);
    }
  }

  async function deleteAction(target: Action) {
    try {
      await api.deleteAction(target.id);
      actions = await api.listActions();
      actionModalOpen = false;
      editingAction = null;
      // Deleting an action clears the tiles that used it.
      await loadTiles();
      undoStack = [];
      flash('Action supprimée.');
    } catch (cause) {
      fail(cause);
    }
  }

  // -- import / export -------------------------------------------------------
  async function exportProfile() {
    if (!profile) return;
    try {
      const list = await api.listPages(profile.id);
      const payload = {
        version: 1,
        profile: { name: profile.name, icon: profile.icon },
        pages: await Promise.all(
          list.map(async (page) => ({
            name: page.name,
            color: page.color,
            icon: page.icon,
            position: page.position,
            tiles: (await api.listTiles(page.id))
              .filter((s) => s.tile)
              .map((s) => ({
                row: s.row,
                col: s.col,
                action_label: s.tile!.action?.label ?? null,
                custom_label: s.tile!.custom_label,
                custom_icon: s.tile!.custom_icon
              }))
          }))
        )
      };

      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: 'application/json'
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `nest-deck-${profile.name.toLowerCase().replace(/\s+/g, '-')}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (cause) {
      fail(cause);
    }
  }

  async function importProfile(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    try {
      const payload = JSON.parse(await file.text());
      const created = await api.createProfile({
        name: `${payload.profile?.name ?? 'Importé'} (import)`,
        icon: payload.profile?.icon ?? 'house'
      });

      for (const page of payload.pages ?? []) {
        const newPage = await api.createPage({
          profile_id: created.id,
          name: page.name,
          color: page.color,
          icon: page.icon
        });
        for (const tile of page.tiles ?? []) {
          // Actions are matched by label — ids differ across databases.
          const match = actions.find((a) => a.label === tile.action_label);
          if (!match) continue;
          await api.placeTile({
            page_id: newPage.id,
            row: tile.row,
            col: tile.col,
            action_id: match.id,
            custom_label: tile.custom_label,
            custom_icon: tile.custom_icon
          });
        }
      }

      profiles = await api.listProfiles();
      profile = created;
      activePageId = null;
      await loadPages();
      flash('Profil importé.');
    } catch (cause) {
      fail(cause);
    } finally {
      if (importInput) importInput.value = '';
    }
  }

  function onKeydown(event: KeyboardEvent) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
      event.preventDefault();
      void undo();
    }
  }
</script>

<svelte:head><title>Nest Deck · Editor</title></svelte:head>
<svelte:window onkeydown={onKeydown} />

<div class="grid h-screen place-items-center p-8 text-center min-[1024px]:hidden">
  <p class="text-body text-surface-muted">
    L'éditeur nécessite une fenêtre d'au moins 1024px de large.
  </p>
</div>

<div class="hidden h-screen grid-rows-[64px_1fr] min-[1024px]:grid">
  <!-- Top bar -------------------------------------------------------------- -->
  <header class="flex items-center gap-3 border-b border-black/5 px-5">
    <h1 class="text-page-heading">Nest Deck</h1>
    <span class="text-label text-surface-muted">Éditeur</span>

    <div class="ml-auto flex items-center gap-2">
      {#if notice}
        <span class="rounded-pill bg-cat-meeting px-3 py-1 text-label text-cat-meeting-text">
          {notice}
        </span>
      {/if}
      {#if error}
        <span class="rounded-pill bg-cat-stream px-3 py-1 text-label text-cat-stream-text">
          {error}
        </span>
      {/if}

      <button
        type="button"
        class="h-10 rounded-pill px-3 text-label hover:bg-black/5 disabled:opacity-40"
        onclick={undo}
        disabled={undoStack.length === 0}
        title="Ctrl+Z"
      >
        <i class="ph ph-arrow-counter-clockwise" aria-hidden="true"></i>
        Annuler
      </button>

      {#if profile && !profile.active}
        <button
          type="button"
          class="h-10 rounded-pill px-3 text-label hover:bg-black/5"
          onclick={activateProfile}
        >
          <i class="ph ph-broadcast" aria-hidden="true"></i>
          Activer sur le Deck
        </button>
      {/if}

      <button
        type="button"
        class="h-10 rounded-pill px-3 text-label hover:bg-black/5"
        onclick={() => importInput?.click()}
      >
        <i class="ph ph-upload-simple" aria-hidden="true"></i> Importer
      </button>
      <input
        bind:this={importInput}
        type="file"
        accept="application/json"
        class="hidden"
        onchange={importProfile}
      />

      <button
        type="button"
        class="h-10 rounded-pill px-3 text-label hover:bg-black/5"
        onclick={exportProfile}
      >
        <i class="ph ph-download-simple" aria-hidden="true"></i> Exporter
      </button>

      <button
        type="button"
        class="h-10 rounded-pill px-3 text-label hover:bg-black/5"
        class:bg-black={livePreview}
        class:text-white={livePreview}
        onclick={() => (livePreview = !livePreview)}
        aria-pressed={livePreview}
      >
        <i class="ph ph-monitor-play" aria-hidden="true"></i> Live preview
      </button>
    </div>
  </header>

  <!-- Three columns --------------------------------------------------------- -->
  <div
    class="grid min-h-0"
    style="grid-template-columns: 280px 1fr {livePreview ? '420px' : '320px'}"
  >
    <aside class="flex min-h-0 flex-col gap-4 overflow-y-auto border-r border-black/5 p-5">
      <ProfileSwitcher
        {profiles}
        current={profile}
        onselect={selectProfile}
        oncreate={createProfile}
        onrename={renameProfile}
        ondelete={deleteProfile}
      />
      <PageList
        {pages}
        activeId={activePageId}
        onselect={async (id) => {
          activePageId = id;
          await loadTiles();
        }}
        oncreate={createPage}
        ondelete={deletePage}
        onreorder={reorderPage}
      />
    </aside>

    <main class="flex min-w-0 flex-col gap-4 overflow-y-auto p-page">
      {#if activePage}
        <div class="flex items-center gap-4">
          <input
            class="min-w-0 flex-1 rounded-xl border border-transparent px-2 py-1 text-page-heading hover:border-black/10 focus:border-black/20"
            value={activePage.name}
            onchange={(event) => renamePage(event.currentTarget.value)}
            aria-label="Nom de la page"
          />
          <div class="flex items-center gap-2">
            {#each CATEGORY_TOKENS as token (token)}
              <button
                type="button"
                class="size-7 rounded-pill border-[3px]"
                style="background: {tokens.category[token].accent}; border-color: {activePage.color ===
                token
                  ? 'rgb(0 0 0 / 0.35)'
                  : 'transparent'}"
                onclick={() => setPageColor(token)}
                aria-label="Couleur {token}"
              ></button>
            {/each}
          </div>
        </div>

        <EditableGrid
          page={activePage}
          {slots}
          onswap={swapSlots}
          onedit={(slot) => (editingSlot = slot)}
          onremove={removeTile}
          onduplicate={duplicateTile}
          ondropaction={placeAction}
        />

        <p class="text-label text-surface-muted">
          Glissez une action du catalogue sur un emplacement, ou faites glisser les
          tuiles entre elles pour les échanger.
        </p>
      {:else}
        <p class="text-body text-surface-muted">
          Aucune page. Créez-en une dans la colonne de gauche.
        </p>
      {/if}
    </main>

    <aside class="flex min-h-0 flex-col gap-4 overflow-hidden border-l border-black/5 p-5">
      {#if livePreview}
        <div class="flex shrink-0 flex-col gap-2">
          <p class="text-label uppercase tracking-wide text-surface-muted">Aperçu Deck</p>
          <!-- 1280x800 scaled down to the panel width. -->
          <div class="aspect-[1280/800] w-full overflow-hidden rounded-2xl border border-black/10">
            <iframe
              src="/"
              title="Aperçu du Deck"
              class="origin-top-left border-0"
              style="width: 1280px; height: 800px; transform: scale(0.29)"
            ></iframe>
          </div>
        </div>
      {/if}
      <ActionCatalog
        {categories}
        {actions}
        oncreate={() => openActionEditor(null)}
        onedit={openActionEditor}
      />
    </aside>
  </div>
</div>

<ActionEditorModal
  open={actionModalOpen}
  action={editingAction}
  {categories}
  onsave={saveAction}
  ondelete={deleteAction}
  onclose={() => {
    actionModalOpen = false;
    editingAction = null;
  }}
/>

<TileEditorModal
  slot={editingSlot}
  {categories}
  {actions}
  pageColor={activePage?.color ?? 'pc'}
  onsave={saveTileEdit}
  oncancel={() => (editingSlot = null)}
/>
