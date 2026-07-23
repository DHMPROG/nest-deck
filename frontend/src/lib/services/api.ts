/**
 * Typed fetch wrapper around the FastAPI backend.
 *
 * In dev, Vite proxies `/api` to `http://127.0.0.1:8000`, so the base stays
 * empty. In Docker, `VITE_API_BASE` points at the server IP.
 */

import type {
  Action,
  ActionType,
  BrowseResult,
  CastDevice,
  CastStatus,
  Category,
  FireResult,
  InstalledApp,
  Page,
  Profile,
  Tile,
  TileSlot
} from '$lib/types';

const BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}/api${path}`, {
      ...init,
      headers:
        init?.body !== undefined
          ? { 'content-type': 'application/json', ...init?.headers }
          : init?.headers
    });
  } catch (cause) {
    // Network-level failure: the backend is down or unreachable.
    throw new ApiError(0, `backend unreachable: ${String(cause)}`);
  }

  if (!response.ok) {
    // FastAPI puts the reason in `detail`; fall back to the status text.
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      /* non-JSON error body — keep the status text */
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

export const api = {
  health: () => request<{ status: string; database: string }>('/health'),

  // -- profiles -------------------------------------------------------------
  listProfiles: () => request<Profile[]>('/profiles'),
  createProfile: (body: { name: string; icon?: string }) =>
    request<Profile>('/profiles', { method: 'POST', ...json(body) }),
  updateProfile: (id: string, body: { name?: string; icon?: string }) =>
    request<Profile>(`/profiles/${id}`, { method: 'PATCH', ...json(body) }),
  activateProfile: (id: string) =>
    request<Profile>(`/profiles/${id}/activate`, { method: 'PATCH' }),
  deleteProfile: (id: string) =>
    request<void>(`/profiles/${id}`, { method: 'DELETE' }),
  listPages: (profileId: string) => request<Page[]>(`/profiles/${profileId}/pages`),

  // -- pages ----------------------------------------------------------------
  createPage: (body: {
    profile_id: string;
    name: string;
    color: string;
    icon?: string;
    position?: number;
  }) => request<Page>('/pages', { method: 'POST', ...json(body) }),
  updatePage: (
    id: string,
    body: {
      name?: string;
      color?: string;
      icon?: string;
      position?: number;
      rows?: number;
      cols?: number;
    }
  ) => request<Page>(`/pages/${id}`, { method: 'PATCH', ...json(body) }),
  movePage: (id: string, position: number) =>
    request<Page>(`/pages/${id}/position`, { method: 'PATCH', ...json({ position }) }),
  deletePage: (id: string) => request<void>(`/pages/${id}`, { method: 'DELETE' }),
  /** Always returns 15 slots, empty ones with `tile: null`. */
  listTiles: (pageId: string) => request<TileSlot[]>(`/pages/${pageId}/tiles`),

  // -- tiles ----------------------------------------------------------------
  placeTile: (body: {
    page_id: string;
    row: number;
    col: number;
    action_id?: string | null;
    custom_label?: string | null;
    custom_icon?: string | null;
  }) => request<Tile>('/tiles', { method: 'POST', ...json(body) }),
  updateTile: (
    id: string,
    body: {
      row?: number;
      col?: number;
      action_id?: string | null;
      custom_label?: string | null;
      custom_icon?: string | null;
    }
  ) => request<Tile>(`/tiles/${id}`, { method: 'PATCH', ...json(body) }),
  clearTile: (id: string) => request<void>(`/tiles/${id}`, { method: 'DELETE' }),

  // -- catalog --------------------------------------------------------------
  listCategories: () => request<Category[]>('/categories'),
  createCategory: (body: { name: string; color?: string; icon?: string }) =>
    request<Category>('/categories', { method: 'POST', ...json(body) }),
  updateCategory: (id: string, body: { name?: string; color?: string; icon?: string }) =>
    request<Category>(`/categories/${id}`, { method: 'PATCH', ...json(body) }),
  deleteCategory: (id: string) =>
    request<void>(`/categories/${id}`, { method: 'DELETE' }),
  listActions: (opts: { category?: string; q?: string } = {}) => {
    const params = new URLSearchParams();
    if (opts.category) params.set('category', opts.category);
    if (opts.q) params.set('q', opts.q);
    const qs = params.toString();
    return request<Action[]>(`/actions${qs ? `?${qs}` : ''}`);
  },

  /** Custom actions: user-defined macros, launchers, URLs. */
  createAction: (body: {
    category_id: string;
    label: string;
    icon?: string;
    type: ActionType;
    endpoint?: string | null;
    params?: Record<string, unknown>;
  }) => request<Action>('/actions', { method: 'POST', ...json(body) }),
  updateAction: (
    id: string,
    body: {
      category_id?: string;
      label?: string;
      icon?: string;
      type?: ActionType;
      endpoint?: string | null;
      params?: Record<string, unknown>;
    }
  ) => request<Action>(`/actions/${id}`, { method: 'PATCH', ...json(body) }),
  deleteAction: (id: string) => request<void>(`/actions/${id}`, { method: 'DELETE' }),

  /** Host introspection, used by the launcher picker in the Editor. */
  listApps: (q?: string) =>
    request<InstalledApp[]>(`/system/apps${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  browse: (path?: string) =>
    request<BrowseResult>(
      `/system/browse${path ? `?path=${encodeURIComponent(path)}` : ''}`
    ),

  // -- fire -----------------------------------------------------------------
  fire: (tileId: string) =>
    request<FireResult>(`/fire/${tileId}`, { method: 'POST' }),

  // -- cast (desktop app) ---------------------------------------------------
  castDevices: (timeout = 6) =>
    request<{ devices: CastDevice[]; remembered: { uuid: string; name: string } | null }>(
      `/cast/devices?timeout=${timeout}`
    ),
  castStatus: () => request<CastStatus>('/cast/status'),
  castConnect: (target: { uuid?: string; name?: string }) =>
    request<CastStatus>('/cast/connect', { method: 'POST', ...json(target) }),
  castRecast: () => request<CastStatus>('/cast/recast', { method: 'POST' }),
  castDisconnect: () =>
    request<{ connected: boolean }>('/cast/disconnect', { method: 'POST' }),
  castForget: () => request<{ remembered: null }>('/cast/remembered', { method: 'DELETE' }),

  // -- app settings (onboarding, autostart, …) ------------------------------
  getSettings: () => request<AppSettings>('/settings'),
  setSettings: (body: { onboarded?: boolean; autostart?: boolean; port?: number }) =>
    request<AppSettings>('/settings', { method: 'PATCH', ...json(body) })
};

export interface AppSettings {
  onboarded: boolean;
  autostart: boolean;
  autostart_supported: boolean;
  /** Port served by the desktop app; applied at the next launch. */
  port: number;
}
