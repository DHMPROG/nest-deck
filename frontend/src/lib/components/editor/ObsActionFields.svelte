<script lang="ts">
  /**
   * OBS settings of an action, as plain choices instead of a raw request.
   *
   * Asks OBS for its scenes, sources and audio inputs so they can be picked
   * from a list. With OBS closed the same choices fall back to free text, and
   * "Requête avancée" keeps the raw request + JSON form for anything else.
   */
  import { onMount, untrack } from 'svelte';
  import { api } from '$lib/services/api';
  import { tokens } from '$lib/theme';
  import type { ObsState } from '$lib/types';

  interface Props {
    /** Params of the action being edited; `{}` for a new one. */
    initial: Record<string, unknown>;
    /** A preset or target was picked: a label and icon that describe it. */
    onsuggest: (suggestion: { label: string; icon: string }) => void;
  }

  let { initial, onsuggest }: Props = $props();

  type Target = 'scene' | 'source' | 'audio' | null;

  const PRESETS: { id: string; request: string; label: string; icon: string; target: Target }[] = [
    { id: 'scene', request: 'SetCurrentProgramScene', label: 'Changer de scène', icon: 'monitor-play', target: 'scene' },
    { id: 'source', request: 'ToggleSceneItem', label: 'Afficher / masquer une source', icon: 'eye', target: 'source' },
    { id: 'mute', request: 'ToggleInputMute', label: 'Couper / rétablir un son', icon: 'microphone-slash', target: 'audio' },
    { id: 'stream', request: 'ToggleStream', label: 'Lancer / arrêter le live', icon: 'broadcast', target: null },
    { id: 'record', request: 'ToggleRecord', label: 'Lancer / arrêter l’enregistrement', icon: 'record', target: null },
    { id: 'pause', request: 'ToggleRecordPause', label: 'Mettre l’enregistrement en pause', icon: 'pause', target: null },
    { id: 'replay', request: 'SaveReplayBuffer', label: 'Sauvegarder le replay', icon: 'film-strip', target: null },
    { id: 'vcam', request: 'ToggleVirtualCam', label: 'Caméra virtuelle on / off', icon: 'webcam', target: null },
    { id: 'studio', request: 'TriggerStudioModeTransition', label: 'Transition (mode studio)', icon: 'arrows-left-right', target: null },
    { id: 'raw', request: '', label: 'Requête avancée…', icon: 'code', target: null }
  ];

  /** Short tile labels for the parameterless presets. */
  const SHORT: Record<string, string> = {
    stream: 'Live',
    record: 'Enregistrer',
    pause: 'Pause rec',
    replay: 'Replay',
    vcam: 'Cam virtuelle',
    studio: 'Transition'
  };

  // Seeded once: the modal mounts this form afresh for every action it opens.
  const seed = untrack(() => initial);
  const initialRequest = typeof seed.request === 'string' ? seed.request : '';
  const initialArgs = (seed.args ?? {}) as Record<string, unknown>;
  const str = (value: unknown) => (typeof value === 'string' ? value : '');

  let preset = $state(
    initialRequest
      ? (PRESETS.find((p) => p.request === initialRequest)?.id ?? 'raw')
      : 'scene'
  );
  let scene = $state(str(initialArgs.sceneName));
  let source = $state(str(initialArgs.sourceName));
  let input = $state(str(initialArgs.inputName));
  let rawRequest = $state(initialRequest);
  let rawArgs = $state(Object.keys(initialArgs).length ? JSON.stringify(initialArgs, null, 2) : '');

  const current = $derived(PRESETS.find((p) => p.id === preset)!);

  // -- connection -------------------------------------------------------------
  let obs = $state<ObsState | null>(null);
  let loading = $state(false);
  let showSettings = $state(false);
  let obsUrl = $state('');
  let obsPassword = $state('');
  let passwordSet = $state(false);

  const online = $derived(obs?.connected === true);
  const sceneSources = $derived(obs?.scenes.find((s) => s.name === scene)?.sources ?? []);
  const devices = $derived(obs?.audio_inputs.filter((a) => a.device) ?? []);
  const otherAudio = $derived(obs?.audio_inputs.filter((a) => !a.device) ?? []);

  async function refresh() {
    loading = true;
    try {
      obs = await api.obsState();
    } catch {
      obs = { connected: false, address: '', scenes: [], audio_inputs: [], error: 'backend injoignable' };
    } finally {
      loading = false;
    }
    // Open the connection settings straight away when there is nothing to pick from.
    if (!obs?.connected) showSettings = true;
  }

  async function saveConnection() {
    const body: { obs_url: string; obs_password?: string } = { obs_url: obsUrl.trim() };
    // An empty field keeps the stored password rather than wiping it.
    if (obsPassword) body.obs_password = obsPassword;
    try {
      const s = await api.setSettings(body);
      passwordSet = s.obs_password_set;
      obsPassword = '';
    } catch {
      /* the refresh below reports the problem */
    }
    await refresh();
    if (obs?.connected) showSettings = false;
  }

  async function forgetPassword() {
    const s = await api.setSettings({ obs_password: '' });
    passwordSet = s.obs_password_set;
    await refresh();
  }

  onMount(() => {
    void refresh();
    void api.getSettings().then((s) => {
      obsUrl = s.obs_url ?? '';
      passwordSet = s.obs_password_set;
    });
  });

  // -- suggestions ------------------------------------------------------------
  function suggest() {
    const p = current;
    if (p.id === 'raw') return;
    let label = SHORT[p.id] ?? '';
    if (p.id === 'scene' && scene) label = scene;
    else if (p.id === 'source' && source) label = source;
    else if (p.id === 'mute' && input) label = `Muet ${input}`;
    if (label) onsuggest({ label: label.slice(0, 28), icon: p.icon });
  }

  function pickPreset(id: string) {
    preset = id;
    suggest();
  }

  /** The params to store, or a message saying what is missing. */
  export function build(): { request: string; args: Record<string, unknown> } | string {
    switch (current.target) {
      case 'scene':
        if (!scene.trim()) return 'Choisissez la scène à afficher.';
        return { request: current.request, args: { sceneName: scene.trim() } };
      case 'source':
        if (!scene.trim() || !source.trim()) return 'Choisissez la scène puis la source.';
        return {
          request: current.request,
          args: { sceneName: scene.trim(), sourceName: source.trim() }
        };
      case 'audio':
        if (!input.trim()) return 'Choisissez la source audio.';
        return { request: current.request, args: { inputName: input.trim() } };
    }
    if (current.id !== 'raw') return { request: current.request, args: {} };

    if (!rawRequest.trim()) return 'Indiquez la requête OBS, par exemple SetCurrentProgramScene.';
    let args: unknown = {};
    if (rawArgs.trim()) {
      try {
        args = JSON.parse(rawArgs);
      } catch {
        return 'Les arguments OBS ne sont pas du JSON valide.';
      }
    }
    return { request: rawRequest.trim(), args: args as Record<string, unknown> };
  }
