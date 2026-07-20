"""Tile placement, moves and clearing."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from ..database import get_session
from ..events import broadcast
from ..models import GRID_COLS, GRID_ROWS, Action, Page, Tile
from ..schemas import TileCreate, TileUpdate, serialize_tile

router = APIRouter(tags=["tiles"])


def _validate_slot(row: int, col: int) -> None:
    if not (0 <= row < GRID_ROWS):
        raise HTTPException(422, f"row must be between 0 and {GRID_ROWS - 1}")
    if not (0 <= col < GRID_COLS):
        raise HTTPException(422, f"col must be between 0 and {GRID_COLS - 1}")


def _tile_at(session: Session, page_id: str, row: int, col: int) -> Optional[Tile]:
    return session.exec(
        select(Tile).where(Tile.page_id == page_id, Tile.row == row, Tile.col == col)
    ).first()


@router.post("/tiles", status_code=201)
def place_tile(body: TileCreate, session: Session = Depends(get_session)):
    """Place an action on a slot. Placing onto an occupied slot replaces it."""
    if session.get(Page, body.page_id) is None:
        raise HTTPException(404, "page not found")
    _validate_slot(body.row, body.col)
    if body.action_id is not None and session.get(Action, body.action_id) is None:
        raise HTTPException(404, "action not found")

    tile = _tile_at(session, body.page_id, body.row, body.col)
    if tile is None:
        tile = Tile(
            page_id=body.page_id,
            row=body.row,
            col=body.col,
            action_id=body.action_id,
            custom_label=body.custom_label,
            custom_icon=body.custom_icon,
        )
    else:
        tile.action_id = body.action_id
        tile.custom_label = body.custom_label
        tile.custom_icon = body.custom_icon

    session.add(tile)
    session.commit()
    session.refresh(tile)

    broadcast("tile_updated", tile_id=tile.id, page_id=tile.page_id)
    return serialize_tile(session, tile)


@router.patch("/tiles/{tile_id}")
def update_tile(
    tile_id: str, body: TileUpdate, session: Session = Depends(get_session)
):
    """Update a tile. Moving onto an occupied slot swaps the two tiles."""
    tile = session.get(Tile, tile_id)
    if tile is None:
        raise HTTPException(404, "tile not found")

    data = body.model_dump(exclude_unset=True)
    if "action_id" in data and data["action_id"] is not None:
        if session.get(Action, data["action_id"]) is None:
            raise HTTPException(404, "action not found")

    for field in ("action_id", "custom_label", "custom_icon"):
        if field in data:
            setattr(tile, field, data[field])

    new_row = data.get("row", tile.row)
    new_col = data.get("col", tile.col)
    if (new_row, new_col) != (tile.row, tile.col):
        _validate_slot(new_row, new_col)
        origin_row, origin_col = tile.row, tile.col
        occupant = _tile_at(session, tile.page_id, new_row, new_col)

        if occupant is not None and occupant.id != tile.id:
            # Swap the two tiles. The (page_id, row, col) unique index forbids a
            # direct exchange, so park the occupant off-grid in between.
            occupant.row, occupant.col = -1, -1
            session.add(occupant)
            session.flush()

            tile.row, tile.col = new_row, new_col
            session.add(tile)
            session.flush()

            occupant.row, occupant.col = origin_row, origin_col
            session.add(occupant)
        else:
            tile.row, tile.col = new_row, new_col

    session.add(tile)
    session.commit()
    session.refresh(tile)

    broadcast("tile_updated", tile_id=tile.id, page_id=tile.page_id)
    return serialize_tile(session, tile)


@router.delete("/tiles/{tile_id}", status_code=204)
def clear_tile(tile_id: str, session: Session = Depends(get_session)):
    tile = session.get(Tile, tile_id)
    if tile is None:
        raise HTTPException(404, "tile not found")

    page_id = tile.page_id
    session.delete(tile)
    session.commit()

    broadcast("tile_updated", tile_id=tile_id, page_id=page_id)
    return Response(status_code=204)
