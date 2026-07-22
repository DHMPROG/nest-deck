<script lang="ts">
  import { tileIcon, tileLabel } from '$lib/types';
  import type { TileSlot } from '$lib/types';
  import type { tokens } from '$lib/theme';

  interface Props {
    slot: TileSlot;
    palette: (typeof tokens)['category'][keyof (typeof tokens)['category']];
    onedit: (slot: TileSlot) => void;
    onremove: (slot: TileSlot) => void;
    onduplicate: (slot: TileSlot) => void;
    /** Open the action's own settings — what the button actually does. */
    onconfigure: (slot: TileSlot) => void;
    /** An action was dropped from the catalog onto this slot. */
    ondropaction: (slot: TileSlot, actionId: string) => void;
  }

  let { slot, palette, onedit, onremove, onduplicate, onconfigure, ondropaction }: Props =
    $props();

  let menuOpen = $state(false);
  let dragOver = $state(false);

  function onDrop(event: DragEvent) {
    dragOver = false;
    const actionId = event.dataTransfer?.getData('text/action-id');
    if (actionId) {
      event.preventDefault();
      ondropaction(slot, actionId);
    }
  }

  function onDragOver(event: DragEvent) {
    // Only signal a drop target for catalog drags.
    if (!event.dataTransfer?.types.includes('text/action-id')) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
    dragOver = true;
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="cell"
  class:filled={slot.tile}
  class:drag-over={dragOver}
  style="--bg: {palette.bg}; --text: {palette.text}; --accent: {palette.accent}; --accent-deep: {palette.accentDeep}"
  ondragover={onDragOver}
  ondragleave={() => (dragOver = false)}
  ondrop={onDrop}
>
  {#if slot.tile}
    <button
      type="button"
      class="body"
      onclick={() => onedit(slot)}
      aria-label="Modifier {tileLabel(slot.tile)}"
    >
      <i
        class="ph-duotone ph-{tileIcon(slot.tile)} icon"
        style="color: {palette.accentDeep}"
        aria-hidden="true"
      ></i>
      <span class="label">{tileLabel(slot.tile)}</span>
    </button>

    <div class="menu-wrap">
      <button
        type="button"
        class="menu-btn"
        onclick={() => (menuOpen = !menuOpen)}
        aria-expanded={menuOpen}
        aria-label="Options de la tuile"
      >
        <i class="ph ph-dots-three-vertical" aria-hidden="true"></i>
      </button>

      {#if menuOpen}
        <ul class="menu">
          <li>
            <button
              type="button"
              onclick={() => {
                menuOpen = false;
                onedit(slot);
              }}
            >
              <i class="ph ph-pencil-simple" aria-hidden="true"></i> Modifier
            </button>
          </li>
          <li>
            <button
              type="button"
              onclick={() => {
                menuOpen = false;
                onconfigure(slot);
              }}
            >
              <i class="ph ph-sliders-horizontal" aria-hidden="true"></i>
              Configurer l’action
            </button>
          </li>
          <li>
            <button
              type="button"
              onclick={() => {
                menuOpen = false;
                onduplicate(slot);
              }}
            >
              <i class="ph ph-copy" aria-hidden="true"></i> Dupliquer
            </button>
          </li>
          <li>
            <button
              type="button"
              class="danger"
              onclick={() => {
                menuOpen = false;
                onremove(slot);
              }}
            >
              <i class="ph ph-trash" aria-hidden="true"></i> Retirer
            </button>
          </li>
        </ul>
      {/if}
    </div>
  {:else}
    <div class="placeholder">
      <i class="ph ph-plus text-3xl" aria-hidden="true"></i>
    </div>
  {/if}
</div>

<style>
  .cell {
    position: relative;
    display: grid;
    place-items: stretch;
    min-width: 0;
    min-height: 0;
    border-radius: 24px;
  }

  .cell:not(.filled) {
    border: 2px dashed var(--border);
  }

  .cell.drag-over {
    outline: 3px solid var(--accent);
    outline-offset: 2px;
  }

  .body {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    width: 100%;
    height: 100%;
    padding: 4px;
    border-radius: 24px;
    background: var(--bg);
    color: var(--text);
    box-shadow:
      0 1px 2px rgb(0 0 0 / 0.06),
      0 4px 12px rgb(0 0 0 / 0.06);
    cursor: grab;
  }

  .icon {
    font-size: 30px;
    line-height: 1;
  }

  .label {
    font-size: 12px;
    font-weight: 500;
    text-align: center;
    max-width: 100%;
    line-height: 1.2;
    /* Wrap onto a second line rather than truncating with an ellipsis; clamp
       at two lines so a long label never pushes the icon around. */
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    overflow: hidden;
    overflow-wrap: anywhere;
  }

  .placeholder {
    display: grid;
    place-items: center;
    color: var(--muted);
    opacity: 0.4;
  }

  .menu-wrap {
    position: absolute;
    top: 4px;
    right: 4px;
  }

  .menu-btn {
    display: grid;
    place-items: center;
    width: 26px;
    height: 26px;
    border-radius: 999px;
    color: var(--text);
    opacity: 0.5;
  }

  .menu-btn:hover {
    opacity: 1;
    background: rgb(255 255 255 / 0.6);
  }

  .menu {
    position: absolute;
    top: 28px;
    right: 0;
    z-index: 10;
    display: flex;
    flex-direction: column;
    min-width: 150px;
    padding: 4px;
    border-radius: 14px;
    background: var(--surface);
    box-shadow:
      0 4px 12px rgb(0 0 0 / 0.08),
      0 12px 32px rgb(0 0 0 / 0.08);
  }

  .menu button {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 10px;
    border-radius: 10px;
    font-size: 13px;
    text-align: left;
    color: var(--text);
  }

  .menu button:hover {
    background: var(--hover);
  }

  .menu .danger {
    color: #c4271e;
  }
</style>
