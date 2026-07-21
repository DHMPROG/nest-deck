# Lancer Nest Deck et caster sur le Nest Hub

Guide de développement local : démarrer le backend et le frontend, puis envoyer
le Deck sur le Google Nest Hub Max via Chromecast.

> Le déploiement Docker (`docker compose up -d`) arrive en phase 7. Ce document
> décrit la procédure manuelle utilisable dès maintenant.

---

## 1. Prérequis

| Outil    | Version utilisée | Note                                                   |
| -------- | ---------------- | ------------------------------------------------------ |
| Python   | 3.11+            | 3.14 fonctionne en local ; Docker épingle 3.11         |
| Node.js  | 22+              | testé avec Node 24                                     |
| `catt`   | dernière         | client Chromecast en ligne de commande                 |

Le PC et le Nest Hub doivent être **sur le même réseau Wi-Fi**.

---

## 2. Backend (FastAPI)

### Installation (une seule fois)

```powershell
cd "C:\Users\Rashfig\Documents\Projects de oufs\nest-deck\backend"
python -m venv .venv
.\.venv\Scripts\pip install fastapi "uvicorn[standard]" sqlmodel sse-starlette
```

Le dossier `.venv/` est déjà dans le `.gitignore`.

Pour les intégrations réelles (OBS, Spotify, macros clavier) :

```powershell
.\.venv\Scripts\pip install obsws-python spotipy pynput
```

> Ces trois-là restent optionnelles : les handlers les importent paresseusement,
> donc l'application démarre sans elles. Seul le déclenchement d'une action du
> type concerné renverra alors une erreur explicite.

### Démarrage

