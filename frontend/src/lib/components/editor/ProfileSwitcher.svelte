<script lang="ts">
  import { categoryPalette } from '$lib/theme';
  import type { Profile } from '$lib/types';

  interface Props {
    profiles: Profile[];
    current: Profile | null;
    onselect: (id: string) => void;
    oncreate: (name: string) => void;
    onrename: (id: string, name: string) => void;
    ondelete: (id: string) => void;
  }

  let { profiles, current, onselect, oncreate, onrename, ondelete }: Props = $props();

  let open = $state(false);
  let editing = $state(false);
  let draft = $state('');

  const pal = categoryPalette('pc');

  function startRename() {
    if (!current) return;
    draft = current.name;
    editing = true;
  }

  function commitRename() {
    editing = false;
    if (current && draft.trim() && draft.trim() !== current.name) {
      onrename(current.id, draft.trim());
    }
  }

  // Inline creation rather than prompt(): native dialogs block the page and
  // cannot be styled to match the rest of the editor.
  let creating = $state(false);
  let newName = $state('');
  /** Two-step delete, so a stray click cannot destroy a profile. */
  let confirmingId = $state<string | null>(null);
  let confirmTimer: ReturnType<typeof setTimeout> | null = null;

  function submitCreate() {
    const name = newName.trim();
    creating = false;
    newName = '';
    if (name) oncreate(name);
  }

  function armDelete(id: string) {
    if (confirmTimer) clearTimeout(confirmTimer);
    if (confirmingId === id) {
      confirmingId = null;
      ondelete(id);
      return;
    }
    confirmingId = id;
    confirmTimer = setTimeout(() => (confirmingId = null), 3000);
  }
</script>

<div class="flex flex-col gap-3">
  <div class="flex items-center gap-3">
    <span
      class="grid size-11 shrink-0 place-items-center rounded-pill"
      style="background: {pal.bg}; color: {pal.accentDeep}"
    >
      <i class="ph ph-{current?.icon ?? 'house'} text-2xl" aria-hidden="true"></i>
    </span>

    <div class="min-w-0 flex-1">
      {#if editing}
        <!-- svelte-ignore a11y_autofocus -->
        <input
          class="w-full rounded-xl border border-app-border px-2 py-1 text-page-heading"
          bind:value={draft}
          onblur={commitRename}
          onkeydown={(e) => {
            if (e.key === 'Enter') commitRename();
            if (e.key === 'Escape') editing = false;
          }}
          autofocus
          aria-label="Nom du profil"
        />
      {:else}
        <button
          type="button"
          class="block w-full truncate text-left text-page-heading"
          onclick={startRename}
          title="Cliquer pour renommer"
        >
          {current?.name ?? '—'}
        </button>
      {/if}
      <p class="text-label text-app-muted">
        {#if current?.active}Profil actif{:else}Inactif{/if}
      </p>
    </div>

    <button
      type="button"
      class="grid size-11 place-items-center rounded-pill hover:bg-app-hover"
      onclick={() => (open = !open)}
      aria-expanded={open}
      aria-label="Changer de profil"
    >
      <i class="ph ph-caret-down" aria-hidden="true"></i>
    </button>
  </div>

  {#if open}
    <ul class="flex flex-col gap-1 rounded-2xl bg-app-sunken p-2">
      {#each profiles as profile (profile.id)}
        <li class="flex items-center gap-1">
          <button
            type="button"
            class="flex h-10 min-w-0 flex-1 items-center gap-2 rounded-xl px-2 text-left text-body hover:bg-app-hover"
            class:font-semibold={profile.id === current?.id}
            onclick={() => {
              open = false;
              onselect(profile.id);
            }}
          >
            <i class="ph ph-{profile.icon}" aria-hidden="true"></i>
            <span class="truncate">{profile.name}</span>
            {#if profile.active}
              <i class="ph ph-check-circle ml-auto text-cat-meeting-accent" aria-hidden="true"></i>
            {/if}
          </button>
          {#if profiles.length > 1}
            <button
              type="button"
              class="grid size-9 place-items-center rounded-lg hover:bg-app-hover"
              class:text-cat-stream-accent-deep={confirmingId === profile.id}
              class:text-app-muted={confirmingId !== profile.id}
              onclick={() => armDelete(profile.id)}
              aria-label={confirmingId === profile.id
                ? `Confirmer la suppression de ${profile.name}`
                : `Supprimer ${profile.name}`}
              title={confirmingId === profile.id
                ? 'Cliquer à nouveau pour confirmer'
                : 'Supprimer'}
            >
              <i
                class="ph {confirmingId === profile.id ? 'ph-check' : 'ph-trash'}"
                aria-hidden="true"
              ></i>
            </button>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}

  {#if creating}
    <!-- svelte-ignore a11y_autofocus -->
    <input
      class="h-10 rounded-xl border border-app-border px-3 text-body"
      placeholder="Nom du profil"
      bind:value={newName}
      onblur={submitCreate}
      onkeydown={(event) => {
        if (event.key === 'Enter') submitCreate();
        if (event.key === 'Escape') {
          creating = false;
          newName = '';
        }
      }}
      autofocus
      aria-label="Nom du nouveau profil"
    />
  {:else}
    <button
      type="button"
      class="flex h-10 items-center justify-center gap-2 rounded-xl border border-dashed border-app-border text-label text-app-muted hover:bg-app-hover"
      onclick={() => (creating = true)}
    >
      <i class="ph ph-plus" aria-hidden="true"></i>
      Nouveau profil
    </button>
  {/if}
</div>
