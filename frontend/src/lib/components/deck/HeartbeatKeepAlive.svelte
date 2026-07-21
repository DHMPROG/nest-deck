<script lang="ts">
  /**
   * Google drops a cast session after ~10 minutes of an "idle" page. Reloading
   * just under that window keeps the Deck on screen indefinitely — this is the
   * `ha-catt-fix` trick, embedded rather than pulled in as a dependency.
   *
   * Renders nothing.
   */
  import { onMount } from 'svelte';

  interface Props {
    /** Minutes between reloads. Must stay below Google's 10-minute timeout. */
    minutes?: number;
    /** Set false in the Editor's live-preview iframe. */
    enabled?: boolean;
  }

  let { minutes = 9, enabled = true }: Props = $props();

  onMount(() => {
    if (!enabled) return;
    const timer = setInterval(() => location.reload(), minutes * 60 * 1000);
    return () => clearInterval(timer);
  });
</script>