```powershell
cd "C:\Users\Rashfig\Documents\Projects de oufs\nest-deck\backend"
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

- API : http://localhost:8000
- Documentation interactive (Swagger) : http://localhost:8000/docs
- Base SQLite : `data/deck.db`, créée et remplie automatiquement au premier
  démarrage (1 profil, 5 pages, 5 catégories, 30 actions `demo`).

**Le backend n'a pas besoin d'être exposé sur le réseau.** Il reste sur
`127.0.0.1` : c'est le serveur frontend qui relaie les appels `/api` (voir §4).

---

## 3. Frontend (SvelteKit)

### Installation (une seule fois)

```powershell
cd "C:\Users\Rashfig\Documents\Projects de oufs\nest-deck\frontend"
npm install
```

### Mode développement — pour coder

```powershell
npm run dev
```

→ http://localhost:5173 (Deck) et http://localhost:5173/editor (Éditeur)

Rechargement à chaud activé.

### Mode production — pour tester sur le Nest Hub

```powershell
npm run build
npm run preview -- --host 0.0.0.0
```

→ http://localhost:4173 et http://192.168.2.11:4173 sur le réseau

C'est ce mode qu'il faut caster : c'est le build réellement livré, sans le
surcoût du serveur de développement.

---

## 4. Pourquoi un seul port suffit

Le client API (`src/lib/services/api.ts`) appelle `/api/...` en **relatif**.
Le Nest Hub charge donc la page sur le port du frontend, et c'est Vite qui
relaie vers le backend en local :

```
Nest Hub ──► 192.168.2.11:4173 ──► (proxy Vite) ──► 127.0.0.1:8000
```

Conséquence : **seul le port 4173** (ou 5173 en dev) doit être joignable depuis
le réseau. Le backend reste inaccessible de l'extérieur, ce qui est le
comportement souhaité.

Le proxy est configuré dans `vite.config.ts`, pour `server` **et** `preview` —
Vite n'hérite pas automatiquement du proxy en mode preview.

---

## 5. Ouvrir le pare-feu Windows

C'est l'étape qui bloque le plus souvent. Par défaut Windows refuse presque
tout le trafic entrant, surtout si le réseau est classé **Public**.

### Vérifier le classement du réseau

```powershell
Get-NetConnectionProfile | Select-Object Name, NetworkCategory
```

### Autoriser le port

Dans un **PowerShell administrateur** (Win + X → « Terminal (administrateur) »,
ou Ctrl + Maj + Entrée depuis la recherche Windows) :

```powershell
New-NetFirewallRule -DisplayName "Nest Deck 4173" -Direction Inbound -Protocol TCP -LocalPort 4173 -Action Allow -Profile Any
```

Pour vérifier que la console est bien élevée (doit renvoyer `True`) :

```powershell
([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
```

Alternative : basculer le réseau domestique en privé (nécessite aussi l'admin).

```powershell
Set-NetConnectionProfile -Name "VIRGIN580" -NetworkCategory Private
```

> Un test depuis le PC lui-même (`curl http://192.168.2.11:4173`) **ne prouve
> pas** que le pare-feu laisse entrer une machine tierce : la boucle locale
> contourne la règle. Seul un accès depuis un autre appareil est probant.

---

## 6. Caster sur le Nest Hub

### Installer catt

```powershell
pip install catt
```

### Trouver l'appareil

```powershell
catt scan
```

La commande liste les appareils Cast du réseau avec leur nom et leur IP.

### Envoyer le Deck

```powershell
catt -d "<IP ou nom du Nest Hub>" cast_site http://192.168.2.11:4173/
```

Exemple : `catt -d "Salon" cast_site http://192.168.2.11:4173/`

### Commandes utiles

```powershell
catt -d "<appareil>" stop      # arrêter la diffusion
catt -d "<appareil>" status    # état courant
```

> **Timeout Google.** Une page castée est coupée au bout de ~10 minutes
> d'inactivité. Le composant `HeartbeatKeepAlive.svelte` recharge la page toutes
> les 9 minutes pour contrer ça (comportement `ha-catt-fix` embarqué). Un bref
> clignotement toutes les 9 minutes est donc normal.

---

## 7. Tester le Deck comme sur le Hub, depuis Chrome

Une fenêtre Chrome classique ne fait pas 1280×800 utiles (la barre d'onglets
mange la hauteur). Pour reproduire l'écran du Nest Hub :

**F12** → **Ctrl + Maj + M** (Toggle device toolbar) → choisir **Responsive** →
saisir **1280 × 800**.

---

## 8. Dépannage

| Symptôme | Cause probable | Solution |
| --- | --- | --- |
| `New-NetFirewallRule : Accès refusé` | Console non élevée | Ouvrir PowerShell **en administrateur** (le préfixe `!` de Claude Code n'est pas élevé) |
| Le Hub affiche une page blanche ou ne charge pas | Pare-feu, ou mauvaise IP | Vérifier §5, puis retester l'URL depuis un téléphone du même Wi-Fi |
| `Internal Server Error` dans la barre de statut | Le backend ne tourne plus | Le proxy Vite renvoie 500 si l'upstream est mort — relancer uvicorn |
| Pastille rouge en haut à droite | Backend injoignable | Idem. La dégradation est volontaire : le Deck ne plante pas |
| `[Errno 10048] error while attempting to bind` | Port 8000 déjà utilisé | Un uvicorn tourne déjà : `netstat -ano \| findstr :8000` puis `taskkill /PID <pid> /F` |
| L'IP `192.168.2.11` ne répond plus | Bail DHCP renouvelé | Récupérer la nouvelle IP : `Get-NetIPAddress -AddressFamily IPv4` |
| Bordures des cases vides invisibles sur le Hub | `color-mix()` non supporté (Chrome < 111) | Signaler : à remplacer par des valeurs `rgb()` précalculées depuis `theme.ts` |
| Une action OBS met ~4 s à répondre en erreur | OBS n'est pas lancé | Comportement normal : le handler attend l'expiration du délai avant d'abandonner |
| `pynput unavailable (headless host?)` | Backend dans Docker, sans périphérique d'entrée | Les macros clavier doivent tourner sur la machine à piloter, pas dans le conteneur |

---

## 9. Réinitialiser la base

Le seeding ne s'exécute que si la base est vide. Pour repartir de zéro :

```powershell
# backend arrêté
Remove-Item "C:\Users\Rashfig\Documents\Projects de oufs\nest-deck\data\deck.db"
```

Elle sera recréée et re-remplie au démarrage suivant.

---

## Récapitulatif des ports

| Port | Service | Exposé au réseau ? |
| ---- | ------- | ------------------ |
| 8000 | Backend FastAPI | Non — `127.0.0.1` uniquement |
| 5173 | Frontend (dev) | Seulement avec `--host` |
| 4173 | Frontend (preview / prod) | Oui, c'est le port à caster |
