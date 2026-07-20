"""Profile CRUD + activation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from ..database import get_session
from ..events import broadcast
from ..models import Page, Profile
from ..schemas import ProfileCreate, ProfileUpdate
from .pages import delete_page_cascade

router = APIRouter(tags=["profiles"])


@router.get("/profiles")
def list_profiles(session: Session = Depends(get_session)):
    return session.exec(select(Profile).order_by(Profile.created_at)).all()


@router.post("/profiles", status_code=201)
def create_profile(body: ProfileCreate, session: Session = Depends(get_session)):
    profile = Profile(name=body.name, icon=body.icon)
    session.add(profile)
    session.commit()
    session.refresh(profile)

    broadcast("profile_updated", profile_id=profile.id)
    return profile


@router.patch("/profiles/{profile_id}")
def update_profile(
    profile_id: str, body: ProfileUpdate, session: Session = Depends(get_session)
):
    profile = session.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(404, "profile not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    session.add(profile)
    session.commit()
    session.refresh(profile)

    broadcast("profile_updated", profile_id=profile.id)
    return profile


@router.patch("/profiles/{profile_id}/activate")
def activate_profile(profile_id: str, session: Session = Depends(get_session)):
    profile = session.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(404, "profile not found")

    # Exactly one active profile at a time.
    for candidate in session.exec(select(Profile)).all():
        candidate.active = candidate.id == profile_id
        session.add(candidate)
    session.commit()
    session.refresh(profile)

    broadcast("profile_activated", profile_id=profile.id)
    return profile


@router.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: str, session: Session = Depends(get_session)):
    profile = session.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(404, "profile not found")

    total = len(session.exec(select(Profile)).all())
    if total <= 1:
        raise HTTPException(400, "cannot delete the only profile")

    was_active = profile.active
    for page in session.exec(
        select(Page).where(Page.profile_id == profile_id)
    ).all():
        delete_page_cascade(session, page)
    session.delete(profile)
    session.commit()

    if was_active:
        # Never leave the deck without an active profile.
        fallback = session.exec(select(Profile).order_by(Profile.created_at)).first()
        if fallback is not None:
            fallback.active = True
            session.add(fallback)
            session.commit()
            broadcast("profile_activated", profile_id=fallback.id)

    return Response(status_code=204)


@router.get("/profiles/{profile_id}/pages")
def list_profile_pages(profile_id: str, session: Session = Depends(get_session)):
    if session.get(Profile, profile_id) is None:
        raise HTTPException(404, "profile not found")

    return session.exec(
        select(Page).where(Page.profile_id == profile_id).order_by(Page.position)
    ).all()
