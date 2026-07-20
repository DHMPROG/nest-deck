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


def seed() -> bool:
    """Populate an empty database. Returns True if seeding ran."""
    with Session(engine) as session:
        if session.exec(select(Profile)).first() is not None:
            return False  # already seeded

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

        return True
