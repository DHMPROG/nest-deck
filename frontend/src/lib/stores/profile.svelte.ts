/**
 * Deck state: the active profile, its pages, and the 15 slots of the current
 * page. This is the single place that talks to the API for the Deck view.
 */

import { api, ApiError } from '$lib/services/api';
import { subscribeToEvents } from '$lib/services/sse';
import type { Page, Profile, TileSlot } from '$lib/types';
import { GRID } from '$lib/theme';

class DeckState {
  profiles = $state<Profile[]>([]);
  profile = $state<Profile | null>(null);
  pages = $state<Page[]>([]);
  pageIndex = $state(0);
  slots = $state<TileSlot[]>([]);

  online = $state(false);
  loading = $state(true);
  error = $state<string | null>(null);
  /** +1 when moving to a later page, -1 when going back. Drives the slide. */
  direction = $state(1);

  activePage = $derived<Page | null>(this.pages[this.pageIndex] ?? null);
  filledCount = $derived(this.slots.filter((s) => s.tile).length);

  /**
   * Depth of in-flight local mutations. The backend broadcasts every write,
   * including our own, so while this is non-zero we ignore incoming events —
   * otherwise a drag would fight the echo of its own PATCH.
   */
  #localWrites = 0;

  #fail(cause: unknown) {
    this.error = cause instanceof ApiError ? cause.message : String(cause);
    if (cause instanceof ApiError && cause.status === 0) this.online = false;
  }

  /** Run a local write with live updates suppressed until its echo passes. */
  async #write<T>(run: () => Promise<T>): Promise<T | undefined> {
    this.#localWrites++;
    try {
      return await run();
    } catch (cause) {
      this.#fail(cause);
      return undefined;
    } finally {
      setTimeout(() => this.#localWrites--, 250);
    }
  }

  /**
   * Subscribe to backend mutations so an edit made in the Editor shows up here
   * without a reload. Returns an unsubscribe function.
   */
  connectLive(): () => void {
    return subscribeToEvents({
      onopen: () => {
        this.online = true;
        this.error = null;
      },
      onerror: () => (this.online = false),

      tile_updated: ({ page_id }) => {
        if (this.#localWrites > 0) return;
        // Only the current page is on screen; anything else can wait.
        if (page_id === this.activePage?.id) void this.refreshTiles();
      },

      page_updated: () => {
        if (this.#localWrites > 0) return;
        void this.reloadPages();
      },

      profile_updated: () => {
        if (this.#localWrites > 0) return;
        void this.reloadProfiles();
      },

      profile_activated: () => {
        // A different profile took over: reload everything.
        this.pageIndex = 0;
        void this.load();
      }
    });
  }

  /** Refresh page metadata (names, colours, order) without losing the slot. */
  async reloadPages() {
    if (!this.profile) return;
    try {
      const current = this.activePage?.id;
      this.pages = await api.listPages(this.profile.id);
      const index = this.pages.findIndex((p) => p.id === current);
      this.pageIndex = index >= 0 ? index : Math.min(this.pageIndex, this.pages.length - 1);
      await this.refreshTiles();
    } catch (cause) {
      this.#fail(cause);
    }
  }

  async reloadProfiles() {
    try {
      this.profiles = await api.listProfiles();
      this.profile =
        this.profiles.find((p) => p.id === this.profile?.id) ?? this.profile;
    } catch (cause) {
      this.#fail(cause);
    }
  }

  async load() {
    this.loading = true;
    try {
      this.profiles = await api.listProfiles();
      this.profile = this.profiles.find((p) => p.active) ?? this.profiles[0] ?? null;
      if (!this.profile) {
        this.online = true;
        this.error = 'no profile on the backend';
        return;
      }
      this.pages = await api.listPages(this.profile.id);
      this.pageIndex = Math.min(this.pageIndex, Math.max(this.pages.length - 1, 0));
      await this.refreshTiles();
      this.online = true;
      this.error = null;
    } catch (cause) {
      this.#fail(cause);
    } finally {
      this.loading = false;
    }
  }

  async refreshTiles() {
    const page = this.activePage;
    if (!page) {
      this.slots = [];
      return;
    }
    try {
      this.slots = await api.listTiles(page.id);
      this.online = true;
      this.error = null;
    } catch (cause) {
      this.#fail(cause);
    }
  }

  async goToPage(index: number) {
    if (index < 0 || index >= this.pages.length || index === this.pageIndex) return;
    this.direction = index > this.pageIndex ? 1 : -1;
    this.pageIndex = index;
    await this.refreshTiles();
  }

  nextPage() {
    return this.goToPage(this.pageIndex + 1);
  }

  previousPage() {
    return this.goToPage(this.pageIndex - 1);
  }

  /**
   * Swap the contents of two slots. A single PATCH is enough: the backend
   * swaps atomically when the destination is occupied, and performs a plain
   * move when it is free.
   */
  async swapSlots(fromIndex: number, toIndex: number) {
    const from = this.slots[fromIndex];
    const to = this.slots[toIndex];
    if (!from || !to || fromIndex === toIndex) return;
    if (!from.tile && !to.tile) return;

    // Optimistic: exchange the payloads, keeping each slot's own row/col.
    const next = [...this.slots];
    next[fromIndex] = { ...from, tile: to.tile };
    next[toIndex] = { ...to, tile: from.tile };
    this.slots = next;

    const mover = from.tile ?? to.tile!;
    const target = from.tile ? { row: to.row, col: to.col } : { row: from.row, col: from.col };

    await this.#write(() => api.updateTile(mover.id, target));
    // The server is authoritative — reconcile either way.
    await this.refreshTiles();
  }

  /** Empty a slot (edit mode). */
  async clearTile(tileId: string) {
    await this.#write(() => api.clearTile(tileId));
    await this.refreshTiles();
  }

  /** Drop an action onto an empty slot. */
  async placeAction(row: number, col: number, actionId: string) {
    const page = this.activePage;
    if (!page) return;
    await this.#write(() =>
      api.placeTile({ page_id: page.id, row, col, action_id: actionId })
    );
    await this.refreshTiles();
  }

  async renamePage(pageId: string, name: string) {
    const trimmed = name.trim();
    if (!trimmed) return;
    const updated = await this.#write(() => api.updatePage(pageId, { name: trimmed }));
    if (updated) this.pages = this.pages.map((p) => (p.id === pageId ? updated : p));
  }

  async activateProfile(profileId: string) {
    try {
      await api.activateProfile(profileId);
      this.pageIndex = 0;
      await this.load();
    } catch (cause) {
      this.#fail(cause);
    }
  }

  /** Index in the flat 15-slot array for a grid position. */
  static indexOf(row: number, col: number) {
    return row * GRID.cols + col;
  }
}

export const deck = new DeckState();
