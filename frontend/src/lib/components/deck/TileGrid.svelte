<script lang="ts">
  import { dndzone } from 'svelte-dnd-action';
  import { fly } from 'svelte/transition';
  import ActionPicker from './ActionPicker.svelte';
  import Tile from './Tile.svelte';
  import { deck } from '$lib/stores/profile.svelte';
  import { editMode } from '$lib/stores/editMode.svelte';
  import { categoryPalette, GRID } from '$lib/theme';
  import type { TileSlot } from '$lib/types';

  interface Item {
    id: string;
    slot: TileSlot;
  }

  const FLIP_MS = 180;
  const SWIPE_MIN_X = 60;
  const SWIPE_MAX_Y = 50;

  const palette = $derived(categoryPalette(deck.activePage?.color));

  /** Identity follows the tile, so dnd tracks content rather than position. */
  const idOf = (slot: TileSlot) =>
    slot.tile ? slot.tile.id : `empty-${slot.row}-${slot.col}`;

  const toItems = (slots: TileSlot[]): Item[] =>
    slots.map((slot) => ({ id: idOf(slot), slot }));

  let items = $state<Item[]>([]);

  // Mirror the store into the local list the dnd zone mutates while dragging.
  $effect(() => {
    items = toItems(deck.slots);
  });

  function handleConsider(event: CustomEvent<{ items: Item[] }>) {
    items = event.detail.items;
  }

  function handleFinalize(event: CustomEvent<{ items: Item[]; info: { id: string } }>) {
    const draggedId = event.detail.info.id;
    // deck.slots is untouched during the drag, so it is the pre-drag order.
    const from = deck.slots.findIndex((slot) => idOf(slot) === draggedId);
    const to = event.detail.items.findIndex((item) => item.id === draggedId);

    // Revert the visual list; swapSlots re-renders from the server result.
    items = toItems(deck.slots);
    if (from >= 0 && to >= 0 && from !== to) void deck.swapSlots(from, to);
  }

  // -- add / remove in edit mode --------------------------------------------
  let pickerFor = $state<TileSlot | null>(null);

  function openPicker(slot: TileSlot) {
    pickerFor = slot;
  }

  async function pick(actionId: string) {
    const slot = pickerFor;
    pickerFor = null;
    if (slot) await deck.placeAction(slot.row, slot.col, actionId);
  }

  async function remove(slot: TileSlot) {
    if (slot.tile) await deck.clearTile(slot.tile.id);
  }

  // -- swipe between pages --------------------------------------------------
  let swipeStart: { x: number; y: number } | null = null;

  function onPointerDown(event: PointerEvent) {
    swipeStart = { x: event.clientX, y: event.clientY };
  }

  function onPointerUp(event: PointerEvent) {
    if (!swipeStart || editMode.active) {
      swipeStart = null;
      return;
    }
    const dx = event.clientX - swipeStart.x;
    const dy = event.clientY - swipeStart.y;
    swipeStart = null;

    if (Math.abs(dx) < SWIPE_MIN_X || Math.abs(dy) > SWIPE_MAX_Y) return;
    if (dx < 0) void deck.nextPage();
    else void deck.previousPage();
  }
</script>

{#key deck.activePage?.id}
  <!-- Swipe is a touch enhancement; the page tabs and arrow keys do the same
       thing, so this layer stays out of the accessibility tree. -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="wrapper"
    in:fly={{ x: 12 * deck.direction, duration: 200, opacity: 0 }}
    onpointerdown={onPointerDown}
    onpointerup={onPointerUp}
    onpointercancel={() => (swipeStart = null)}
  >
    <div
      class="grid"
      style="grid-template-columns: repeat({GRID.cols}, 1fr); grid-template-rows: repeat({GRID.rows}, 1fr)"
      use:dndzone={{
        items,
        dragDisabled: !editMode.active,
        flipDurationMs: FLIP_MS,
        dropTargetStyle: {},
        type: 'deck-tiles'
      }}
      onconsider={handleConsider}
      onfinalize={handleFinalize}
    >
      {#each items as item, index (item.id)}
        <Tile
          slot={item.slot}
          {index}
          {palette}
          onadd={openPicker}
          onremove={remove}
        />
      {/each}
    </div>
  </div>
{/key}

<ActionPicker open={pickerFor !== null} onpick={pick} onclose={() => (pickerFor = null)} />

<style>
  .wrapper {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .grid {
    display: grid;
    gap: 24px;
    padding: 0 32px;
    flex: 1;
    min-height: 0;
  }

  /* The dnd library needs the children to be laid out by us, not outlined. */
  .grid :global(> *) {
    min-width: 0;
    min-height: 0;
  }
</style>
