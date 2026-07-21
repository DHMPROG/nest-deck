"""Action catalog: listing, search, and user-defined actions.

The spec only calls for `GET /api/actions`, but a deck whose catalog is frozen
at seed time cannot be made your own — the write endpoints below let the Editor
define custom macros and launchers.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, col, or_, select

from ..database import get_session
from ..events import broadcast
from ..models import Action, ActionType, Category, Tile
from ..schemas import ActionCreate, ActionUpdate, serialize_action

router = APIRouter(tags=["actions"])


def _validate(kind: ActionType, endpoint: Optional[str], params: dict[str, Any]) -> None:
    """Reject configurations that could never fire, with a readable reason.

    Deliberately shallow: it checks the shape a handler needs, not whether the
    target exists. An OBS scene name or a Steam binary can only be resolved at
    fire time, and a tile for an app you have not installed yet is legitimate.
    """
    params = params or {}

    if kind is ActionType.pc:
        combo, text = params.get("combo"), params.get("text")
        if not combo and not text and not params.get("launch"):
            raise HTTPException(422, "une macro PC demande 'combo', 'text' ou 'launch'")
        if combo is not None and (
            not isinstance(combo, list)
            or not combo
            or not all(isinstance(key, str) and key for key in combo)
        ):
            raise HTTPException(422, "'combo' doit être une liste de touches non vide")

    elif kind is ActionType.launcher:
        if not params.get("launch") and not params.get("args") and not params.get("shell") and not endpoint:
            raise HTTPException(422, "un lanceur demande une commande à exécuter")

    elif kind is ActionType.obs:
        if not params.get("request"):
            raise HTTPException(422, "une action OBS demande un 'request'")

    elif kind is ActionType.spotify:
        if not params.get("command"):
            raise HTTPException(422, "une action Spotify demande une 'command'")

    elif kind is ActionType.meeting:
        if not params.get("platform") or not params.get("command"):
            raise HTTPException(422, "une action meeting demande 'platform' et 'command'")

    elif kind in (ActionType.fetch, ActionType.open):
        if not endpoint:
            raise HTTPException(422, f"une action {kind.value} demande une URL")


@router.get("/actions")
def list_actions(
    category: Optional[str] = Query(
        None, description="Category id, name or color token (e.g. 'stream')"
    ),
    q: Optional[str] = Query(None, description="Case-insensitive label search"),
    session: Session = Depends(get_session),
):
    statement = select(Action)

    if category:
        matches = session.exec(
            select(Category).where(
                or_(
                    Category.id == category,
                    col(Category.name).ilike(category),
                    col(Category.color).ilike(category),
                )
            )
        ).all()
        category_ids = [c.id for c in matches]
        if not category_ids:
            return []
        statement = statement.where(col(Action.category_id).in_(category_ids))

    if q:
        statement = statement.where(col(Action.label).ilike(f"%{q}%"))

    actions = session.exec(statement.order_by(Action.label)).all()
    return [serialize_action(action) for action in actions]


@router.post("/actions", status_code=201)
def create_action(body: ActionCreate, session: Session = Depends(get_session)):
    if session.get(Category, body.category_id) is None:
        raise HTTPException(404, "category not found")
    _validate(body.type, body.endpoint, body.params)

    action = Action(
        category_id=body.category_id,
        label=body.label,
        icon=body.icon,
        type=body.type,
        endpoint=body.endpoint,
        params=body.params or {},
    )
    session.add(action)
    session.commit()
    session.refresh(action)

    broadcast("action_updated", action_id=action.id)
    return serialize_action(action)


@router.patch("/actions/{action_id}")
def update_action(
    action_id: str, body: ActionUpdate, session: Session = Depends(get_session)
):
    action = session.get(Action, action_id)
    if action is None:
        raise HTTPException(404, "action not found")

    data = body.model_dump(exclude_unset=True)
    if "category_id" in data and session.get(Category, data["category_id"]) is None:
        raise HTTPException(404, "category not found")

    # Validate the resulting state, not just the patch.
    _validate(
        data.get("type", action.type),
        data.get("endpoint", action.endpoint),
        data.get("params", action.params),
    )

    for field, value in data.items():
        setattr(action, field, value)

    session.add(action)
    session.commit()
    session.refresh(action)

    broadcast("action_updated", action_id=action.id)
    return serialize_action(action)


@router.delete("/actions/{action_id}", status_code=204)
def delete_action(action_id: str, session: Session = Depends(get_session)):
    action = session.get(Action, action_id)
    if action is None:
        raise HTTPException(404, "action not found")

    # Tiles hold a foreign key to the action, so clear the slots that used it
    # rather than leaving dangling references behind.
    orphaned = session.exec(select(Tile).where(Tile.action_id == action_id)).all()
    for tile in orphaned:
        session.delete(tile)

    session.delete(action)
    session.commit()

    for tile in orphaned:
        broadcast("tile_updated", tile_id=tile.id, page_id=tile.page_id)
    broadcast("action_updated", action_id=action_id)

    return Response(status_code=204)
