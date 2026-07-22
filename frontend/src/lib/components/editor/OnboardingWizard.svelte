<script lang="ts">
  /**
   * First-launch setup wizard: welcome → find & cast the Hub → how to place an
   * action → action types → profiles & pages. Doubles as setup (the cast step
   * actually connects). Shown once; re-openable from the editor's help button.
   */
  import { api } from '$lib/services/api';
  import { tokens } from '$lib/theme';
  import type { CastDevice } from '$lib/types';

  interface Props {
    open: boolean;
    onclose: () => void;
  }

  let { open, onclose }: Props = $props();

  const steps = ['welcome', 'cast', 'place', 'types', 'organise', 'done'] as const;
  type Step = (typeof steps)[number];

  let index = $state(0);
  const step = $derived<Step>(steps[index]);
  const progress = $derived((index / (steps.length - 1)) * 100);

  // -- cast step -------------------------------------------------------------
  let devices = $state<CastDevice[]>([]);
  let scanning = $state(false);
  let connectingUuid = $state<string | null>(null);
  let connectedName = $state<string | null>(null);
  let castError = $state<string | null>(null);

  async function scan() {
    scanning = true;
    castError = null;
    try {
      const result = await api.castDevices(6);
      devices = result.devices;
    } catch (cause) {
      castError = cause instanceof Error ? cause.message : String(cause);
    } finally {
      scanning = false;
    }
  }

  async function connect(device: CastDevice) {
    connectingUuid = device.uuid;
    castError = null;
    try {
      const status = await api.castConnect({ uuid: device.uuid });
      connectedName = status.device?.name ?? device.name;
    } catch (cause) {
      castError = cause instanceof Error ? cause.message : String(cause);
    } finally {
      connectingUuid = null;
    }
  }

  // Scan automatically when the user reaches the cast step.
  $effect(() => {
    if (open && step === 'cast' && devices.length === 0 && !scanning) void scan();
  });

  function next() {
    if (index < steps.length - 1) index += 1;
  }
  function back() {
    if (index > 0) index -= 1;
  }

  async function finish() {
    try {
      await api.setSettings({ onboarded: true });
    } catch {
      /* non-fatal: worst case the wizard shows again */
    }
    onclose();
  }

  const cats = [
    { c: 'media', icon: 'music-notes', t: 'Média', d: 'Play/pause, volume — via les touches multimédia. Marche direct.' },
    { c: 'pc', icon: 'desktop', t: 'PC', d: 'Verrouiller, capture, macros clavier. Sur ce PC.' },
    { c: 'games', icon: 'game-controller', t: 'Logiciels', d: 'Lancer Steam, Discord… choisis dans la liste.' },
    { c: 'stream', icon: 'broadcast', t: 'OBS', d: 'Scènes, stream, enregistrement. OBS doit tourner.' }
  ] as const;
</script>

