/**
 * Server-Sent Events subscription.
 *
 * The backend emits one named event per mutation (`tile_updated`,
 * `page_updated`, `profile_activated`, ...) plus a `ping` every 15s so idle
 * connections are not dropped by a proxy or by the Nest Hub's Chromium.
 *
 * `EventSource` reconnects on its own, so the only thing to handle here is
 * surfacing the connection state.
 */

const BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');

export interface EventHandlers {
  profile_activated?: (payload: { profile_id: string }) => void;
  profile_updated?: (payload: { profile_id: string }) => void;
  page_updated?: (payload: { page_id: string }) => void;
  tile_updated?: (payload: { tile_id: string; page_id: string }) => void;
  action_fired?: (payload: { tile_id: string; status: string }) => void;
  /** Connection came up (also fires after an automatic reconnect). */
  onopen?: () => void;
  /** Connection dropped; EventSource will retry by itself. */
  onerror?: () => void;
}

const EVENT_NAMES = [
  'profile_activated',
  'profile_updated',
  'page_updated',
  'tile_updated',
  'action_fired'
] as const;

/**
 * Opens the stream. Returns a function that closes it — call it on unmount.
 * Returns a no-op during SSR, where `EventSource` does not exist.
 */
export function subscribeToEvents(handlers: EventHandlers): () => void {
  if (typeof EventSource === 'undefined') return () => {};

  const source = new EventSource(`${BASE}/api/events`);

  source.onopen = () => handlers.onopen?.();
  source.onerror = () => handlers.onerror?.();

  for (const name of EVENT_NAMES) {
    const handler = handlers[name];
    if (!handler) continue;
    source.addEventListener(name, (event) => {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (handler as (payload: any) => void)(JSON.parse((event as MessageEvent).data));
      } catch {
        // A malformed frame must not kill the stream.
      }
    });
  }

  return () => source.close();
}
