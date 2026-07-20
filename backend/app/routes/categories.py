"""Category listing."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Category

router = APIRouter(tags=["categories"])


@router.get("/categories")
def list_categories(session: Session = Depends(get_session)):
    return session.exec(select(Category).order_by(Category.name)).all()