{#if open}
  <div class="backdrop">
    <div class="sheet" role="dialog" aria-modal="true" aria-label="Bienvenue">
      <div class="bar"><span class="fill" style="width: {progress}%"></span></div>

      <div class="body">
        {#if step === 'welcome'}
          <div class="hero" style="background: {tokens.category.stream.bg}">
            <i class="ph-duotone ph-squares-four" style="color: {tokens.category.stream.accentDeep}"></i>
          </div>
          <h2>Bienvenue sur Nest Deck</h2>
          <p>
            Transforme ton Nest Hub en télécommande tactile. En trois minutes :
            on trouve ton écran, on caste le Deck, et tu poses tes premiers
            boutons.
          </p>
        {:else if step === 'cast'}
          <h2>1 · Trouve ton écran</h2>
          <p>Choisis l'écran Google Cast sur lequel afficher le Deck.</p>

          <div class="devices">
            {#if scanning && devices.length === 0}
              <p class="muted">Recherche des écrans…</p>
            {:else}
              {#each devices as device (device.uuid)}
                {@const isConnected = connectedName === device.name}
                <button
                  type="button"
                  class="device"
                  class:on={isConnected}
                  disabled={connectingUuid === device.uuid}
                  onclick={() => connect(device)}
                >
                  <i class="ph ph-television"></i>
                  <span>{device.name}<small>{device.model}</small></span>
                  {#if connectingUuid === device.uuid}
                    <i class="ph ph-spinner spin"></i>
                  {:else if isConnected}
                    <i class="ph ph-check-circle" style="color: {tokens.category.meeting.accent}"></i>
                  {/if}
                </button>
              {:else}
                <p class="muted">Aucun écran trouvé.</p>
              {/each}
            {/if}
            <button type="button" class="rescan" onclick={scan} disabled={scanning}>
              <i class="ph ph-arrows-clockwise" class:spin={scanning}></i>
              Rechercher à nouveau
            </button>
          </div>

          {#if connectedName}
            <p class="ok">✓ Le Deck est casté sur « {connectedName} ». Il se
              reconnectera tout seul au prochain démarrage.</p>
          {/if}
          {#if castError}<p class="err">{castError}</p>{/if}
          <p class="muted small">
            Pas d'écran maintenant ? Passe cette étape, tu pourras caster plus
            tard avec le bouton en haut à droite.
          </p>
        {:else if step === 'place'}
          <h2>2 · Pose une action sur une tuile</h2>
          <p>Deux façons de remplir un emplacement de la grille :</p>
          <ul class="tips">
            <li>
              <i class="ph ph-arrows-out-cardinal"></i>
              <span><b>Depuis l'éditeur</b> — glisse une action du catalogue
                (à droite) vers un emplacement.</span>
            </li>
            <li>
              <i class="ph ph-hand-tap"></i>
              <span><b>Depuis le Hub</b> — tape un emplacement vide, choisis
                une action dans la liste.</span>
            </li>
          </ul>
          <p class="muted small">
            Un clic sur le menu ⋮ d'une tuile permet de la modifier, la
            dupliquer ou changer ce qu'elle fait.
          </p>
        {:else if step === 'types'}
          <h2>3 · Les types d'actions</h2>
          <p>Chaque bouton fait quelque chose de précis :</p>
          <div class="types">
            {#each cats as t (t.c)}
              <div class="type" style="background: {tokens.category[t.c].bg}; color: {tokens.category[t.c].text}">
                <i class="ph-duotone ph-{t.icon}" style="color: {tokens.category[t.c].accentDeep}"></i>
                <div><b>{t.t}</b><span>{t.d}</span></div>
              </div>
            {/each}
          </div>
          <p class="muted small">
            « Média » et les volumes marchent sans rien configurer. OBS, Spotify
            et les lanceurs ont besoin de l'appli correspondante installée.
          </p>
        {:else if step === 'organise'}
          <h2>4 · Profils, pages & grille</h2>
          <ul class="tips">
            <li><i class="ph ph-cards"></i><span><b>Pages</b> — regroupe tes
              boutons par thème (Stream, PC, Jeux…). Swipe pour changer de page
              sur le Hub.</span></li>
            <li><i class="ph ph-user-switch"></i><span><b>Profils</b> — plusieurs
              jeux de pages, ex. « Boulot » et « Gaming ».</span></li>
            <li><i class="ph ph-grid-four"></i><span><b>Taille</b> — chaque page
              va de 3×5 à 6×6, réglable en haut de la grille.</span></li>
          </ul>
        {:else if step === 'done'}
          <div class="hero" style="background: {tokens.category.meeting.bg}">
            <i class="ph-duotone ph-check-circle" style="color: {tokens.category.meeting.accentDeep}"></i>
          </div>
          <h2>C'est parti !</h2>
          <p>
            Tu peux rouvrir ce guide à tout moment avec le bouton
            <i class="ph ph-question inline"></i> en haut. Amuse-toi bien.
          </p>
        {/if}
      </div>

      <footer>
        <button type="button" class="skip" onclick={finish}>
          {step === 'done' ? '' : 'Passer'}
        </button>
        <div class="dots">
          {#each steps as s, i (s)}
            <span class="dot" class:active={i === index}></span>
          {/each}
        </div>
        <div class="nav">
          {#if index > 0 && step !== 'done'}
            <button type="button" class="ghost" onclick={back}>Retour</button>
          {/if}
          {#if step === 'done'}
            <button type="button" class="primary" onclick={finish}>Commencer</button>
          {:else}
            <button type="button" class="primary" onclick={next}>Suivant</button>
          {/if}
        </div>
      </footer>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 80;
    display: grid;
    place-items: center;
    background: rgb(0 0 0 / 0.45);
    animation: fade 160ms ease-out;
  }
  @keyframes fade {
    from {
      opacity: 0;
    }
  }

  .sheet {
    display: flex;
    flex-direction: column;
    width: min(520px, 92vw);
    max-height: 88vh;
    border-radius: 28px;
    background: var(--surface);
    color: var(--text);
    overflow: hidden;
    box-shadow:
      0 4px 12px rgb(0 0 0 / 0.12),
      0 24px 60px rgb(0 0 0 / 0.25);
    animation: pop 180ms cubic-bezier(0.2, 0.8, 0.2, 1);
  }
  @keyframes pop {
    from {
      opacity: 0;
      transform: scale(0.96);
    }
  }

  .bar {
    height: 4px;
    background: var(--hover);
  }
  .fill {
    display: block;
    height: 100%;
    background: #34c759;
    transition: width 250ms ease;
  }

  .body {
    padding: 28px 28px 8px;
    overflow-y: auto;
  }

  .hero {
    display: grid;
    place-items: center;
    width: 72px;
    height: 72px;
    margin: 0 auto 16px;
    border-radius: 22px;
    font-size: 40px;
  }

  h2 {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 8px;
    text-align: center;
  }

  .body > p {
    font-size: 15px;
    line-height: 1.5;
    color: var(--text);
    text-align: center;
    margin-bottom: 4px;
  }

  .muted {
    color: var(--muted);
  }
  .small {
    font-size: 13px;
  }
  .ok {
    margin-top: 12px;
    font-size: 14px;
    color: #248a3d;
    text-align: center;
  }
  .err {
    margin-top: 8px;
    font-size: 13px;
    color: #c4271e;
    text-align: center;
  }

  .devices {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin: 16px 0 4px;
  }

  .device {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border-radius: 14px;
    border: 1px solid var(--border);
    font-size: 15px;
    text-align: left;
  }
  .device:hover {
    background: var(--hover);
  }
  .device.on {
    border-color: #34c759;
    background: color-mix(in srgb, #34c759 10%, transparent);
  }
  .device span {
    flex: 1;
    display: flex;
    flex-direction: column;
    line-height: 1.2;
  }
  .device small {
    font-size: 12px;
    color: var(--muted);
  }
  .device i:first-child {
    font-size: 20px;
  }

  .rescan {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 10px;
    border-radius: 12px;
    border: 1px dashed var(--border);
    font-size: 13px;
    color: var(--muted);
  }

  .tips {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin: 16px 0;
  }
  .tips li {
    display: flex;
    gap: 12px;
    font-size: 15px;
    line-height: 1.45;
  }
  .tips i {
    font-size: 22px;
    color: var(--muted);
    flex-shrink: 0;
  }

  .types {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin: 16px 0;
  }
  .type {
    display: flex;
    gap: 10px;
    padding: 12px;
    border-radius: 14px;
  }
  .type i {
    font-size: 26px;
    flex-shrink: 0;
  }
  .type b {
    display: block;
    font-size: 14px;
  }
  .type span {
    font-size: 12px;
    opacity: 0.85;
    line-height: 1.35;
  }

  .inline {
    font-size: 15px;
    vertical-align: -1px;
  }

  footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 16px 24px;
    border-top: 1px solid var(--border);
  }

  .skip {
    min-width: 60px;
    font-size: 13px;
    color: var(--muted);
    text-align: left;
  }

  .dots {
    display: flex;
    gap: 6px;
  }
  .dot {
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: var(--border);
  }
  .dot.active {
    background: #34c759;
  }

  .nav {
    display: flex;
    gap: 8px;
    min-width: 60px;
    justify-content: flex-end;
  }
  .ghost,
  .primary {
    height: 38px;
    padding: 0 18px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 600;
  }
  .ghost {
    background: var(--hover);
    color: var(--text);
  }
  .primary {
    background: #1c1c1e;
    color: #fff;
  }
  :root[data-theme='dark'] .primary {
    background: #f2f2f7;
    color: #1c1c1e;
  }

  .spin {
    animation: spin 900ms linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
