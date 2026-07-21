"""First-run seeding, plus in-place catalog upgrades on later boots.

The catalog ships pre-configured rather than as inert ``demo`` entries, so a
fresh install can already drive the machine. Media and volume ride the system
media keys, which need no setup at all; OBS and the launchers only work once
the matching app is installed and running, and say so when it is not.
"""

from __future__ import annotations

import json

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

# The catalog ships pre-configured: every entry targets a real service rather
# than the inert `demo` type, so a fresh install can already drive the machine.
# Media and volume use system media keys, which work with Spotify, YouTube, VLC
# and anything else without an OAuth round trip.
#
# color token -> [(label, icon, type, endpoint, params), ...]
Entry = tuple[str, str, ActionType, "str | None", dict]

ACTIONS: dict[str, list[Entry]] = {
    "stream": [
        ("Go Live", "broadcast", ActionType.obs, None, {"request": "ToggleStream", "args": {}}),
        ("Record", "record", ActionType.obs, None, {"request": "ToggleRecord", "args": {}}),
        ("Scene: Cam", "video-camera", ActionType.obs, None,
         {"request": "SetCurrentProgramScene", "args": {"sceneName": "Camera"}}),
        ("Scene: Screen", "monitor", ActionType.obs, None,
         {"request": "SetCurrentProgramScene", "args": {"sceneName": "Screen"}}),
        ("Mute Mic", "microphone-slash", ActionType.obs, None,
         {"request": "ToggleInputMute", "args": {"inputName": "Mic/Aux"}}),
        ("Stinger", "lightning", ActionType.obs, None,
         {"request": "SetCurrentProgramScene", "args": {"sceneName": "Stinger"}}),
    ],
    "pc": [
        ("Lock", "lock", ActionType.pc, None, {"combo": ["cmd", "l"]}),
        ("Sleep", "moon", ActionType.launcher, None,
         {"shell": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"}),
        ("Screenshot", "camera", ActionType.pc, None, {"combo": ["cmd", "shift", "s"]}),
        ("Volume Up", "speaker-high", ActionType.pc, None, {"combo": ["media_volume_up"]}),
        ("Volume Down", "speaker-low", ActionType.pc, None, {"combo": ["media_volume_down"]}),
        ("Terminal", "terminal-window", ActionType.launcher, None, {"launch": "wt.exe"}),
    ],
    "games": [
        ("Steam", "game-controller", ActionType.launcher, None, {"launch": "steam"}),
        ("Discord", "discord-logo", ActionType.launcher, None, {"launch": "discord"}),
        ("Clip That", "film-strip", ActionType.pc, None, {"combo": ["cmd", "alt", "g"]}),
        ("Overlay", "cards", ActionType.pc, None, {"combo": ["cmd", "g"]}),
        ("Explorateur", "folder-open", ActionType.launcher, None, {"launch": "explorer.exe"}),
        ("Big Picture", "television", ActionType.launcher, None,
         {"args": ["steam", "-bigpicture"]}),
    ],
    "meeting": [
        ("Meet · Micro", "microphone-slash", ActionType.meeting, None,
         {"platform": "meet", "command": "mute"}),
        ("Meet · Caméra", "video-camera-slash", ActionType.meeting, None,
         {"platform": "meet", "command": "camera"}),
        ("Meet · Main levée", "hand", ActionType.meeting, None,
         {"platform": "meet", "command": "hand"}),
        ("Meet · Chat", "chat-circle", ActionType.meeting, None,
         {"platform": "meet", "command": "chat"}),
        ("Zoom · Partager", "screencast", ActionType.meeting, None,
         {"platform": "zoom", "command": "share"}),
        ("Zoom · Quitter", "phone-x", ActionType.meeting, None,
         {"platform": "zoom", "command": "leave"}),
    ],
    "media": [
        ("Play / Pause", "play-pause", ActionType.pc, None, {"combo": ["media_play_pause"]}),
        ("Next", "skip-forward", ActionType.pc, None, {"combo": ["media_next"]}),
        ("Previous", "skip-back", ActionType.pc, None, {"combo": ["media_previous"]}),
        ("Volume Up", "speaker-high", ActionType.pc, None, {"combo": ["media_volume_up"]}),
        ("Muet", "speaker-x", ActionType.pc, None, {"combo": ["media_volume_mute"]}),
        ("Spotify", "spotify-logo", ActionType.launcher, None, {"launch": "spotify"}),
    ],
}

# Upgrade path for databases seeded before the catalog was pre-configured:
# (color token, old label) -> the real configuration to apply. Only actions
# still typed `demo` are touched, so anything you customised is left alone.
# A tuple's optional 6th/7th slots rename and re-icon the entry.
UPGRADES: dict[tuple[str, str], tuple[ActionType, dict, str | None, str | None]] = {
    ("games", "FPS Counter"): (ActionType.launcher, {"launch": "explorer.exe"}, "Explorateur", "folder-open"),
    ("meeting", "Mute"): (ActionType.meeting, {"platform": "meet", "command": "mute"}, "Meet · Micro", None),
    ("meeting", "Camera Off"): (ActionType.meeting, {"platform": "meet", "command": "camera"}, "Meet · Caméra", None),
    ("meeting", "Raise Hand"): (ActionType.meeting, {"platform": "meet", "command": "hand"}, "Meet · Main levée", None),
    ("meeting", "Chat"): (ActionType.meeting, {"platform": "meet", "command": "chat"}, "Meet · Chat", None),
    ("meeting", "Share Screen"): (ActionType.meeting, {"platform": "zoom", "command": "share"}, "Zoom · Partager", None),
    ("meeting", "Leave"): (ActionType.meeting, {"platform": "zoom", "command": "leave"}, "Zoom · Quitter", None),
    ("media", "Like"): (ActionType.pc, {"combo": ["media_volume_mute"]}, "Muet", "speaker-x"),
    ("media", "Shuffle"): (ActionType.launcher, {"launch": "spotify"}, "Spotify", "spotify-logo"),
}



def _upgrade_catalog(session: Session) -> int:
    """Give pre-existing `demo` entries a real configuration.

    Idempotent, and deliberately conservative: an action is only touched while
    it is still typed `demo`, so anything already customised — by the seed's
    own upgrade on a previous boot, or by hand in the Editor — is left alone.
    """
    categories = {c.color: c for c in session.exec(select(Category)).all()}
    by_id = {c.id: c for c in categories.values()}

    # (token, label) -> (type, params, new label, new icon)
    plan: dict[tuple[str, str], tuple[ActionType, dict, str | None, str | None]] = {
        (token, label): (kind, params, None, None)
        for token, entries in ACTIONS.items()
        for label, _icon, kind, _endpoint, params in entries
    }
    plan.update(UPGRADES)

    changed = 0
    for action in session.exec(select(Action).where(Action.type == ActionType.demo)).all():
        token = by_id.get(action.category_id)
        if token is None:
            continue
        target = plan.get((token.color, action.label))
        if target is None:
            continue

        kind, params, new_label, new_icon = target
        action.type = kind
        action.params = params
        if new_label:
            action.label = new_label
        if new_icon:
            action.icon = new_icon
        session.add(action)
        changed += 1

    if changed:
        session.commit()
    return changed


def _drop_unused_duplicates(session: Session) -> int:
    """Collapse actions that do exactly the same thing in the same category.

    Earlier versions added service-backed entries next to the demo ones; with
    the demos now upgraded in place, both copies fire identically and only
    clutter the catalog. Two actions are duplicates when their category, type,
    endpoint and params all match.

    A copy that a tile references is always the one kept, so nothing disappears
    from an existing deck.
    """
    used = {t.action_id for t in session.exec(select(Tile)).all() if t.action_id}

    groups: dict[tuple, list[Action]] = {}
    for action in session.exec(select(Action)).all():
        key = (
            action.category_id,
            action.type,
            action.endpoint,
            json.dumps(action.params or {}, sort_keys=True),
        )
        groups.setdefault(key, []).append(action)

    removed = 0
    for copies in groups.values():
        if len(copies) < 2:
            continue
        # Prefer keeping a copy that is already on a page.
        copies.sort(key=lambda a: (a.id not in used, a.label))
        for extra in copies[1:]:
            if extra.id in used:
                continue  # never orphan a placed tile
            session.delete(extra)
            removed += 1

    if removed:
        session.commit()
    return removed


def seed() -> bool:
    """Populate an empty database. Returns True if the first-run seeding ran."""
    with Session(engine) as session:
        if session.exec(select(Profile)).first() is not None:
            # Already seeded, but the catalog may predate the real configs.
            _upgrade_catalog(session)
            _drop_unused_duplicates(session)
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
            for label, icon, kind, endpoint, params in items:
                action = Action(
                    category_id=categories[token].id,
                    label=label,
                    icon=icon,
                    type=kind,
                    endpoint=endpoint,
                    params=params,
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

        return True
