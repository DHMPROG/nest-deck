<script lang="ts">
  /**
   * Touch-friendly action picker, opened from an empty slot in edit mode.
   * Not in the original component list, but the Deck needs a way to add a tile
   * without walking over to the desktop Editor.
   */

  import { api } from '$lib/services/api';
  import { CATEGORY_TOKENS, categoryPalette } from '$lib/theme';
  import type { Action, Category } from '$lib/types';

  interface Props {
    open: boolean;
    onpick: (actionId: string) => void;
    onclose: () => void;
  }

  let { open, onpick, onclose }: Props = $props();

  let categories = $state<Category[]>([]);
  let actions = $state<Action[]>([]);
  let loaded = $state(false);
  let error = $state<string | null>(null);

  const groups = $derived(
    [...categories]
      .sort(
        (a, b) =>
          CATEGORY_TOKENS.indexOf(a.color as never) -
          CATEGORY_TOKENS.indexOf(b.color as never)
      )
      .map((category) => ({
        category,
        items: actions.filter((a) => a.category_id === category.id)
      }))
      .filter((group) => group.items.length > 0)
  );

  // Fetch once, the first time the picker is opened.
  $effect(() => {
    if (!open || loaded) return;
    void (async () => {
      try {
        [categories, actions] = await Promise.all([
          api.listCategories(),
          api.listActions()
        ]);
        loaded = true;
        error = null;
      } catch (cause) {
        error = cause instanceof Error ? cause.message : String(cause);
      }
    })();
  });
</script>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="backdrop"
    onpointerup={(event) => {
      if (event.target === event.currentTarget) onclose();
    }}
  >
    <div
      class="sheet"
      role="dialog"
      aria-modal="true"
      aria-label="Choisir une action"
    >
      <header class="sheet-head">
        <h2 class="text-page-heading">Choisir une action</h2>
        <button type="button" class="close" onpointerup={onclose} aria-label="Fermer">
          <i class="ph ph-x" aria-hidden="true"></i>
        </button>
      </header>

      <div class="scroll">
        {#if error}
          <p class="text-body">{error}</p>
        {:else if !loaded}
          <p class="text-body">Chargement…</p>
        {:else}
          {#each groups as group (group.category.id)}
            {@const pal = categoryPalette(group.category.color)}
            <section>
              <h3 class="group-title">
                <span class="dot" style="background: {pal.accent}"></span>
                {group.category.name}
              </h3>
              <div class="items">
                {#each group.items as action (action.id)}
                  <button
                    type="button"
                    class="item"
                    style="background: {pal.bg}; color: {pal.text}"
                    onpointerup={(event) => {
                      event.stopPropagation();
                      onpick(action.id);
                    }}
                  >
                    <i
                      class="ph-duotone ph-{action.icon} text-2xl"
                      style="color: {pal.accentDeep}"
                      aria-hidden="true"
                    ></i>
                    <span class="truncate">{action.label}</span>
                  </button>
                {/each}
              </div>
            </section>
          {/each}
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  /* Entrance in CSS, not `transition:` — a Svelte transition here never
     finished its outro, which left the sheet impossible to close. */
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: grid;
    place-items: center;
    background: rgb(0 0 0 / 0.35);
    animation: backdrop-in 150ms ease-out;
  }

  @keyframes backdrop-in {
    from {
      opacity: 0;
    }
  }

  @keyframes sheet-in {
    from {
      opacity: 0;
      transform: scale(0.96);
    }
  }

  .sheet {
    animation: sheet-in 180ms cubic-bezier(0.2, 0.8, 0.2, 1);
    display: flex;
    flex-direction: column;
    width: min(900px, 88vw);
    max-height: 80vh;
    padding: 24px;
    border-radius: 32px;
    background: var(--surface);
    box-shadow:
      0 4px 12px rgb(0 0 0 / 0.08),
      0 12px 32px rgb(0 0 0 / 0.08);
  }

  .sheet-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .close {
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    border-radius: 999px;
    font-size: 20px;
  }

  .scroll {
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .group-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    font-size: 15px;
    font-weight: 600;
  }

  .dot {
    width: 12px;
    height: 12px;
    border-radius: 999px;
  }

  .items {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 8px;
  }

  .item {
    display: flex;
    align-items: center;
    gap: 12px;
    /* Comfortable touch target on the Hub. */
    height: 56px;
    padding: 0 16px;
    border-radius: 16px;
    font-size: 15px;
    text-align: left;
  }
</style>
