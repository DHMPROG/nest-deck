<script lang="ts">
  import { fade } from 'svelte/transition';
  import { deck } from '$lib/stores/profile.svelte';
  import { status } from '$lib/stores/status.svelte';
  import { categoryPalette, tokens } from '$lib/theme';

  const palette = $derived(categoryPalette(deck.activePage?.color));

  const OK = tokens.category.meeting;
  const ERR = tokens.category.stream;
</script>

<footer class="flex h-[60px] shrink-0 items-center justify-center">
  {#if status.current}
    {@const tone = status.current.tone === 'ok' ? OK : ERR}
    {#key status.current.id}
      <p
        class="pill"
        style="background: {tone.bg}; color: {tone.text}"
        in:fade={{ duration: 150 }}
        out:fade={{ duration: 250 }}
        role="status"
      >
        <i
          class="ph ph-{status.current.tone === 'ok' ? 'check-circle' : 'warning-circle'}"
          aria-hidden="true"
        ></i>
        <span>{status.current.text}</span>
      </p>
    {/key}
  {:else if deck.error}
    <p class="pill" style="background: {ERR.bg}; color: {ERR.text}" role="status">
      <i class="ph ph-warning-circle" aria-hidden="true"></i>
      <span>{deck.error}</span>
    </p>
  {:else}
    <!-- Ambient state: which page, how full. -->
    <p
      class="pill"
      style="background: {palette.bg}; color: {palette.text}"
      in:fade={{ duration: 200 }}
    >
      <i class="ph ph-squares-four" aria-hidden="true"></i>
      <span>{deck.activePage?.name ?? '—'} · {deck.filledCount}/15 tuiles</span>
    </p>
  {/if}
</footer>

<style>
  .pill {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    height: 40px;
    padding: 0 1.25rem;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
    box-shadow:
      0 1px 2px rgb(0 0 0 / 0.06),
      0 4px 12px rgb(0 0 0 / 0.06);
  }
</style>
