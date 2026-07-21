<script lang="ts">
  /**
   * Create or edit a catalog action. Each action type needs different settings,
   * so the form swaps its fields rather than exposing a raw JSON blob.
   *
   * Not in the spec's component list: the catalog was frozen at seed time, and
   * defining your own macros and launchers is the whole point of the deck.
   */
  import { CATEGORY_TOKENS, categoryPalette, tokens } from '$lib/theme';
  import type { Action, ActionType, Category } from '$lib/types';

  interface Props {
    open: boolean;
    /** null = creating a new action. */
    action: Action | null;
    categories: Category[];
    onsave: (payload: {
      category_id: string;
      label: string;
      icon: string;
      type: ActionType;
      endpoint: string | null;
      params: Record<string, unknown>;
      /** Set instead of category_id when a new category should be created. */
      newCategory?: { name: string; color: string };
    }) => void;
    ondelete?: (action: Action) => void;
    onclose: () => void;
  }

  let { open, action, categories, onsave, ondelete, onclose }: Props = $props();

  const TYPES: { value: ActionType; label: string; hint: string }[] = [
    { value: 'pc', label: 'Macro clavier', hint: 'Envoie une combinaison de touches sur le PC.' },
    { value: 'launcher', label: 'Lancer un logiciel', hint: 'Démarre une application ou une commande.' },
    { value: 'open', label: 'Ouvrir un lien', hint: 'Ouvre une URL sur le Deck.' },
    { value: 'fetch', label: 'Appel HTTP', hint: 'Appelle une URL (webhook, domotique…).' },
    { value: 'obs', label: 'OBS', hint: 'Envoie une requête à OBS via WebSocket.' },
    { value: 'spotify', label: 'Spotify', hint: 'Contrôle la lecture Spotify.' },
    { value: 'meeting', label: 'Visioconférence', hint: 'Raccourci Meet / Zoom / Teams.' },
    { value: 'demo', label: 'Démo', hint: 'Ne fait rien, réussit toujours. Pour tester.' }
  ];

  const MEETING_PLATFORMS = ['meet', 'zoom', 'teams'];
  const MEETING_COMMANDS = ['mute', 'camera', 'hand', 'chat', 'share', 'leave'];
  const SPOTIFY_COMMANDS = ['toggle', 'play', 'pause', 'next', 'previous', 'volume', 'shuffle'];

  /** Sentinel value of the "create a category" entry in the dropdown. */
  const NEW_CATEGORY = '__new__';

  let categoryId = $state('');
  let newCategoryName = $state('');
  let newCategoryColor = $state<string>(CATEGORY_TOKENS[0]);
  let label = $state('');
  let icon = $state('lightning');
  let kind = $state<ActionType>('pc');
  let endpoint = $state('');
  let error = $state<string | null>(null);

  // Type-specific fields, kept separate so switching type does not lose input.
  let combo = $state('');
  let launch = $state('');
  let obsRequest = $state('');
  let obsArgs = $state('');
  let spotifyCommand = $state('toggle');
  let spotifyValue = $state('50');
  let meetingPlatform = $state('meet');
  let meetingCommand = $state('mute');
  let httpMethod = $state('GET');

  const current = $derived(TYPES.find((t) => t.value === kind));

  // Re-seed whenever a different action (or "new") is opened.
  $effect(() => {
    if (!open) return;
    error = null;

    if (action) {
      categoryId = action.category_id;
      label = action.label;
      icon = action.icon;
      kind = action.type;
      endpoint = action.endpoint ?? '';
      const p = action.params ?? {};
      combo = Array.isArray(p.combo) ? (p.combo as string[]).join('+') : '';
      launch = typeof p.launch === 'string' ? p.launch : '';
      obsRequest = typeof p.request === 'string' ? p.request : '';
      obsArgs = p.args ? JSON.stringify(p.args, null, 2) : '';
      spotifyCommand = typeof p.command === 'string' ? p.command : 'toggle';
      spotifyValue = p.value !== undefined ? String(p.value) : '50';
      meetingPlatform = typeof p.platform === 'string' ? p.platform : 'meet';
      meetingCommand = typeof p.command === 'string' ? p.command : 'mute';
      httpMethod = typeof p.method === 'string' ? p.method : 'GET';
    } else {
      categoryId = categories[0]?.id ?? '';
      newCategoryName = '';
      newCategoryColor = CATEGORY_TOKENS[0];
      label = '';
      icon = 'lightning';
      kind = 'pc';
      endpoint = '';
      combo = '';
      launch = '';
      obsRequest = '';
      obsArgs = '';
    }
  });

  function buildParams(): Record<string, unknown> | null {
    switch (kind) {
      case 'pc': {
        const keys = combo
          .split('+')
          .map((k) => k.trim())
          .filter(Boolean);
        if (keys.length === 0) {
          error = 'Indiquez au moins une touche, par exemple ctrl+shift+s';
          return null;
        }
        return { combo: keys };
      }
      case 'launcher': {
        if (!launch.trim()) {
          error = 'Indiquez la commande ou le programme à lancer.';
          return null;
        }
        return { launch: launch.trim() };
      }
      case 'obs': {
        if (!obsRequest.trim()) {
          error = 'Indiquez la requête OBS, par exemple SetCurrentProgramScene.';
          return null;
        }
        let args: unknown = {};
        if (obsArgs.trim()) {
          try {
            args = JSON.parse(obsArgs);
          } catch {
            error = 'Les arguments OBS ne sont pas du JSON valide.';
            return null;
          }
        }
        return { request: obsRequest.trim(), args };
      }
      case 'spotify':
        return spotifyCommand === 'volume'
          ? { command: 'volume', value: Number(spotifyValue) || 0 }
          : { command: spotifyCommand };
      case 'meeting':
        return { platform: meetingPlatform, command: meetingCommand };
      case 'fetch':
        return { method: httpMethod };
      default:
        return {};
    }
  }

  function save() {
    error = null;
    if (!label.trim()) {
      error = 'Donnez un nom au bouton.';
      return;
    }
    if (!categoryId) {
      error = 'Choisissez une catégorie.';
      return;
    }
    if (categoryId === NEW_CATEGORY && !newCategoryName.trim()) {
      error = 'Donnez un nom à la nouvelle catégorie.';
      return;
    }
    if ((kind === 'fetch' || kind === 'open') && !endpoint.trim()) {
      error = 'Indiquez une URL.';
      return;
    }

    const params = buildParams();
    if (params === null) return;

    onsave({
      category_id: categoryId === NEW_CATEGORY ? '' : categoryId,
      label: label.trim(),
      icon: icon.trim() || 'lightning',
      type: kind,
      endpoint: endpoint.trim() || null,
      params,
      newCategory:
        categoryId === NEW_CATEGORY
          ? { name: newCategoryName.trim(), color: newCategoryColor }
          : undefined
    });
  }
