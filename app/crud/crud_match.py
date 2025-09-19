"""
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Tue Jul 15 2025
# SPDX-License-Identifier: MIT
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db import models


def create_match(db: Session, volunteer_id: int, need_id: int, match_details: str):
    """
    Creates a new match record between a volunteer and a need.
    """
    db_match = models.VolunteerNeedMatch(
        volunteer_id=volunteer_id, need_id=need_id, match_details=match_details, created_at=datetime.now(timezone.utc)
    )
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    return db_match


def get_matches_for_volunteer(db: Session, volunteer_id: int):
    """
    Retrieves all matches for a specific volunteer.
    """
    return (
        db.query(models.VolunteerNeedMatch)
        .filter(models.VolunteerNeedMatch.volunteer_id == volunteer_id)
        .all()
    )


def get_matches_for_need(db: Session, need_id: int):
    """
    Retrieves all matches for a specific need.
    """
    return db.query(models.VolunteerNeedMatch).filter(models.VolunteerNeedMatch.need_id == need_id).all()


def delete_matches_for_need(db: Session, need_id: int):
    """
    Deletes all match records associated with a specific need.
    """
    db.query(models.VolunteerNeedMatch).filter(models.VolunteerNeedMatch.need_id == need_id).delete()
    db.commit()
    return True


def delete_matches_for_volunteer(db: Session, volunteer_id: int):
    """
    Deletes all match records associated with a specific volunteer.
    """
    db.query(models.VolunteerNeedMatch).filter(
        models.VolunteerNeedMatch.volunteer_id == volunteer_id
    ).delete()
    db.commit()
    return True


def get_matched_need_ids_for_volunteer(db: Session, volunteer_id: int):
    """
    Returns a set of need IDs that the volunteer is already matched to.
    """
    matches = db.query(models.VolunteerNeedMatch.need_id).filter(
        models.VolunteerNeedMatch.volunteer_id == volunteer_id
    ).all()
    return {match.need_id for match in matches}


def get_matched_volunteer_ids_for_need(db: Session, need_id: int):
    """
    Returns a set of volunteer IDs that are already matched to the need.
    """
    matches = db.query(models.VolunteerNeedMatch.volunteer_id).filter(
        models.VolunteerNeedMatch.need_id == need_id
    ).all()
    return {match.volunteer_id for match in matches}


def delete_all_matches(db: Session):
    """
    Deletes all match records from the database.
    """
    db.query(models.VolunteerNeedMatch).delete()
    db.commit()
    return True
