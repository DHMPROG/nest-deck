<script lang="ts">
  import { deck } from '$lib/stores/profile.svelte';
  import { categoryPalette, tokens } from '$lib/theme';

  const LONG_PRESS_MS = 500;

  let renamingId = $state<string | null>(null);
  let draft = $state('');
  let holdTimer: ReturnType<typeof setTimeout> | null = null;

  function startHold(pageId: string, name: string) {
    holdTimer = setTimeout(() => {
      holdTimer = null;
      renamingId = pageId;
      draft = name;
    }, LONG_PRESS_MS);
  }

  function endHold(index: number) {
    // A long press opens the rename field instead of switching page.
    const wasHolding = holdTimer !== null;
    if (holdTimer) clearTimeout(holdTimer);
    holdTimer = null;
    if (wasHolding) void deck.goToPage(index);
  }

  function cancelHold() {
    if (holdTimer) clearTimeout(holdTimer);
    holdTimer = null;
  }

  async function commit() {
    if (!renamingId) return;
    const id = renamingId;
    renamingId = null;
    await deck.renamePage(id, draft);
  }

  function onKey(event: KeyboardEvent) {
    if (event.key === 'Enter') void commit();
    if (event.key === 'Escape') renamingId = null;
  }
</script>

<nav class="flex items-center gap-2" aria-label="Pages">
  {#each deck.pages as page, index (page.id)}
    {@const pal = categoryPalette(page.color)}
    {@const isActive = index === deck.pageIndex}
    {#if renamingId === page.id}
      <!-- svelte-ignore a11y_autofocus -->
      <input
        class="h-11 w-32 rounded-pill border-2 px-4 text-label"
        style="border-color: {pal.accent}; background: {pal.bg}; color: {pal.text}"
        bind:value={draft}
        onblur={commit}
        onkeydown={onKey}
        autofocus
        aria-label="Renommer la page"
      />
    {:else}
      <button
        type="button"
        class="flex h-11 min-w-11 items-center gap-2 rounded-pill border-2 px-4 text-label transition-[background-color,border-color,color] duration-200"
        style="
          border-color: {isActive ? pal.accent : 'transparent'};
          background: {isActive ? pal.bg : 'transparent'};
          color: {isActive ? pal.text : tokens.surface.muted}"
        aria-current={isActive ? 'page' : undefined}
        onpointerdown={() => startHold(page.id, page.name)}
        onpointerup={() => endHold(index)}
        onpointerleave={cancelHold}
        onpointercancel={cancelHold}
      >
        <i class="ph ph-{page.icon} text-lg" aria-hidden="true"></i>
        <span>{page.name}</span>
      </button>
    {/if}
  {/each}
</nav>
