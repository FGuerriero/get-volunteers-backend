# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud import crud_match
from app.db import models
from app.schemas import schemas
from app.events import match_handlers
from app.utils.security import get_password_hash


def get_volunteer(db: Session, volunteer_id: int):
    return (
        db.query(models.Volunteer).filter(models.Volunteer.id == volunteer_id).first()
    )


def get_volunteer_by_email(db: Session, email: str):
    return db.query(models.Volunteer).filter(models.Volunteer.email == email).first()


def get_volunteers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Volunteer).offset(skip).limit(limit).all()


async def create_volunteer(db: Session, volunteer: schemas.VolunteerCreate):
    hashed_password = get_password_hash(volunteer.password)
    db_volunteer = models.Volunteer(
        name=volunteer.name,
        email=volunteer.email,
        password=hashed_password,
        phone=volunteer.phone,
        about_me=volunteer.about_me,
        skills=volunteer.skills,
        volunteer_interests=volunteer.volunteer_interests,
        location=volunteer.location,
        availability=volunteer.availability,
        is_active=1
    )
    try:
        db.add(db_volunteer)
        db.commit()
        db.refresh(db_volunteer)

        await match_handlers.trigger_volunteer_matching(db, db_volunteer)

        return db_volunteer
    except IntegrityError:
        db.rollback()
        return None  # Indicate that creation failed, likely due to duplicate email


async def update_volunteer(db: Session, volunteer_id: int, volunteer: schemas.VolunteerCreate):
    db_volunteer = db.query(models.Volunteer).filter(
        models.Volunteer.id == volunteer_id
    ).first()
    if db_volunteer:
        update_data = volunteer.model_dump(exclude_unset=True, exclude={'password'})
        for key, value in update_data.items():
            setattr(db_volunteer, key, value)

        if volunteer.password:
            db_volunteer.password = get_password_hash(volunteer.password)

        db.commit()
        db.refresh(db_volunteer)

        await match_handlers.trigger_volunteer_matching(db, db_volunteer)

        return db_volunteer
    return None


def delete_volunteer(db: Session, volunteer_id: int):
    db_volunteer = db.query(models.Volunteer).filter(
        models.Volunteer.id == volunteer_id
    ).first()
    if db_volunteer:
        db.delete(db_volunteer)
        db.commit()
        crud_match.delete_matches_for_volunteer(db, volunteer_id)
        return True
    return False
