# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from fastapi import BackgroundTasks
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud import crud_match
from app.db import models
from app.events import match_handlers
from app.schemas import schemas


def get_need(db: Session, need_id: int):
    return db.query(models.Need).filter(models.Need.id == need_id).first()


def get_needs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Need).offset(skip).limit(limit).all()


async def create_need(
    db: Session, need: schemas.NeedCreate, owner_id: int, background_tasks: BackgroundTasks
):
    db_need = models.Need(
        title=need.title,
        description=need.description,
        required_tasks=need.required_tasks,
        required_skills=need.required_skills,
        num_volunteers_needed=need.num_volunteers_needed,
        format=need.format,
        location_details=need.location_details,
        contact_name=need.contact_name,
        contact_email=need.contact_email,
        contact_phone=need.contact_phone,
        owner_id=owner_id,
    )
    try:
        db.add(db_need)
        db.commit()
        db.refresh(db_need)

        background_tasks.add_task(match_handlers.trigger_need_matching, db_need.id)

        return db_need
    except IntegrityError:
        db.rollback()
        return None


async def update_need(
    db: Session, need_id: int, need: schemas.NeedCreate, owner_id: int, background_tasks: BackgroundTasks
):
    db_need = (
        db.query(models.Need).filter(models.Need.id == need_id, models.Need.owner_id == owner_id).first()
    )
    if db_need:
        for key, value in need.model_dump(exclude_unset=True).items():
            setattr(db_need, key, value)
        db.commit()
        db.refresh(db_need)

        background_tasks.add_task(match_handlers.trigger_need_matching, db_need.id)

        return db_need
    return None


def delete_need(db: Session, need_id: int, owner_id: int):
    db_need = (
        db.query(models.Need).filter(models.Need.id == need_id, models.Need.owner_id == owner_id).first()
    )
    if db_need:
        db.delete(db_need)
        db.commit()
        crud_match.delete_matches_for_need(db, need_id)
        return True
    return False