</script>

<svelte:window
  onkeydown={(event) => {
    if (event.key === 'Escape' && open) onclose();
  }}
/>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- Entrance animated in CSS rather than with `transition:`. A Svelte
       transition here never finished its outro, leaving the dialog mounted
       after `open` went false — it simply could not be closed. -->
  <div
    class="backdrop"
    onclick={(event) => {
      if (event.target === event.currentTarget) onclose();
    }}
  >
    <div
      class="sheet"
      role="dialog"
      aria-modal="true"
      aria-label={action ? 'Modifier une action' : 'Nouvelle action'}
    >
      <header class="head">
        <h2 class="text-page-heading">
          {action ? 'Modifier l’action' : 'Nouvelle action'}
        </h2>
        <button type="button" class="icon-btn" onclick={onclose} aria-label="Fermer">
          <i class="ph ph-x" aria-hidden="true"></i>
        </button>
      </header>

      <div class="body">
        <label class="field">
          <span>Nom du bouton</span>
          <input bind:value={label} placeholder="Ex. Couper le micro" />
        </label>

        <div class="row">
          <label class="field">
            <span>Catégorie</span>
            <select bind:value={categoryId}>
              {#each [...categories].sort((a, b) => CATEGORY_TOKENS.indexOf(a.color as never) - CATEGORY_TOKENS.indexOf(b.color as never)) as category (category.id)}
                <option value={category.id}>{category.name}</option>
              {/each}
              <option value={NEW_CATEGORY}>＋ Nouvelle catégorie…</option>
            </select>
          </label>

          <label class="field">
            <span>Icône Phosphor</span>
            <input bind:value={icon} placeholder="ex. keyboard" />
          </label>
        </div>

        {#if categoryId === NEW_CATEGORY}
          <div class="new-cat">
            <label class="field">
              <span>Nom de la nouvelle catégorie</span>
              <input bind:value={newCategoryName} placeholder="Ex. Domotique" />
            </label>
            <div class="field">
              <span>Couleur</span>
              <div class="swatches">
                {#each CATEGORY_TOKENS as token (token)}
                  <button
                    type="button"
                    class="swatch"
                    class:on={newCategoryColor === token}
                    style="background: {tokens.category[token].accent}"
                    onclick={() => (newCategoryColor = token)}
                    aria-label={token}
                  ></button>
                {/each}
              </div>
              <small>
                La couleur reprend l’un des cinq tons du deck — c’est celle des
                pastilles du catalogue.
              </small>
            </div>
          </div>
        {/if}

        <label class="field">
          <span>Type d’action</span>
          <select bind:value={kind}>
            {#each TYPES as type (type.value)}
              <option value={type.value}>{type.label}</option>
            {/each}
          </select>
          <small>{current?.hint}</small>
        </label>

        <!-- Type-specific settings -->
        {#if kind === 'pc'}
          <label class="field">
            <span>Combinaison de touches</span>
            <input bind:value={combo} placeholder="ctrl+shift+s" />
            <small>
              Séparez par <code>+</code>. Modificateurs : <code>ctrl</code>,
              <code>shift</code>, <code>alt</code>, <code>cmd</code> (touche Windows).
              Touches spéciales : <code>enter</code>, <code>esc</code>, <code>f1</code>…
            </small>
          </label>
        {:else if kind === 'launcher'}
          <label class="field">
            <span>Programme ou commande</span>
            <input bind:value={launch} placeholder="notepad.exe" />
            <small>
              S’exécute sur la machine qui fait tourner le backend. Un chemin avec
              des espaces doit être entre guillemets.
            </small>
          </label>
        {:else if kind === 'open' || kind === 'fetch'}
          <label class="field">
            <span>URL</span>
            <input bind:value={endpoint} placeholder="https://exemple.fr/webhook" />
          </label>
          {#if kind === 'fetch'}
            <label class="field">
              <span>Méthode HTTP</span>
              <select bind:value={httpMethod}>
                {#each ['GET', 'POST', 'PUT', 'DELETE'] as method (method)}
                  <option value={method}>{method}</option>
                {/each}
              </select>
            </label>
          {/if}
        {:else if kind === 'obs'}
          <label class="field">
            <span>Requête OBS</span>
            <input bind:value={obsRequest} placeholder="SetCurrentProgramScene" />
          </label>
          <label class="field">
            <span>Arguments (JSON)</span>
            <textarea bind:value={obsArgs} rows="3" placeholder={'{ "sceneName": "Camera" }'}
            ></textarea>
          </label>
        {:else if kind === 'spotify'}
          <label class="field">
            <span>Commande</span>
            <select bind:value={spotifyCommand}>
              {#each SPOTIFY_COMMANDS as command (command)}
                <option value={command}>{command}</option>
              {/each}
            </select>
          </label>
          {#if spotifyCommand === 'volume'}
            <label class="field">
              <span>Volume (%)</span>
              <input type="number" min="0" max="100" bind:value={spotifyValue} />
            </label>
          {/if}
        {:else if kind === 'meeting'}
          <div class="row">
            <label class="field">
              <span>Plateforme</span>
              <select bind:value={meetingPlatform}>
                {#each MEETING_PLATFORMS as platform (platform)}
                  <option value={platform}>{platform}</option>
                {/each}
              </select>
            </label>
            <label class="field">
              <span>Commande</span>
              <select bind:value={meetingCommand}>
                {#each MEETING_COMMANDS as command (command)}
                  <option value={command}>{command}</option>
                {/each}
              </select>
            </label>
          </div>
        {/if}

        {#if error}
          <p class="error">{error}</p>
        {/if}
      </div>

      <footer class="actions">
        {#if action && ondelete}
          <button type="button" class="danger" onclick={() => ondelete(action)}>
            <i class="ph ph-trash" aria-hidden="true"></i> Supprimer
          </button>
        {/if}
        <span class="spacer"></span>
        <button type="button" class="ghost" onclick={onclose}>Annuler</button>
        <button type="button" class="primary" onclick={save}>Enregistrer</button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 70;
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
    display: flex;
    flex-direction: column;
    width: min(560px, 92vw);
    max-height: 88vh;
    padding: 24px;
    border-radius: 32px;
    background: #fff;
    box-shadow:
      0 4px 12px rgb(0 0 0 / 0.08),
      0 12px 32px rgb(0 0 0 / 0.08);
  }

  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .icon-btn {
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    border-radius: 999px;
    font-size: 20px;
  }

  .body {
    display: flex;
    flex-direction: column;
    gap: 14px;
    overflow-y: auto;
  }

  .row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 13px;
    font-weight: 500;
    min-width: 0;
  }

  .field input,
  .field select,
  .field textarea {
    padding: 10px;
    border: 1px solid rgb(0 0 0 / 0.12);
    border-radius: 12px;
    font-size: 15px;
    font-weight: 400;
    font-family: inherit;
    background: #fff;
  }

  .field textarea {
    resize: vertical;
    font-family: ui-monospace, monospace;
    font-size: 13px;
  }

  .field small {
    font-weight: 400;
    color: #8e8e93;
    line-height: 1.45;
  }

  .field code {
    padding: 1px 4px;
    border-radius: 4px;
    background: rgb(0 0 0 / 0.05);
    font-size: 12px;
  }

  /* Set apart so it is obvious these fields create something new. */
  .new-cat {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 14px;
    border-radius: 16px;
    background: rgb(0 0 0 / 0.03);
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

  .error {
    padding: 10px 12px;
    border-radius: 12px;
    background: #ffe5e4;
    color: #4a0f0a;
    font-size: 13px;
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 18px;
  }

  .spacer {
    flex: 1;
  }

  .actions button {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 40px;
    padding: 0 18px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 600;
  }

  .ghost {
    background: rgb(0 0 0 / 0.05);
  }

  .primary {
    background: #1c1c1e;
    color: #fff;
  }

  .danger {
    background: #ffe5e4;
    color: #c4271e;
  }
</style>
