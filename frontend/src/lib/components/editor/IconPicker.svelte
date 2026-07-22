<script lang="ts" module>
  /**
   * The list of icon names is read straight from the Phosphor stylesheet the
   * app already loads, rather than hardcoded. It cannot drift from the
   * installed version, and costs one pass over the CSSOM on first use.
   */
  let cache: string[] | null = null;

  export function availableIcons(): string[] {
    if (cache) return cache;
    if (typeof document === 'undefined') return [];

    const names = new Set<string>();
    for (const sheet of Array.from(document.styleSheets)) {
      let rules: CSSRuleList;
      try {
        rules = sheet.cssRules;
      } catch {
        continue; // cross-origin sheet, nothing to read
      }
      for (const rule of Array.from(rules)) {
        const selector = (rule as CSSStyleRule).selectorText;
        if (!selector || !selector.includes('.ph-')) continue;
        for (const match of selector.matchAll(/\.ph-([a-z0-9-]+)(?=::?before)/g)) {
          const name = match[1];
          // `.ph-duotone` / `.ph-fill` are weights, not icons.
          if (!['duotone', 'fill', 'bold', 'light', 'thin'].includes(name)) {
            names.add(name);
          }
        }
      }
    }

    cache = [...names].sort();
    return cache;
  }
</script>

<script lang="ts">
  interface Props {
    /** Currently selected Phosphor name, without the `ph-` prefix. */
    value: string;
    /** Seeds the search, typically the button's label. */
    hint?: string;
    onpick: (icon: string) => void;
  }

  let { value, hint = '', onpick }: Props = $props();

  const MAX_SHOWN = 120;

  let query = $state('');
  let icons = $state<string[]>([]);
  let seeded = $state(false);

  $effect(() => {
    if (icons.length === 0) icons = availableIcons();
  });

  // Start from the button's own words — "Bloc-notes" surfaces note icons.
  $effect(() => {
    if (seeded || icons.length === 0) return;
    seeded = true;
    const words = hint
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((w) => w.length > 2);
    for (const word of words) {
      if (icons.some((i) => i.includes(word))) {
        query = word;
        return;
      }
    }
  });

  const results = $derived(
    (() => {
      const needle = query.trim().toLowerCase();
      if (!needle) return icons.slice(0, MAX_SHOWN);
      // Prefix matches first: searching "note" should lead with `note`, not
      // `music-notes-simple`.
      const starts = icons.filter((i) => i.startsWith(needle));
      const contains = icons.filter((i) => !i.startsWith(needle) && i.includes(needle));
      return [...starts, ...contains].slice(0, MAX_SHOWN);
    })()
  );

  const total = $derived(
    query.trim()
      ? icons.filter((i) => i.includes(query.trim().toLowerCase())).length
      : icons.length
  );
</script>

<div class="picker">
  <div class="head">
    <span class="current">
      <i class="ph-duotone ph-{value || 'question'}" aria-hidden="true"></i>
      <code>{value || '—'}</code>
    </span>
    <input
      class="search"
      bind:value={query}
      placeholder="Chercher une icône…"
      aria-label="Chercher une icône"
    />
  </div>

  <div class="grid" role="listbox" aria-label="Icônes disponibles">
    {#each results as name (name)}
      <button
        type="button"
        class="icon"
        class:on={name === value}
        onclick={() => onpick(name)}
        title={name}
        aria-label={name}
        role="option"
        aria-selected={name === value}
      >
        <i class="ph-duotone ph-{name}" aria-hidden="true"></i>
      </button>
    {:else}
      <p class="empty">Aucune icône ne correspond.</p>
    {/each}
  </div>

  <small>
    {#if icons.length === 0}
      Chargement des icônes…
    {:else}
      {Math.min(results.length, MAX_SHOWN)} affichées sur {total}
      {#if total > MAX_SHOWN}— affinez la recherche{/if}
    {/if}
  </small>
</div>

<style>
  .picker {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: rgb(0 0 0 / 0.02);
  }

  .head {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .current {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--surface);
    border: 1px solid var(--border);
    font-size: 20px;
    flex-shrink: 0;
  }

  .current code {
    font-size: 11px;
    color: var(--muted);
    max-width: 110px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .search {
    flex: 1;
    min-width: 0;
    height: 34px;
    padding: 0 10px;
    border: 1px solid var(--border);
    border-radius: 10px;
    font-size: 14px;
    font-weight: 400;
    background: var(--surface);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(38px, 1fr));
    gap: 4px;
    max-height: 168px;
    overflow-y: auto;
  }

  .icon {
    display: grid;
    place-items: center;
    aspect-ratio: 1;
    border-radius: 8px;
    font-size: 22px;
    color: var(--text);
  }

  .icon:hover {
    background: var(--hover);
  }

  .icon.on {
    background: #1c1c1e;
    color: #fff;
  }

  .empty {
    grid-column: 1 / -1;
    padding: 12px;
    font-size: 13px;
    color: var(--muted);
  }

  small {
    font-size: 11px;
    font-weight: 400;
    color: var(--muted);
  }
</style>
