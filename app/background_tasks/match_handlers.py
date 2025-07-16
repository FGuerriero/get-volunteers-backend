"""
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Tue Jul 15 2025
# SPDX-License-Identifier: MIT
"""

from sqlalchemy.orm import Session

from app.crud import crud_need, crud_volunteer
from app.db.database import get_db
from app.services.matching_service import MatchingService


async def trigger_need_matching(need_id: int):
    """
    Triggers matching analysis for a specific need against all volunteers.
    This function is designed to run as a background task.
    """
    db: Session = next(get_db())
    try:
        need = crud_need.get_need(db, need_id)
        if need:
            matching_service = MatchingService(db)
            all_volunteers = crud_volunteer.get_volunteers(db)
            await matching_service.analyze_and_match(need, all_volunteers)
        else:
            print(f"Background Task Warning: Need with ID {need_id} not found for matching.")
    finally:
        db.close()


async def trigger_volunteer_matching(volunteer_id: int):
    """
    Triggers matching analysis for a specific volunteer against all needs.
    This function is designed to run as a background task.
    """
    db: Session = next(get_db())
    try:
        volunteer = crud_volunteer.get_volunteer(db, volunteer_id)
        if volunteer:
            matching_service = MatchingService(db)
            all_needs = crud_need.get_needs(db)
            await matching_service.analyze_volunteer_against_all_needs(volunteer, all_needs)
        else:
            print(f"Background Task Warning: Volunteer with ID {volunteer_id} not found for matching.")
    finally:
        db.close()
