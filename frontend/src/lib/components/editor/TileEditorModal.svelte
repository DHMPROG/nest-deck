<script lang="ts">
  import IconPicker from './IconPicker.svelte';
  import { CATEGORY_TOKENS, categoryPalette, tokens } from '$lib/theme';
  import { tileIcon, tileLabel } from '$lib/types';
  import type { Action, Category, TileSlot } from '$lib/types';

  interface Props {
    slot: TileSlot | null;
    categories: Category[];
    actions: Action[];
    pageColor: string;
    onsave: (patch: {
      action_id?: string;
      custom_label?: string | null;
      custom_icon?: string | null;
    }) => void;
    /** Jump to the action's own settings (what the button actually does). */
    onconfigure: (actionId: string) => void;
    oncancel: () => void;
  }

  let { slot, categories, actions, pageColor, onsave, onconfigure, oncancel }: Props =
    $props();

  let actionId = $state('');
  let label = $state('');
  let icon = $state('');
  let colorOverride = $state('');

  // Re-seed the form each time a different slot is opened.
  $effect(() => {
    if (!slot?.tile) return;
    actionId = slot.tile.action_id ?? '';
    label = slot.tile.custom_label ?? '';
    icon = slot.tile.custom_icon ?? '';
    colorOverride = '';
  });

  const selected = $derived(actions.find((a) => a.id === actionId) ?? null);

  const preview = $derived({
    label: label.trim() || selected?.label || tileLabel(slot?.tile ?? null),
    icon: icon.trim() || selected?.icon || tileIcon(slot?.tile ?? null),
    type: selected?.type ?? slot?.tile?.action?.type ?? ''
  });

  const palette = $derived(categoryPalette(colorOverride || pageColor));

  const grouped = $derived(
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

  function save() {
    onsave({
      action_id: actionId || undefined,
      // Empty string clears the override rather than storing "".
      custom_label: label.trim() || null,
      custom_icon: icon.trim() || null
    });
  }
</script>

<svelte:window
  onkeydown={(event) => {
    if (event.key === 'Escape' && slot?.tile) oncancel();
  }}
/>

{#if slot?.tile}
  <!-- Clicking the backdrop closes the dialog; Escape (above) is the keyboard
       equivalent, so the backdrop itself stays out of the tab order. -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div
    class="backdrop"
    onclick={(event) => {
      if (event.target === event.currentTarget) oncancel();
    }}
  >
    <div
      class="sheet"
      role="dialog"
      aria-modal="true"
      aria-label="Modifier la tuile"
    >
      <!-- Preview, exactly as the Deck will render it. -->
      <div class="preview-pane">
        <p class="text-label uppercase tracking-wide text-app-muted">Aperçu</p>
        <div
          class="preview-tile"
          style="background: {palette.bg}; color: {palette.text}"
        >
          <i
            class="ph-duotone ph-{preview.icon} preview-icon"
            style="color: {palette.accentDeep}"
            aria-hidden="true"
          ></i>
          <span class="preview-title">{preview.label}</span>
          <span class="preview-sub">{preview.type}</span>
        </div>
      </div>

      <div class="form">
        <h2 class="text-page-heading">Modifier la tuile</h2>

        <label class="field">
          <span>Action</span>
          <select bind:value={actionId}>
            {#each grouped as group (group.category.id)}
              <optgroup label={group.category.name}>
                {#each group.items as action (action.id)}
                  <option value={action.id}>{action.label}</option>
                {/each}
              </optgroup>
            {/each}
          </select>
        </label>

        {#if actionId}
          <button type="button" class="configure" onclick={() => onconfigure(actionId)}>
            <i class="ph ph-sliders-horizontal" aria-hidden="true"></i>
            <span>
              Configurer « {selected?.label ?? 'cette action'} »
              <small>Modifier ce que fait le bouton (macro, logiciel, URL…)</small>
            </span>
            <i class="ph ph-caret-right" aria-hidden="true"></i>
          </button>
        {/if}

        <label class="field">
          <span>Libellé personnalisé</span>
          <input bind:value={label} placeholder={selected?.label ?? 'Par défaut'} />
        </label>

        <div class="field">
          <span>Icône personnalisée</span>
          <IconPicker
            value={icon || selected?.icon || ''}
            hint={label || selected?.label || ''}
            onpick={(name) => (icon = name)}
          />
          <small>
            Laissez tel quel pour garder l'icône de l'action
            {#if icon}
              · <button type="button" class="reset" onclick={() => (icon = '')}>
                réinitialiser
              </button>
            {/if}
          </small>
        </div>

        <div class="field">
          <span>Couleur (aperçu seulement)</span>
          <div class="swatches">
            <button
              type="button"
              class="swatch"
              class:on={colorOverride === ''}
              style="background: {categoryPalette(pageColor).accent}"
              onclick={() => (colorOverride = '')}
              aria-label="Couleur de la page"
            ></button>
            {#each CATEGORY_TOKENS as token (token)}
              <button
                type="button"
                class="swatch"
                class:on={colorOverride === token}
                style="background: {tokens.category[token].accent}"
                onclick={() => (colorOverride = token)}
                aria-label={token}
              ></button>
            {/each}
          </div>
          <small>La couleur d'une tuile suit celle de sa page — à changer dans la page.</small>
        </div>

        <div class="actions">
          <button type="button" class="ghost" onclick={oncancel}>Annuler</button>
          <button type="button" class="primary" onclick={save}>Enregistrer</button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  /* Entrance in CSS, not `transition:` — a Svelte transition here never
     finished its outro, which left the dialog impossible to close. */
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: grid;
    place-items: center;
    background: rgb(0 0 0 / 0.35);
    animation: backdrop-in 140ms ease-out;
  }

  @keyframes backdrop-in {
    from {
      opacity: 0;
    }
  }

  @keyframes sheet-in {
    from {
      opacity: 0;
      transform: scale(0.97);
    }
  }

  .sheet {
    animation: sheet-in 160ms cubic-bezier(0.2, 0.8, 0.2, 1);
    display: grid;
    grid-template-columns: 260px 1fr;
    gap: 24px;
    width: min(760px, 90vw);
    padding: 24px;
    border-radius: 32px;
    background: var(--surface);
    box-shadow:
      0 4px 12px rgb(0 0 0 / 0.08),
      0 12px 32px rgb(0 0 0 / 0.08);
  }

  .preview-pane {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .preview-tile {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    aspect-ratio: 224 / 193;
    border-radius: 24px;
    box-shadow:
      0 1px 2px rgb(0 0 0 / 0.06),
      0 4px 12px rgb(0 0 0 / 0.06);
  }

  .preview-icon {
    font-size: 56px;
    line-height: 1;
  }

  .preview-title {
    font-size: 18px;
    font-weight: 700;
  }

  .preview-sub {
    font-size: 13px;
    font-weight: 500;
    opacity: 0.55;
  }

  .form {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 13px;
    font-weight: 500;
  }

  .field input,
  .field select {
    height: 40px;
    padding: 0 10px;
    border: 1px solid var(--border);
    border-radius: 12px;
    font-size: 15px;
    font-weight: 400;
    background: var(--surface);
  }

  .field small {
    font-weight: 400;
    color: var(--muted);
  }

  .reset {
    color: #007aff;
    text-decoration: underline;
  }

  .swatches {
    display: flex;
    gap: 8px;
  }

  .swatch {
    width: 28px;
    height: 28px;
    border-radius: 999px;
    border: 3px solid transparent;
  }

  .swatch.on {
    border-color: rgb(0 0 0 / 0.35);
  }

  /* Sends you to the action itself — a different object from the tile, so it
     is styled as a link out rather than another field. */
  .configure {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 12px;
    border-radius: 14px;
    background: var(--hover);
    font-size: 13px;
    font-weight: 600;
    text-align: left;
  }

  .configure:hover {
    background: var(--hover);
  }

  .configure span {
    flex: 1;
    min-width: 0;
  }

  .configure small {
    display: block;
    font-weight: 400;
    color: var(--muted);
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: auto;
  }

  .actions button {
    height: 40px;
    padding: 0 18px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 600;
  }

  .ghost {
    background: var(--hover);
  }

  .primary {
    background: #1c1c1e;
    color: #fff;
  }
</style>
