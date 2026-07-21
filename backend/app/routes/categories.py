"""Categories: listing, plus creation so the Editor can group custom actions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from ..database import get_session
from ..events import broadcast
from ..models import Action, Category
from ..schemas import CategoryCreate, CategoryUpdate

router = APIRouter(tags=["categories"])


@router.get("/categories")
def list_categories(session: Session = Depends(get_session)):
    return session.exec(select(Category).order_by(Category.name)).all()


@router.post("/categories", status_code=201)
def create_category(body: CategoryCreate, session: Session = Depends(get_session)):
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "le nom de la catégorie est requis")

    existing = session.exec(select(Category).where(Category.name == name)).first()
    if existing is not None:
        raise HTTPException(409, "une catégorie porte déjà ce nom")

    category = Category(name=name, color=body.color, icon=body.icon)
    session.add(category)
    session.commit()
    session.refresh(category)

    broadcast("category_updated", category_id=category.id)
    return category


@router.patch("/categories/{category_id}")
def update_category(
    category_id: str, body: CategoryUpdate, session: Session = Depends(get_session)
):
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(404, "category not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    session.add(category)
    session.commit()
    session.refresh(category)

    broadcast("category_updated", category_id=category.id)
    return category


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: str, session: Session = Depends(get_session)):
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(404, "category not found")

    # Actions carry a non-nullable category, so refuse rather than cascade —
    # deleting a category should never silently take a chunk of the catalog
    # (and the tiles using it) with it.
    used = session.exec(select(Action).where(Action.category_id == category_id)).first()
    if used is not None:
        raise HTTPException(409, "cette catégorie contient encore des actions")

    session.delete(category)
    session.commit()

    broadcast("category_updated", category_id=category_id)
    return Response(status_code=204)
