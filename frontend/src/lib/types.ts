/**
 * Wire types — these mirror `backend/app/models.py` and `backend/app/schemas.py`.
 * Keep them in sync when the backend schema changes.
 */

import type { CategoryToken } from './theme';

export type ActionType =
  | 'demo'
  | 'fetch'
  | 'obs'
  | 'spotify'
  | 'pc'
  | 'meeting'
  | 'launcher'
  | 'open';

export interface Category {
  id: string;
  name: string;
  /** One of the five design tokens. */
  color: CategoryToken | string;
  icon: string;
}

export interface Action {
  id: string;
  category_id: string;
  label: string;
  /** Phosphor icon name, e.g. `broadcast`. */
  icon: string;
  type: ActionType;
  endpoint: string | null;
  params: Record<string, unknown>;
}

export interface Profile {
  id: string;
  name: string;
  icon: string;
  active: boolean;
  created_at: string;
}

export interface Page {
  id: string;
  profile_id: string;
  name: string;
  color: CategoryToken | string;
  position: number;
  icon: string;
  /** Grid geometry, per page: 3-6 rows by 5-6 columns. */
  rows: number;
  cols: number;
}

export interface Tile {
  id: string;
  page_id: string;
  action_id: string | null;
  row: number;
  col: number;
  custom_label: string | null;
  custom_icon: string | null;
  /** Inlined by the backend so the Deck renders in one round-trip. */
  action: Action | null;
}

/** One of the 15 grid slots. `tile` is null for an empty slot. */
export interface TileSlot {
  row: number;
  col: number;
  tile: Tile | null;
}

/** An application discovered on the host, for the launcher picker. */
export interface InstalledApp {
  name: string;
  path: string;
}

export interface BrowseEntry {
  name: string;
  path: string;
  kind: 'dir' | 'file';
}

export interface BrowseResult {
  path: string | null;
  parent: string | null;
  entries: BrowseEntry[];
}

/** A Chromecast / Nest Hub found on the network (desktop app). */
export interface CastDevice {
  uuid: string;
  name: string;
  model: string;
  host: string;
  port: number;
}

export interface CastStatus {
  connected: boolean;
  device: CastDevice | null;
  casting?: boolean;
  current_app?: string | null;
  deck_url?: string;
}

export interface FireResult {
  status: 'ok' | 'error';
  message: string;
  duration_ms: number;
}

/** SSE payloads broadcast by the backend on every mutation. */
export type DeckEvent =
  | { type: 'profile_activated'; payload: { profile_id: string } }
  | { type: 'profile_updated'; payload: { profile_id: string } }
  | { type: 'page_updated'; payload: { page_id: string } }
  | { type: 'tile_updated'; payload: { tile_id: string; page_id: string } }
  | { type: 'action_fired'; payload: { tile_id: string; status: string } };

/** What a tile actually shows, after applying per-tile overrides. */
export function tileLabel(tile: Tile | null): string {
  return tile?.custom_label ?? tile?.action?.label ?? '';
}

export function tileIcon(tile: Tile | null): string {
  return tile?.custom_icon ?? tile?.action?.icon ?? 'plus';
}
