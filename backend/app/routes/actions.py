"""Action catalog listing and search."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, col, or_, select

from ..database import get_session
from ..models import Action, Category
from ..schemas import serialize_action

router = APIRouter(tags=["actions"])


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
