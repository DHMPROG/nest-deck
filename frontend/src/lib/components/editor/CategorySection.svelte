<script lang="ts">
  import { slide } from 'svelte/transition';
  import { categoryPalette } from '$lib/theme';
  import type { Action, Category } from '$lib/types';

  interface Props {
    category: Category;
    actions: Action[];
    /** Forced open while a search is active. */
    forceOpen?: boolean;
  }

  let { category, actions, forceOpen = false }: Props = $props();

  let collapsed = $state(false);
  const open = $derived(forceOpen || !collapsed);
  const pal = $derived(categoryPalette(category.color));
</script>

<section class="flex flex-col gap-2">
  <button
    type="button"
    class="flex h-10 items-center gap-2 rounded-xl px-1 text-body font-semibold hover:bg-black/5"
    onclick={() => (collapsed = !collapsed)}
    aria-expanded={open}
  >
    <span class="size-3 rounded-pill" style="background: {pal.accent}"></span>
    <span>{category.name}</span>
    <span class="text-label font-normal text-surface-muted">{actions.length}</span>
    <i
      class="ph ph-caret-down ml-auto transition-transform duration-200"
      class:rotate-180={!open}
      aria-hidden="true"
    ></i>
  </button>

  {#if open}
    <ul class="flex flex-col gap-1" transition:slide={{ duration: 160 }}>
      {#each actions as action (action.id)}
        <li>
          <!-- Native HTML5 drag: the catalog is a palette, items are copied
               onto the grid rather than moved out of the list. -->
          <div
            class="flex h-11 cursor-grab items-center gap-3 rounded-2xl px-3 text-body active:cursor-grabbing"
            style="background: {pal.bg}; color: {pal.text}"
            draggable="true"
            role="option"
            aria-selected="false"
            tabindex="0"
            ondragstart={(event) => {
              event.dataTransfer?.setData('text/action-id', action.id);
              event.dataTransfer!.effectAllowed = 'copy';
            }}
          >
            <i
              class="ph-duotone ph-{action.icon} text-xl"
              style="color: {pal.accentDeep}"
              aria-hidden="true"
            ></i>
            <span class="truncate">{action.label}</span>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>
