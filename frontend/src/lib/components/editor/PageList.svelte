<script lang="ts">
  import { dndzone } from 'svelte-dnd-action';
  import { CATEGORY_TOKENS, categoryPalette } from '$lib/theme';
  import type { Page } from '$lib/types';

  interface Props {
    pages: Page[];
    activeId: string | null;
    onselect: (id: string) => void;
    oncreate: (name: string, color: string) => void;
    ondelete: (id: string) => void;
    onreorder: (id: string, position: number) => void;
  }

  let { pages, activeId, onselect, oncreate, ondelete, onreorder }: Props = $props();

  interface Item {
    id: string;
    page: Page;
  }

  let items = $state<Item[]>([]);

  $effect(() => {
    items = pages.map((page) => ({ id: page.id, page }));
  });

  function handleConsider(event: CustomEvent<{ items: Item[] }>) {
    items = event.detail.items;
  }

  function handleFinalize(event: CustomEvent<{ items: Item[]; info: { id: string } }>) {
    const id = event.detail.info.id;
    const to = event.detail.items.findIndex((item) => item.id === id);
    items = event.detail.items;
    if (to >= 0) onreorder(id, to);
  }

  // Inline creation rather than prompt(): native dialogs block the page and
  // cannot be styled to match the rest of the editor.
  let creating = $state(false);
  let draft = $state('');
  /** Two-step delete, so a stray click cannot destroy a page. */
  let confirmingId = $state<string | null>(null);
  let confirmTimer: ReturnType<typeof setTimeout> | null = null;

  function submitCreate() {
    const name = draft.trim();
    creating = false;
    draft = '';
    if (!name) return;
    // Cycle through the five tokens so a new page is never colourless.
    const color = CATEGORY_TOKENS[pages.length % CATEGORY_TOKENS.length];
    oncreate(name, color);
  }

  function armDelete(id: string) {
    if (confirmTimer) clearTimeout(confirmTimer);
    if (confirmingId === id) {
      confirmingId = null;
      ondelete(id);
      return;
    }
    confirmingId = id;
    confirmTimer = setTimeout(() => (confirmingId = null), 3000);
  }
</script>

<div class="flex min-h-0 flex-1 flex-col gap-2">
  <h2 class="text-label uppercase tracking-wide text-surface-muted">Pages</h2>

  <ul
    class="flex flex-col gap-1 overflow-y-auto"
    use:dndzone={{ items, flipDurationMs: 160, dropTargetStyle: {} }}
    onconsider={handleConsider}
    onfinalize={handleFinalize}
  >
    {#each items as item (item.id)}
      {@const pal = categoryPalette(item.page.color)}
      <li class="group flex items-center gap-1">
        <button
          type="button"
          class="flex h-11 min-w-0 flex-1 items-center gap-3 rounded-2xl px-3 text-left text-body hover:bg-black/5"
          style={item.page.id === activeId
            ? `background: ${pal.bg}; color: ${pal.text}`
            : ''}
          onclick={() => onselect(item.page.id)}
        >
          <span class="size-3 shrink-0 rounded-pill" style="background: {pal.accent}"></span>
          <span class="truncate">{item.page.name}</span>
        </button>
        <button
          type="button"
          class="grid size-9 shrink-0 place-items-center rounded-lg opacity-0 hover:bg-black/5 group-hover:opacity-100 focus:opacity-100"
          class:!opacity-100={confirmingId === item.page.id}
          class:text-cat-stream-accent-deep={confirmingId === item.page.id}
          class:text-surface-muted={confirmingId !== item.page.id}
          onclick={() => armDelete(item.page.id)}
          aria-label={confirmingId === item.page.id
            ? `Confirmer la suppression de ${item.page.name}`
            : `Supprimer la page ${item.page.name}`}
          title={confirmingId === item.page.id ? 'Cliquer à nouveau pour confirmer' : 'Supprimer'}
        >
          <i
            class="ph {confirmingId === item.page.id ? 'ph-check' : 'ph-trash'}"
            aria-hidden="true"
          ></i>
        </button>
      </li>
    {/each}
  </ul>

  {#if creating}
    <!-- svelte-ignore a11y_autofocus -->
    <input
      class="h-10 shrink-0 rounded-xl border border-black/15 px-3 text-body"
      placeholder="Nom de la page"
      bind:value={draft}
      onblur={submitCreate}
      onkeydown={(event) => {
        if (event.key === 'Enter') submitCreate();
        if (event.key === 'Escape') {
          creating = false;
          draft = '';
        }
      }}
      autofocus
      aria-label="Nom de la nouvelle page"
    />
  {:else}
    <button
      type="button"
      class="flex h-10 shrink-0 items-center justify-center gap-2 rounded-xl border border-dashed border-black/15 text-label text-surface-muted hover:bg-black/5"
      onclick={() => (creating = true)}
    >
      <i class="ph ph-plus" aria-hidden="true"></i>
      Nouvelle page
    </button>
  {/if}
</div>