</script>

<div class="obs">
  <!-- Connection status: whether the lists below come from OBS itself. -->
  <div class="status">
    <span
      class="dot"
      style="background: {online
        ? tokens.category.meeting.accent
        : loading
          ? tokens.surface.muted
          : tokens.category.stream.accent}"
    ></span>
    <span class="status-text">
      {#if loading && !obs}
        Connexion à OBS…
      {:else if online}
        OBS {obs?.version ?? ''} connecté · {obs?.address}
      {:else}
        OBS injoignable{obs?.error ? ` — ${obs.error}` : ''}
      {/if}
    </span>
    <button type="button" class="mini" onclick={refresh} disabled={loading} title="Actualiser">
      <i class="ph ph-arrows-clockwise" class:spin={loading} aria-hidden="true"></i>
    </button>
    <button
      type="button"
      class="mini"
      onclick={() => (showSettings = !showSettings)}
      aria-expanded={showSettings}
      title="Réglages de connexion"
    >
      <i class="ph ph-gear-six" aria-hidden="true"></i>
    </button>
  </div>

  {#if showSettings}
    <div class="panel">
      <div class="row">
        <label class="field">
          <span>Adresse</span>
          <input bind:value={obsUrl} placeholder="ws://localhost:4455" />
        </label>
        <label class="field">
          <span>Mot de passe</span>
          <input
            type="password"
            bind:value={obsPassword}
            placeholder={passwordSet ? '•••••• (enregistré)' : 'Aucun'}
            autocomplete="off"
          />
        </label>
      </div>
      <small>
        Dans OBS : <b>Outils → Paramètres du serveur WebSocket</b>, cochez « Activer
        le serveur WebSocket ». Le port et le mot de passe sont dans « Afficher les
        informations de connexion ».
        {#if passwordSet}
          · <button type="button" class="link" onclick={forgetPassword}>oublier le mot de passe</button>
        {/if}
      </small>
      <button type="button" class="test" onclick={saveConnection} disabled={loading}>
        Enregistrer et tester
      </button>
    </div>
  {/if}

  <!-- What the button does, as a choice rather than an API name. -->
  <div class="field">
    <span>Que fait le bouton ?</span>
    <div class="presets">
      {#each PRESETS as p (p.id)}
        <button
          type="button"
          class="preset"
          class:on={preset === p.id}
          onclick={() => pickPreset(p.id)}
        >
          <i class="ph-duotone ph-{p.icon}" aria-hidden="true"></i>
          <span>{p.label}</span>
        </button>
      {/each}
    </div>
  </div>

  {#if current.target === 'scene' || current.target === 'source'}
    <label class="field">
      <span>{current.target === 'scene' ? 'Scène à afficher' : 'Dans la scène'}</span>
      {#if online}
        <select
          bind:value={scene}
          onchange={() => {
            if (!sceneSources.includes(source)) source = '';
            suggest();
          }}
        >
          <option value="" disabled>Choisir une scène…</option>
          {#if scene && !obs?.scenes.some((s) => s.name === scene)}
            <option value={scene}>{scene} (introuvable dans OBS)</option>
          {/if}
          {#each obs?.scenes ?? [] as s (s.name)}
            <option value={s.name}>{s.name}{s.name === obs?.current_scene ? ' · en direct' : ''}</option>
          {/each}
        </select>
      {:else}
        <input bind:value={scene} placeholder="Nom exact de la scène" onchange={suggest} />
      {/if}
    </label>
  {/if}

  {#if current.target === 'source'}
    <label class="field">
      <span>Source à afficher / masquer</span>
      {#if online && scene}
        <select bind:value={source} onchange={suggest}>
          <option value="" disabled>Choisir une source…</option>
          {#if source && !sceneSources.includes(source)}
            <option value={source}>{source} (introuvable dans OBS)</option>
          {/if}
          {#each sceneSources as name (name)}
            <option value={name}>{name}</option>
          {/each}
        </select>
      {:else}
        <input bind:value={source} placeholder="Nom exact de la source" onchange={suggest} />
      {/if}
      <small>Chaque appui inverse l’état : visible ↔ masquée.</small>
    </label>
  {/if}

  {#if current.target === 'audio'}
    <label class="field">
      <span>Source audio</span>
      {#if online}
        <select bind:value={input} onchange={suggest}>
          <option value="" disabled>Choisir une source audio…</option>
          {#if input && !obs?.audio_inputs.some((a) => a.name === input)}
            <option value={input}>{input} (introuvable dans OBS)</option>
          {/if}
          {#if devices.length}
            <optgroup label="Micros et sorties audio">
              {#each devices as a (a.name)}
                <option value={a.name}>{a.name}</option>
              {/each}
            </optgroup>
          {/if}
          {#if otherAudio.length}
            <optgroup label="Autres sources avec du son">
              {#each otherAudio as a (a.name)}
                <option value={a.name}>{a.name}</option>
              {/each}
            </optgroup>
          {/if}
        </select>
      {:else}
        <input bind:value={input} placeholder="Ex. Mic/Aux" onchange={suggest} />
      {/if}
    </label>
  {/if}

  {#if current.id === 'raw'}
    <label class="field">
      <span>Requête OBS</span>
      <input bind:value={rawRequest} placeholder="SetCurrentProgramScene" />
    </label>
    <label class="field">
      <span>Arguments (JSON)</span>
      <textarea bind:value={rawArgs} rows="3" placeholder={'{ "sceneName": "Camera" }'}></textarea>
      <small>
        N’importe quelle requête obs-websocket v5 — la liste complète est dans la
        documentation du protocole obs-websocket.
      </small>
    </label>
  {/if}
</div>

<style>
  .obs {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 8px 8px 12px;
    border-radius: 12px;
    background: var(--hover);
    font-size: 13px;
  }

  .dot {
    flex: none;
    width: 8px;
    height: 8px;
    border-radius: 999px;
  }

  .status-text {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mini {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 999px;
    font-size: 16px;
  }

  .mini:hover {
    background: var(--surface);
  }

  .spin {
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .spin {
      animation: none;
    }
  }

  .panel {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px;
    border-radius: 16px;
    background: rgb(0 0 0 / 0.03);
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
    border: 1px solid var(--border);
    border-radius: 12px;
    font-size: 15px;
    font-weight: 400;
    font-family: inherit;
    background: var(--surface);
  }

  .field textarea {
    resize: vertical;
    font-family: ui-monospace, monospace;
    font-size: 13px;
  }

  small {
    font-size: 13px;
    font-weight: 400;
    color: var(--muted);
    line-height: 1.45;
  }

  .link {
    text-decoration: underline;
  }

  .test {
    align-self: flex-start;
    height: 34px;
    padding: 0 14px;
    border-radius: 999px;
    background: var(--hover);
    font-size: 13px;
    font-weight: 600;
  }

  .presets {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
  }

  .preset {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: 12px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
  }

  .preset i {
    flex: none;
    font-size: 20px;
  }

  .preset:hover {
    background: var(--hover);
  }

  .preset.on {
    border-color: currentColor;
    background: var(--hover);
    font-weight: 700;
  }
</style>
