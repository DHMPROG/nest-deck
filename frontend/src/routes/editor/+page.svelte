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
  import CastPanel from '$lib/components/editor/CastPanel.svelte';
  import OnboardingWizard from '$lib/components/editor/OnboardingWizard.svelte';
  import { theme } from '$lib/stores/theme.svelte';
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

  // -- onboarding & settings -------------------------------------------------
  let showOnboarding = $state(false);
  let settingsOpen = $state(false);
  let autostart = $state(false);
  let autostartSupported = $state(false);
  let appPort = $state(8770);
  let portDraft = $state('8770');
  let portSaved = $state(false);

  async function refreshSettings() {
    try {
      const s = await api.getSettings();
      autostart = s.autostart;
      autostartSupported = s.autostart_supported;
      appPort = s.port;
      portDraft = String(s.port);
      return s;
    } catch {
      return null;
    }
  }

  async function toggleAutostart() {
    autostart = !autostart; // optimistic
    try {
      const s = await api.setSettings({ autostart });
      autostart = s.autostart;
    } catch (cause) {
      autostart = !autostart;
      fail(cause);
    }
  }

  async function savePort() {
    const value = Number(portDraft);
    if (!Number.isInteger(value) || value < 1024 || value > 65535) {
      portDraft = String(appPort);
      return;
    }
    if (value === appPort) return;
    try {
      const s = await api.setSettings({ port: value });
      appPort = s.port;
      portDraft = String(s.port);
      portSaved = true;
      setTimeout(() => (portSaved = false), 3000);
    } catch (cause) {
      portDraft = String(appPort);
      fail(cause);
    }
  }

  onMount(() => {
    void load();
    void (async () => {
      const s = await refreshSettings();
      if (s) showOnboarding = !s.onboarded;
    })();
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

  /** Resize the grid. Shrinking clears the tiles that fall outside. */
  async function setGrid(rows: number, cols: number) {
    if (!activePage) return;
    const before = { rows: activePage.rows, cols: activePage.cols };
    if (rows === before.rows && cols === before.cols) return;

    const shrinking = rows < before.rows || cols < before.cols;
    const lost = shrinking
      ? slots.filter((s) => s.tile && (s.row >= rows || s.col >= cols)).length
      : 0;

    try {
      await api.updatePage(activePage.id, { rows, cols });
      await loadPages();
      if (lost > 0) flash(`${lost} tuile${lost > 1 ? 's' : ''} retirée${lost > 1 ? 's' : ''}.`);
      // Not undoable when it destroyed tiles — re-growing cannot restore them.
      if (lost === 0) {
        pushUndo('taille de la grille', async () => {
          await api.updatePage(activePage.id, before);
          await loadPages();
        });
      } else {
        undoStack = [];
      }
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

  /** Configure the action sitting on a placed tile. */
  function configureTileAction(slot: TileSlot) {
    const target = actions.find((a) => a.id === slot.tile?.action_id);
    if (target) openActionEditor(target);
  }

  function configureActionById(actionId: string) {
    const target = actions.find((a) => a.id === actionId);
    if (!target) return;
    editingSlot = null; // close the tile modal first
    openActionEditor(target);
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
  <p class="text-body text-app-muted">
    L'éditeur nécessite une fenêtre d'au moins 1024px de large.
  </p>
</div>

<div class="hidden h-screen grid-rows-[64px_1fr] min-[1024px]:grid">
  <!-- Top bar -------------------------------------------------------------- -->
  <header class="flex items-center gap-3 border-b border-app-border px-5">
    <h1 class="text-page-heading">Nest Deck</h1>
    <span class="text-label text-app-muted">Éditeur</span>

    <div class="ml-auto flex items-center gap-2">
      <CastPanel />
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
        class="h-10 rounded-pill px-3 text-label hover:bg-app-hover disabled:opacity-40"
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
          class="h-10 rounded-pill px-3 text-label hover:bg-app-hover"
          onclick={activateProfile}
        >
          <i class="ph ph-broadcast" aria-hidden="true"></i>
          Activer sur le Deck
        </button>
      {/if}

      <button
        type="button"
        class="h-10 rounded-pill px-3 text-label hover:bg-app-hover"
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
        class="h-10 rounded-pill px-3 text-label hover:bg-app-hover"
        onclick={exportProfile}
      >
        <i class="ph ph-download-simple" aria-hidden="true"></i> Exporter
      </button>

      <button
        type="button"
        class="h-10 rounded-pill px-3 text-label hover:bg-app-hover"
        class:bg-black={livePreview}
        class:text-white={livePreview}
        onclick={() => (livePreview = !livePreview)}
        aria-pressed={livePreview}
      >
        <i class="ph ph-monitor-play" aria-hidden="true"></i> Live preview
      </button>

      <button
        type="button"
        class="grid size-10 place-items-center rounded-pill hover:bg-app-hover"
        onclick={() => theme.toggle()}
        aria-label={theme.mode === 'dark' ? 'Passer en clair' : 'Passer en sombre'}
        title={theme.mode === 'dark' ? 'Mode clair' : 'Mode sombre'}
      >
        <i class="ph ph-{theme.mode === 'dark' ? 'sun' : 'moon'} text-lg" aria-hidden="true"></i>
      </button>

      <button
        type="button"
        class="grid size-10 place-items-center rounded-pill hover:bg-app-hover"
        onclick={() => (showOnboarding = true)}
        aria-label="Revoir le guide"
        title="Revoir le guide"
      >
        <i class="ph ph-question text-lg" aria-hidden="true"></i>
      </button>

      <div class="relative">
        <button
          type="button"
          class="grid size-10 place-items-center rounded-pill hover:bg-app-hover"
          onclick={() => {
            settingsOpen = !settingsOpen;
            if (settingsOpen) void refreshSettings();
          }}
          aria-label="Réglages"
          aria-expanded={settingsOpen}
          title="Réglages"
        >
          <i class="ph ph-gear text-lg" aria-hidden="true"></i>
        </button>

        {#if settingsOpen}
          <div
            class="absolute top-12 right-0 z-40 w-72 rounded-2xl bg-app-surface p-2 shadow-hover"
          >
            <button
              type="button"
              class="flex w-full items-center gap-3 rounded-xl p-3 text-left hover:bg-app-hover disabled:opacity-50"
              onclick={toggleAutostart}
              disabled={!autostartSupported}
            >
              <i class="ph ph-power text-xl" aria-hidden="true"></i>
              <span class="flex-1">
                <span class="block text-body font-medium">Démarrer avec Windows</span>
                <span class="block text-label text-app-muted">
                  {#if autostartSupported}
                    Lancer Nest Deck à l'ouverture de session
                  {:else}
                    Disponible seulement dans l'application (.exe)
                  {/if}
                </span>
              </span>
              <span
                class="relative h-6 w-10 shrink-0 rounded-pill transition-colors"
                style="background: {autostart
                  ? tokens.category.meeting.accent
                  : 'var(--border)'}"
              >
                <span
                  class="absolute top-0.5 size-5 rounded-pill bg-white transition-all"
                  style="left: {autostart ? '1.25rem' : '0.125rem'}"
                ></span>
              </span>
            </button>

            <div class="flex w-full items-center gap-3 rounded-xl p-3">
              <i class="ph ph-plugs text-xl" aria-hidden="true"></i>
              <span class="flex-1">
                <span class="block text-body font-medium">Port du serveur</span>
                <span class="block text-label text-app-muted">
                  {#if portSaved}
                    Enregistré — redémarre l'application
                  {:else}
                    Appliqué au prochain démarrage
                  {/if}
                </span>
              </span>
              <input
                type="number"
                min="1024"
                max="65535"
                class="w-20 rounded-lg border border-app-border bg-transparent px-2 py-1 text-right text-body"
                bind:value={portDraft}
                onblur={savePort}
                onkeydown={(e) => e.key === 'Enter' && (e.currentTarget as HTMLInputElement).blur()}
                aria-label="Port du serveur"
              />
            </div>
          </div>
        {/if}
      </div>
    </div>
  </header>

  <!-- Three columns --------------------------------------------------------- -->
  <div
    class="grid min-h-0"
    style="grid-template-columns: 280px 1fr {livePreview ? '420px' : '320px'}"
  >
    <aside class="flex min-h-0 flex-col gap-4 overflow-y-auto border-r border-app-border p-5">
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
            class="min-w-0 flex-1 rounded-xl border border-transparent px-2 py-1 text-page-heading hover:border-app-border focus:border-app-border"
            value={activePage.name}
            onchange={(event) => renamePage(event.currentTarget.value)}
            aria-label="Nom de la page"
          />
          <!-- Grid size: 3-6 rows by 5-6 columns. -->
          <div class="flex items-center gap-2 rounded-pill bg-app-sunken px-3 py-1.5">
            <i class="ph ph-grid-four text-app-muted" aria-hidden="true"></i>
            <select
              class="rounded-lg bg-transparent text-label"
              value={activePage.rows}
              onchange={(e) => setGrid(Number(e.currentTarget.value), activePage.cols)}
              aria-label="Nombre de lignes"
            >
              {#each [3, 4, 5, 6] as n (n)}
                <option value={n}>{n}</option>
              {/each}
            </select>
            <span class="text-label text-app-muted">×</span>
            <select
              class="rounded-lg bg-transparent text-label"
              value={activePage.cols}
              onchange={(e) => setGrid(activePage.rows, Number(e.currentTarget.value))}
              aria-label="Nombre de colonnes"
            >
              {#each [5, 6] as n (n)}
                <option value={n}>{n}</option>
              {/each}
            </select>
          </div>

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
          onconfigure={configureTileAction}
          ondropaction={placeAction}
        />

        <p class="text-label text-app-muted">
          Glissez une action du catalogue sur un emplacement, ou faites glisser les
          tuiles entre elles pour les échanger.
        </p>
      {:else}
        <p class="text-body text-app-muted">
          Aucune page. Créez-en une dans la colonne de gauche.
        </p>
      {/if}
    </main>

    <aside class="flex min-h-0 flex-col gap-4 overflow-hidden border-l border-app-border p-5">
      {#if livePreview}
        <div class="flex shrink-0 flex-col gap-2">
          <p class="text-label uppercase tracking-wide text-app-muted">Aperçu Deck</p>
          <!-- 1280x800 scaled down to the panel width. -->
          <div class="aspect-[1280/800] w-full overflow-hidden rounded-2xl border border-app-border">
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

<OnboardingWizard open={showOnboarding} onclose={() => (showOnboarding = false)} />

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
  onconfigure={configureActionById}
  oncancel={() => (editingSlot = null)}
/>
