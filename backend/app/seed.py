"""First-run seeding.

Everything seeded uses the ``demo`` action type so the deck is fully usable
without OBS, Spotify or any other external service configured.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .database import engine
from .models import Action, ActionType, Category, Page, Profile, Tile

# (display name, color token, phosphor icon)
CATEGORIES: list[tuple[str, str, str]] = [
    ("Stream", "stream", "broadcast"),
    ("PC", "pc", "desktop"),
    ("Games", "games", "game-controller"),
    ("Meeting", "meeting", "video-camera"),
    ("Media", "media", "music-notes"),
]

# color token -> [(label, phosphor icon), ...]
ACTIONS: dict[str, list[tuple[str, str]]] = {
    "stream": [
        ("Go Live", "broadcast"),
        ("Record", "record"),
        ("Scene: Cam", "video-camera"),
        ("Scene: Screen", "monitor"),
        ("Mute Mic", "microphone-slash"),
        ("Stinger", "lightning"),
    ],
    "pc": [
        ("Lock", "lock"),
        ("Sleep", "moon"),
        ("Screenshot", "camera"),
        ("Volume Up", "speaker-high"),
        ("Volume Down", "speaker-low"),
        ("Terminal", "terminal-window"),
    ],
    "games": [
        ("Steam", "game-controller"),
        ("Discord", "discord-logo"),
        ("Clip That", "film-strip"),
        ("Overlay", "cards"),
        ("FPS Counter", "gauge"),
        ("Big Picture", "television"),
    ],
    "meeting": [
        ("Mute", "microphone-slash"),
        ("Camera Off", "video-camera-slash"),
        ("Share Screen", "screencast"),
        ("Raise Hand", "hand"),
        ("Chat", "chat-circle"),
        ("Leave", "phone-x"),
    ],
    "media": [
        ("Play / Pause", "play-pause"),
        ("Next", "skip-forward"),
        ("Previous", "skip-back"),
        ("Volume Up", "speaker-high"),
        ("Like", "heart"),
        ("Shuffle", "shuffle"),
    ],
}


# Real, service-backed actions added alongside the demo catalog. Each one is
# inert until the matching service is configured — firing an unconfigured tile
# returns an error message rather than doing anything.
# (color token, label, icon, type, endpoint, params)
REAL_ACTIONS: list[tuple[str, str, str, ActionType, str | None, dict]] = [
    ("stream", "OBS · Scène Caméra", "video-camera", ActionType.obs, None,
     {"request": "SetCurrentProgramScene", "args": {"sceneName": "Camera"}}),
    ("stream", "OBS · Scène Écran", "monitor", ActionType.obs, None,
     {"request": "SetCurrentProgramScene", "args": {"sceneName": "Screen"}}),
    ("stream", "OBS · Démarrer le stream", "broadcast", ActionType.obs, None,
     {"request": "StartStream", "args": {}}),
    ("stream", "OBS · Enregistrement", "record", ActionType.obs, None,
     {"request": "ToggleRecord", "args": {}}),
    ("media", "Spotify · Lecture/Pause", "play-pause", ActionType.spotify, None,
     {"command": "toggle"}),
    ("media", "Spotify · Suivant", "skip-forward", ActionType.spotify, None,
     {"command": "next"}),
    ("media", "Spotify · Volume 40%", "speaker-low", ActionType.spotify, None,
     {"command": "volume", "value": 40}),
    ("pc", "PC · Verrouiller", "lock", ActionType.pc, None,
     {"combo": ["cmd", "l"]}),
    ("pc", "PC · Capture d'écran", "camera", ActionType.pc, None,
     {"combo": ["cmd", "shift", "s"]}),
    ("meeting", "Meet · Micro", "microphone-slash", ActionType.meeting, None,
     {"platform": "meet", "command": "mute"}),
    ("meeting", "Zoom · Micro", "microphone-slash", ActionType.meeting, None,
     {"platform": "zoom", "command": "mute"}),
    ("games", "Lancer Steam", "game-controller", ActionType.launcher, None,
     {"launch": "steam"}),
]


def _ensure_real_actions(session: Session) -> int:
    """Add any missing service-backed action. Idempotent, matched on label."""
    categories = {c.color: c for c in session.exec(select(Category)).all()}
    existing = {a.label for a in session.exec(select(Action)).all()}

    added = 0
    for token, label, icon, kind, endpoint, params in REAL_ACTIONS:
        if label in existing or token not in categories:
            continue
        session.add(
            Action(
                category_id=categories[token].id,
                label=label,
                icon=icon,
                type=kind,
                endpoint=endpoint,
                params=params,
            )
        )
        added += 1

    if added:
        session.commit()
    return added


def seed() -> bool:
    """Populate an empty database. Returns True if the first-run seeding ran."""
    with Session(engine) as session:
        if session.exec(select(Profile)).first() is not None:
            # Already seeded, but the catalog may predate the real actions.
            _ensure_real_actions(session)
            return False

        profile = Profile(name="Home", icon="house", active=True)
        session.add(profile)
        session.commit()
        session.refresh(profile)

        categories: dict[str, Category] = {}
        pages: dict[str, Page] = {}
        for position, (name, token, icon) in enumerate(CATEGORIES):
            category = Category(name=name, color=token, icon=icon)
            page = Page(
                profile_id=profile.id,
                name=name,
                color=token,
                position=position,
                icon=icon,
            )
            session.add(category)
            session.add(page)
            categories[token] = category
            pages[token] = page
        session.commit()

        actions: dict[str, list[Action]] = {}
        for token, items in ACTIONS.items():
            session.refresh(categories[token])
            actions[token] = []
            for label, icon in items:
                action = Action(
                    category_id=categories[token].id,
                    label=label,
                    icon=icon,
                    type=ActionType.demo,
                    endpoint=None,
                    params={},
                )
                session.add(action)
                actions[token].append(action)
        session.commit()

        # Pre-place the Stream actions on the first row of the Stream page so a
        # fresh install has something tappable out of the box.
        session.refresh(pages["stream"])
        for col, action in enumerate(actions["stream"][:5]):
            session.refresh(action)
            session.add(
                Tile(page_id=pages["stream"].id, action_id=action.id, row=0, col=col)
            )
        session.commit()

        _ensure_real_actions(session)
        return True
