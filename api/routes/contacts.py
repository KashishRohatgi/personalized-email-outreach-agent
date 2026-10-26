from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent.logging import actions
from agent.services.activity_service import log_activity
from agent.validators import ContactCreate, ContactRead, ContactUpdate
from database.models import Contact, Profile
from database.session import get_db

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _validate_profile_id(db: Session, profile_id: int | None) -> None:
    if profile_id is not None and db.get(Profile, profile_id) is None:
        raise HTTPException(
            status_code=422, detail="profile_id does not reference an existing profile"
        )


@router.post("/", response_model=ContactRead, status_code=201)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)):
    _validate_profile_id(db, payload.profile_id)
    contact = Contact(**payload.model_dump(mode="json"))
    db.add(contact)
    db.flush()
    log_activity(
        db,
        actions.CONTACT_CREATED,
        {"contact_id": contact.id, "name": contact.name},
    )
    db.refresh(contact)
    return contact


@router.get("/", response_model=list[ContactRead])
def list_contacts(db: Session = Depends(get_db)):
    stmt = select(Contact).order_by(Contact.created_at.desc(), Contact.id.desc())
    return list(db.scalars(stmt).all())


@router.get("/{contact_id}", response_model=ContactRead)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.get(Contact, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: int,
    payload: ContactUpdate,
    db: Session = Depends(get_db),
):
    contact = db.get(Contact, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    data = payload.model_dump(mode="json", exclude_unset=True)
    if "profile_id" in data:
        _validate_profile_id(db, data["profile_id"])
    for key, value in data.items():
        setattr(contact, key, value)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.get(Contact, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
    return None