<script lang="ts">
  import { dndzone } from 'svelte-dnd-action';
  import EditableTile from './EditableTile.svelte';
  import { categoryPalette, gridOf } from '$lib/theme';
  import type { Page, TileSlot } from '$lib/types';

  interface Props {
    page: Page | null;
    slots: TileSlot[];
    onswap: (fromIndex: number, toIndex: number) => void;
    onedit: (slot: TileSlot) => void;
    onremove: (slot: TileSlot) => void;
    onduplicate: (slot: TileSlot) => void;
    onconfigure: (slot: TileSlot) => void;
    ondropaction: (slot: TileSlot, actionId: string) => void;
  }

  let {
    page,
    slots,
    onswap,
    onedit,
    onremove,
    onduplicate,
    onconfigure,
    ondropaction
  }: Props = $props();

  interface Item {
    id: string;
    slot: TileSlot;
  }

  const palette = $derived(categoryPalette(page?.color));
  const grid = $derived(gridOf(page));

  const idOf = (slot: TileSlot) =>
    slot.tile ? slot.tile.id : `empty-${slot.row}-${slot.col}`;

  const toItems = (list: TileSlot[]): Item[] =>
    list.map((slot) => ({ id: idOf(slot), slot }));

  let items = $state<Item[]>([]);

  $effect(() => {
    items = toItems(slots);
  });

  function handleConsider(event: CustomEvent<{ items: Item[] }>) {
    items = event.detail.items;
  }

  function handleFinalize(event: CustomEvent<{ items: Item[]; info: { id: string } }>) {
    const draggedId = event.detail.info.id;
    // `slots` is untouched during the drag, so it holds the pre-drag order.
    const from = slots.findIndex((slot) => idOf(slot) === draggedId);
    const to = event.detail.items.findIndex((item) => item.id === draggedId);

    items = toItems(slots);
    if (from >= 0 && to >= 0 && from !== to) onswap(from, to);
  }
</script>

<div
  class="grid aspect-[1280/660] w-full gap-4 rounded-container bg-app-sunken p-5"
  style="grid-template-columns: repeat({grid.cols}, 1fr); grid-template-rows: repeat({grid.rows}, 1fr)"
  use:dndzone={{ items, flipDurationMs: 160, dropTargetStyle: {}, type: 'editor-tiles' }}
  onconsider={handleConsider}
  onfinalize={handleFinalize}
>
  {#each items as item (item.id)}
    <EditableTile
      slot={item.slot}
      {palette}
      {onedit}
      {onremove}
      {onduplicate}
      {onconfigure}
      {ondropaction}
    />
  {/each}
</div>
