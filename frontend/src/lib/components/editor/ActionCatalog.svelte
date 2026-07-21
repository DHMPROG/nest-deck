<script lang="ts">
  import CategorySection from './CategorySection.svelte';
  import { CATEGORY_TOKENS } from '$lib/theme';
  import type { Action, Category } from '$lib/types';

  interface Props {
    categories: Category[];
    actions: Action[];
    oncreate: () => void;
    onedit: (action: Action) => void;
  }

  let { categories, actions, oncreate, onedit }: Props = $props();

  let query = $state('');

  const filtered = $derived(
    query.trim()
      ? actions.filter((a) => a.label.toLowerCase().includes(query.trim().toLowerCase()))
      : actions
  );

  // Canonical order (Stream, PC, Games, Meeting, Media), not the backend's
  // alphabetical sort.
  const groups = $derived(
    [...categories]
      .sort(
        (a, b) =>
          CATEGORY_TOKENS.indexOf(a.color as never) -
          CATEGORY_TOKENS.indexOf(b.color as never)
      )
      .map((category) => ({
        category,
        items: filtered.filter((a) => a.category_id === category.id)
      }))
      .filter((group) => group.items.length > 0)
  );
</script>

<div class="flex min-h-0 flex-col gap-3">
  <label class="relative block shrink-0">
    <i
      class="ph ph-magnifying-glass pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-surface-muted"
      aria-hidden="true"
    ></i>
    <input
      class="h-11 w-full rounded-pill border border-black/10 bg-black/[0.02] pr-3 pl-9 text-body"
      placeholder="Rechercher une action"
      bind:value={query}
      aria-label="Rechercher une action"
    />
  </label>

  <div class="flex min-h-0 flex-col gap-4 overflow-y-auto">
    {#if groups.length === 0}
      <p class="text-label text-surface-muted">Aucune action ne correspond.</p>
    {:else}
      {#each groups as group (group.category.id)}
        <CategorySection
          category={group.category}
          actions={group.items}
          forceOpen={query.trim().length > 0}
          {onedit}
        />
      {/each}
    {/if}
  </div>

  <button
    type="button"
    class="flex h-11 shrink-0 items-center justify-center gap-2 rounded-xl border border-dashed border-black/15 text-label text-surface-muted hover:bg-black/5"
    onclick={oncreate}
  >
    <i class="ph ph-plus" aria-hidden="true"></i>
    Nouvelle action
  </button>
</div>
