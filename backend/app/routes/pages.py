"""Page CRUD + the 15-slot tile grid of a page."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from ..database import get_session
from ..events import broadcast
from ..models import GRID_COLS, GRID_ROWS, Page, Profile, Tile
from ..schemas import PageCreate, PageUpdate, PositionUpdate, serialize_slot

router = APIRouter(tags=["pages"])


def delete_page_cascade(session: Session, page: Page) -> None:
    """Delete a page and every tile sitting on it. Caller commits."""
    for tile in session.exec(select(Tile).where(Tile.page_id == page.id)).all():
        session.delete(tile)
    session.delete(page)


def _resequence(session: Session, profile_id: str) -> None:
    """Rewrite positions to a dense 0..n-1 range, preserving current order."""
    siblings = session.exec(
        select(Page).where(Page.profile_id == profile_id).order_by(Page.position)
    ).all()
    for index, page in enumerate(siblings):
        page.position = index
        session.add(page)


@router.post("/pages", status_code=201)
def create_page(body: PageCreate, session: Session = Depends(get_session)):
    if session.get(Profile, body.profile_id) is None:
        raise HTTPException(404, "profile not found")

    if body.position is None:
        existing = session.exec(
            select(Page).where(Page.profile_id == body.profile_id)
        ).all()
        position = len(existing)
    else:
        position = body.position

    page = Page(
        profile_id=body.profile_id,
        name=body.name,
        color=body.color,
        icon=body.icon,
        position=position,
    )
    session.add(page)
    session.commit()
    session.refresh(page)

    broadcast("page_updated", page_id=page.id)
    return page


@router.patch("/pages/{page_id}")
def update_page(
    page_id: str, body: PageUpdate, session: Session = Depends(get_session)
):
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(404, "page not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(page, field, value)

    session.add(page)
    session.commit()
    session.refresh(page)

    broadcast("page_updated", page_id=page.id)
    return page


@router.patch("/pages/{page_id}/position")
def move_page(
    page_id: str, body: PositionUpdate, session: Session = Depends(get_session)
):
    """Move a page to a new index within its profile, then re-densify."""
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(404, "page not found")

    siblings = session.exec(
        select(Page).where(Page.profile_id == page.profile_id).order_by(Page.position)
    ).all()
    siblings = [p for p in siblings if p.id != page.id]

    target = max(0, min(body.position, len(siblings)))
    siblings.insert(target, page)
    for index, sibling in enumerate(siblings):
        sibling.position = index
        session.add(sibling)

    session.commit()
    session.refresh(page)

    broadcast("page_updated", page_id=page.id)
    return page


@router.delete("/pages/{page_id}", status_code=204)
def delete_page(page_id: str, session: Session = Depends(get_session)):
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(404, "page not found")

    profile_id = page.profile_id
    delete_page_cascade(session, page)
    session.commit()
    _resequence(session, profile_id)
    session.commit()

    broadcast("page_updated", page_id=page_id)
    return Response(status_code=204)


@router.get("/pages/{page_id}/tiles")
def list_page_tiles(page_id: str, session: Session = Depends(get_session)):
    """Always returns the full 5x3 grid — 15 slots, empty ones with tile=null."""
    if session.get(Page, page_id) is None:
        raise HTTPException(404, "page not found")

    tiles = session.exec(select(Tile).where(Tile.page_id == page_id)).all()
    by_slot = {(tile.row, tile.col): tile for tile in tiles}

    return [
        serialize_slot(session, row, col, by_slot.get((row, col)))
        for row in range(GRID_ROWS)
        for col in range(GRID_COLS)
    ]
