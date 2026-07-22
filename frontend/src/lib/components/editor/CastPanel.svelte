<script lang="ts">
  /**
   * Cast control for the desktop app: shows the current Hub, finds devices on
   * the network, connects (which casts the Deck). Lives in the editor top bar.
   *
   * The cast endpoints only do anything when the backend runs on a machine on
   * the LAN (i.e. the desktop app) — in a plain browser they still work but
   * cast from wherever the backend runs.
   */
  import { api } from '$lib/services/api';
  import type { CastDevice, CastStatus } from '$lib/types';

  let open = $state(false);
  let status = $state<CastStatus>({ connected: false, device: null });
  let devices = $state<CastDevice[]>([]);
  let remembered = $state<{ uuid: string; name: string } | null>(null);
  let scanning = $state(false);
  let busyUuid = $state<string | null>(null);
  let error = $state<string | null>(null);

  const label = $derived(
    status.connected && status.device
      ? status.device.name
      : remembered
        ? remembered.name
        : 'Caster'
  );

  async function refresh() {
    try {
      status = await api.castStatus();
      error = null;
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    }
  }

  async function scan() {
    scanning = true;
    error = null;
    try {
      const result = await api.castDevices(6);
      devices = result.devices;
      remembered = result.remembered;
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      scanning = false;
    }
  }

  async function toggle() {
    open = !open;
    if (open) {
      await refresh();
      if (devices.length === 0) await scan();
    }
  }

  async function connect(device: CastDevice) {
    busyUuid = device.uuid;
    error = null;
    try {
      status = await api.castConnect({ uuid: device.uuid });
      remembered = { uuid: device.uuid, name: device.name };
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    } finally {
      busyUuid = null;
    }
  }

  async function disconnect() {
    try {
      await api.castDisconnect();
      await refresh();
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    }
  }

  async function recast() {
    try {
      status = await api.castRecast();
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause);
    }
  }
</script>

<div class="cast">
  <button
    type="button"
    class="trigger"
    class:on={status.connected}
    onclick={toggle}
    aria-expanded={open}
    title="Caster le Deck sur un écran"
  >
    <i class="ph ph-{status.connected ? 'cast' : 'monitor'}" aria-hidden="true"></i>
    <span class="truncate">{label}</span>
    {#if status.connected}
      <span class="dot" class:live={status.casting}></span>
    {/if}
  </button>

  {#if open}
    <div class="panel">
      <header>
        <strong>Diffusion</strong>
        <button
          type="button"
          class="ghost"
          onclick={scan}
          disabled={scanning}
          title="Rechercher les écrans"
        >
          <i
            class="ph ph-arrows-clockwise"
            class:spin={scanning}
            aria-hidden="true"
          ></i>
          {scanning ? 'Recherche…' : 'Actualiser'}
        </button>
      </header>

      {#if status.connected && status.device}
        <div class="current">
          <div>
            <p class="name">{status.device.name}</p>
            <p class="sub">
              {status.casting ? 'Deck à l’écran' : 'En veille — recaster ?'}
            </p>
          </div>
          <div class="current-actions">
            {#if !status.casting}
              <button type="button" class="mini" onclick={recast}>Recaster</button>
            {/if}
            <button type="button" class="mini danger" onclick={disconnect}>
              Arrêter
            </button>
          </div>
        </div>
      {/if}

      <ul class="devices">
        {#each devices as device (device.uuid)}
          {@const active = status.device?.uuid === device.uuid}
          <li>
            <button
              type="button"
              class="device"
              class:active
              disabled={busyUuid === device.uuid}
              onclick={() => connect(device)}
            >
              <i class="ph ph-television" aria-hidden="true"></i>
              <span class="truncate">
                {device.name}
                <small>{device.model}</small>
              </span>
              {#if busyUuid === device.uuid}
                <i class="ph ph-spinner spin" aria-hidden="true"></i>
              {:else if active}
                <i class="ph ph-check" aria-hidden="true"></i>
              {/if}
            </button>
          </li>
        {:else}
          {#if !scanning}
            <li class="hint">Aucun écran trouvé sur le réseau.</li>
          {/if}
        {/each}
      </ul>

      {#if error}
        <p class="error">{error}</p>
      {/if}
    </div>
  {/if}
</div>

<style>
  .cast {
    position: relative;
  }

  .trigger {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 40px;
    max-width: 180px;
    padding: 0 12px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 500;
  }

  .trigger:hover {
    background: var(--hover);
  }

  .trigger.on {
    background: #e3f9e9;
    color: #0f3a1a;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: var(--muted);
    flex-shrink: 0;
  }

  .dot.live {
    background: #34c759;
  }

  .panel {
    position: absolute;
    top: 46px;
    right: 0;
    z-index: 40;
    width: 300px;
    padding: 12px;
    border-radius: 18px;
    background: var(--surface);
    box-shadow:
      0 4px 12px rgb(0 0 0 / 0.08),
      0 12px 32px var(--border);
  }

  .panel header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .ghost {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 5px 9px;
    border-radius: 8px;
    font-size: 12px;
    color: #007aff;
  }

  .ghost:disabled {
    color: var(--muted);
  }

  .current {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 10px;
    margin-bottom: 8px;
    border-radius: 12px;
    background: #e3f9e9;
  }

  .current .name {
    font-size: 14px;
    font-weight: 600;
    color: #0f3a1a;
  }

  .current .sub {
    font-size: 12px;
    color: #248a3d;
  }

  .current-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }

  .mini {
    padding: 5px 10px;
    border-radius: 8px;
    background: rgb(255 255 255 / 0.7);
    font-size: 12px;
    font-weight: 600;
  }

  .mini.danger {
    color: #c4271e;
  }

  .devices {
    display: flex;
    flex-direction: column;
    gap: 3px;
    max-height: 240px;
    overflow-y: auto;
  }

  .device {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 9px 10px;
    border-radius: 10px;
    font-size: 14px;
    text-align: left;
  }

  .device:hover {
    background: var(--hover);
  }

  .device.active {
    background: #e3f9e9;
    color: #0f3a1a;
  }

  .device span {
    flex: 1;
    display: flex;
    flex-direction: column;
    line-height: 1.2;
  }

  .device small {
    font-size: 11px;
    color: var(--muted);
  }

  .hint,
  .error {
    padding: 10px;
    font-size: 13px;
    color: var(--muted);
  }

  .error {
    color: #c4271e;
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
