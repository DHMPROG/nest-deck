<script lang="ts">
  /**
   * Google drops a cast session after ~10 minutes of an "idle" page. Reloading
   * just under that window keeps the Deck on screen indefinitely — this is the
   * `ha-catt-fix` trick, embedded rather than pulled in as a dependency.
   *
   * Renders nothing.
   */
  import { onMount } from 'svelte';
  import { api } from '$lib/services/api';

  interface Props {
    /** Minutes between reloads. Must stay below Google's 10-minute timeout. */
    minutes?: number;
    /** Set false in the Editor's live-preview iframe. */
    enabled?: boolean;
  }

  let { minutes = 9, enabled = true }: Props = $props();

  /**
   * Reload only when the server answers: reloading while the PC is off would
   * swap a working (cached) Deck for the browser's error page, for good.
   */
  async function reloadIfReachable() {
    try {
      await api.health();
      location.reload();
    } catch {
      /* server unreachable: keep the current page on screen */
    }
  }

  onMount(() => {
    if (!enabled) return;
    const timer = setInterval(reloadIfReachable, minutes * 60 * 1000);
    return () => clearInterval(timer);
  });
</script>
