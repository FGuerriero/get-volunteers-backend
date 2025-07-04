from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import models
from app.schemas import schemas


def get_volunteer(db: Session, volunteer_id: int):
    return (
        db.query(models.Volunteer).filter(models.Volunteer.id == volunteer_id).first()
    )


def get_volunteer_by_email(db: Session, email: str):
    return db.query(models.Volunteer).filter(models.Volunteer.email == email).first()


def get_volunteers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Volunteer).offset(skip).limit(limit).all()


def create_volunteer(db: Session, volunteer: schemas.VolunteerCreate):
    db_volunteer = models.Volunteer(
        name=volunteer.name,
        email=volunteer.email,
        phone=volunteer.phone,
        about_me=volunteer.about_me,
        skills=volunteer.skills,
        volunteer_interests=volunteer.volunteer_interests,
        location=volunteer.location,
        availability=volunteer.availability,
    )
    try:
        db.add(db_volunteer)
        db.commit()
        db.refresh(db_volunteer)
        return db_volunteer
    except IntegrityError:
        db.rollback()
        return None  # Indicate that creation failed, likely due to duplicate email


def update_volunteer(
    db: Session, volunteer_id: int, volunteer: schemas.VolunteerCreate
):
    db_volunteer = (
        db.query(models.Volunteer).filter(models.Volunteer.id == volunteer_id).first()
    )
    if db_volunteer:
        for key, value in volunteer.model_dump(exclude_unset=True).items():
            setattr(db_volunteer, key, value)
        db.commit()
        db.refresh(db_volunteer)
        return db_volunteer
    return None


def delete_volunteer(db: Session, volunteer_id: int):
    db_volunteer = (
        db.query(models.Volunteer).filter(models.Volunteer.id == volunteer_id).first()
    )
    if db_volunteer:
        db.delete(db_volunteer)
        db.commit()
        return True
    return False
