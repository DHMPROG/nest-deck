<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { theme } from '$lib/stores/theme.svelte';

  let { children } = $props();

  // Apply the saved theme to both the Deck and the Editor.
  onMount(() => theme.init());
</script>

{@render children()}
