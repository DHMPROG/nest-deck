<script lang="ts">
  /**
   * Create or edit a catalog action. Each action type needs different settings,
   * so the form swaps its fields rather than exposing a raw JSON blob.
   *
   * Not in the spec's component list: the catalog was frozen at seed time, and
   * defining your own macros and launchers is the whole point of the deck.
   */
  import IconPicker from './IconPicker.svelte';
  import ObsActionFields from './ObsActionFields.svelte';
  import { api } from '$lib/services/api';
  import { CATEGORY_TOKENS, categoryPalette, tokens } from '$lib/theme';
  import type {
    Action,
    ActionType,
    BrowseResult,
    Category,
    InstalledApp
  } from '$lib/types';

  type Payload = {
    category_id: string;
    label: string;
    icon: string;
    type: ActionType;
    endpoint: string | null;
    params: Record<string, unknown>;
    /** Set instead of category_id when a new category should be created. */
    newCategory?: { name: string; color: string };
  };

  interface Props {
    open: boolean;
    /**
     * null = creating a new catalog entry. An action with `template: false` is
     * a tile's own copy: saving it changes that one button, nothing else.
     */
    action: Action | null;
    categories: Category[];
    onsave: (payload: Payload) => void;
    /** Tile copies only: also file the current settings in the catalog. */
    onsavetemplate?: (payload: Payload) => void;
    ondelete?: (action: Action) => void;
    onclose: () => void;
  }

  let { open, action, categories, onsave, onsavetemplate, ondelete, onclose }: Props =
    $props();

  const isTileCopy = $derived(action !== null && action.template === false);

  const TYPES: { value: ActionType; label: string; hint: string }[] = [
    { value: 'pc', label: 'Macro clavier', hint: 'Envoie une combinaison de touches sur le PC.' },
    { value: 'launcher', label: 'Lancer un logiciel', hint: 'Démarre une application ou une commande.' },
    { value: 'open', label: 'Ouvrir un lien', hint: 'Ouvre une URL dans le navigateur de l’ordinateur.' },
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
  let obsFields = $state<ReturnType<typeof ObsActionFields>>();
  let spotifyCommand = $state('toggle');
  let spotifyValue = $state('50');
  let meetingPlatform = $state('meet');
  let meetingCommand = $state('mute');
  let httpMethod = $state('GET');

  const current = $derived(TYPES.find((t) => t.value === kind));

  // -- launcher picker -------------------------------------------------------
  let apps = $state<InstalledApp[]>([]);
  let browse = $state<BrowseResult | null>(null);
  let browsing = $state(false);

  /** Filter the installed list by whatever is typed, so it narrows as you go. */
  const matchingApps = $derived(
    (() => {
      const needle = launch.trim().toLowerCase();
      const pool = needle
        ? apps.filter(
            (a) => a.name.toLowerCase().includes(needle) || a.path.toLowerCase().includes(needle)
          )
        : apps;
      return pool.slice(0, 40);
    })()
  );

  // Load the app list the first time the launcher type is selected.
  $effect(() => {
    if (!open || kind !== 'launcher' || apps.length > 0) return;
    void (async () => {
      try {
        apps = await api.listApps();
      } catch {
        apps = [];
      }
    })();
  });

  function pickApp(path: string) {
    launch = path;
    browsing = false;
    // A path is unambiguous, so prefill the label from the file name.
    if (!label.trim()) {
      const base = path.split(/[\\/]/).pop() ?? '';
      label = base.replace(/\.(lnk|exe|bat|cmd|url|com)$/i, '');
    }
  }

  async function loadBrowse(path?: string) {
    browsing = true;
    try {
      browse = await api.browse(path);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    }
  }

  // Re-seed whenever a different action (or "new") is opened.
  $effect(() => {
    if (!open) return;
    error = null;

    if (action) {
      // A tile copy can outlive its category; fall back so saving still works.
      categoryId = categories.some((c) => c.id === action.category_id)
        ? action.category_id
        : (categories[0]?.id ?? '');
      label = action.label;
      icon = action.icon;
      kind = action.type;
      endpoint = action.endpoint ?? '';
      const p = action.params ?? {};
      combo = Array.isArray(p.combo) ? (p.combo as string[]).join('+') : '';
      launch = typeof p.launch === 'string' ? p.launch : '';
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
    }
    suggestedLabel = '';
    suggestedIcon = '';
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
        const built = obsFields?.build() ?? 'Réglages OBS indisponibles.';
        if (typeof built === 'string') {
          error = built;
          return null;
        }
        return built;
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

  // What the OBS form last proposed. A label or icon still equal to it was not
  // typed by hand, so the next suggestion may replace it.
  let suggestedLabel = '';
  let suggestedIcon = '';

  function applySuggestion(s: { label: string; icon: string }) {
    if (!label.trim() || label === suggestedLabel) label = s.label;
    if (icon === 'lightning' || icon === suggestedIcon) icon = s.icon;
    suggestedLabel = s.label;
    suggestedIcon = s.icon;
  }

  function payload(): Payload | null {
    error = null;
    if (!label.trim()) {
      error = 'Donnez un nom au bouton.';
      return null;
    }
    if (!categoryId) {
      error = 'Choisissez une catégorie.';
      return null;
    }
    if (categoryId === NEW_CATEGORY && !newCategoryName.trim()) {
      error = 'Donnez un nom à la nouvelle catégorie.';
      return null;
    }
    if ((kind === 'fetch' || kind === 'open') && !endpoint.trim()) {
      error = 'Indiquez une URL.';
      return null;
    }

    const params = buildParams();
    if (params === null) return null;

    return {
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
    };
  }

  function save() {
    const built = payload();
    if (built) onsave(built);
  }

  function saveTemplate() {
    const built = payload();
    if (built) onsavetemplate?.(built);
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
      aria-label={isTileCopy ? 'Configurer le bouton' : action ? 'Modifier le modèle' : 'Nouveau modèle'}
    >
      <header class="head">
        <h2 class="text-page-heading">
          {isTileCopy ? 'Configurer le bouton' : action ? 'Modifier le modèle' : 'Nouveau modèle'}
        </h2>
        <button type="button" class="icon-btn" onclick={onclose} aria-label="Fermer">
          <i class="ph ph-x" aria-hidden="true"></i>
        </button>
      </header>

      <div class="body">
        <p class="scope">
          <i class="ph ph-{isTileCopy ? 'hand-tap' : 'stack'}" aria-hidden="true"></i>
          {#if isTileCopy}
            Ces réglages ne concernent que ce bouton. Le modèle du catalogue et les
            autres boutons ne changent pas.
          {:else}
            Modèle du catalogue : les boutons déjà posés en sont des copies et ne
            changent pas. Seuls les prochains dépôts en profitent.
          {/if}
        </p>

        <label class="field">
          <span>Nom du bouton</span>
          <input bind:value={label} placeholder="Ex. Couper le micro" maxlength="28" />
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

        </div>

        <div class="field">
          <span>Icône</span>
          <IconPicker value={icon} hint={label} onpick={(name) => (icon = name)} />
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
          <div class="field">
            <span>Application</span>
            <input
              bind:value={launch}
              placeholder="Cherchez une application installée…"
              oninput={() => (browsing = false)}
            />

            {#if browsing}
              <div class="picker">
                <div class="picker-head">
                  <button
                    type="button"
                    class="crumb"
                    disabled={!browse?.parent}
                    onclick={() => loadBrowse(browse?.parent ?? undefined)}
                    aria-label="Dossier parent"
                    title="Dossier parent"
                  >
                    <i class="ph ph-arrow-up" aria-hidden="true"></i>
                  </button>
                  <span class="crumb-path">{browse?.path ?? 'Emplacements'}</span>
                  <button type="button" class="crumb" onclick={() => (browsing = false)}>
                    Liste des applis
                  </button>
                </div>
                <ul class="picker-list">
                  {#each browse?.entries ?? [] as entry (entry.path)}
                    <li>
                      <button
                        type="button"
                        onclick={() =>
                          entry.kind === 'dir' ? loadBrowse(entry.path) : pickApp(entry.path)}
                      >
                        <i
                          class="ph {entry.kind === 'dir' ? 'ph-folder' : 'ph-app-window'}"
                          aria-hidden="true"
                        ></i>
                        <span class="truncate">{entry.name}</span>
                      </button>
                    </li>
                  {:else}
                    <li class="empty-hint">Rien à lancer ici.</li>
                  {/each}
                </ul>
              </div>
            {:else}
              <div class="picker">
                <ul class="picker-list">
                  {#each matchingApps as app (app.path)}
                    <li>
                      <button type="button" onclick={() => pickApp(app.path)}>
                        <i class="ph ph-app-window" aria-hidden="true"></i>
                        <span class="truncate">{app.name}</span>
                      </button>
                    </li>
                  {:else}
                    <li class="empty-hint">
                      {apps.length === 0
                        ? 'Recherche des applications installées…'
                        : 'Aucune application ne correspond.'}
                    </li>
                  {/each}
                </ul>
                <button type="button" class="browse-btn" onclick={() => loadBrowse()}>
                  <i class="ph ph-folder-open" aria-hidden="true"></i>
                  Parcourir les fichiers…
                </button>
              </div>
            {/if}

            <small>
              Choisissez dans la liste, ou tapez un nom : il est résolu contre le
              menu Démarrer, donc <code>steam</code> suffit. Le programme démarre
              sur la machine qui fait tourner le backend.
            </small>
          </div>
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
          <ObsActionFields
            bind:this={obsFields}
            initial={action?.type === 'obs' ? (action.params ?? {}) : {}}
            onsuggest={applySuggestion}
          />
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
        {#if isTileCopy && onsavetemplate}
          <button
            type="button"
            class="ghost"
            onclick={saveTemplate}
            title="Ajoute une copie de ces réglages au catalogue, pour la réutiliser"
          >
            <i class="ph ph-stack-plus" aria-hidden="true"></i> Ajouter au catalogue
          </button>
        {/if}
        {#if action && !isTileCopy && ondelete}
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
    background: var(--surface);
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
  .field select {
    padding: 10px;
    border: 1px solid var(--border);
    border-radius: 12px;
    font-size: 15px;
    font-weight: 400;
    font-family: inherit;
    background: var(--surface);
  }

  .field small {
    font-weight: 400;
    color: var(--muted);
    line-height: 1.45;
  }

  .field code {
    padding: 1px 4px;
    border-radius: 4px;
    background: var(--hover);
    font-size: 12px;
  }

  /* Launcher picker: a short scrollable list beats typing a program name. */
  .picker {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 6px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: rgb(0 0 0 / 0.02);
  }

  .picker-head {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .crumb {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: 8px;
    background: var(--hover);
    font-size: 12px;
  }

  .crumb:disabled {
    opacity: 0.4;
  }

  .crumb-path {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    direction: rtl; /* keep the deepest folder visible when it overflows */
    font-size: 12px;
    font-weight: 400;
    color: var(--muted);
  }

  .picker-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    max-height: 190px;
    overflow-y: auto;
  }

  .picker-list button {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 7px 8px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 400;
    text-align: left;
  }

  .picker-list button:hover {
    background: rgb(0 0 0 / 0.06);
  }

  .empty-hint {
    padding: 8px;
    font-size: 13px;
    font-weight: 400;
    color: var(--muted);
  }

  .browse-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 8px;
    border-radius: 8px;
    border: 1px dashed rgb(0 0 0 / 0.15);
    font-size: 13px;
    color: var(--muted);
  }

  .browse-btn:hover {
    background: var(--hover);
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

  .scope {
    display: flex;
    gap: 8px;
    padding: 10px 12px;
    border-radius: 12px;
    background: var(--hover);
    font-size: 13px;
    line-height: 1.45;
    color: var(--muted);
  }

  .scope i {
    flex: none;
    margin-top: 2px;
    font-size: 16px;
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
    background: var(--hover);
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
