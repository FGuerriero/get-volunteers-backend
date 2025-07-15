'''
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Tue Jul 15 2025
# SPDX-License-Identifier: MIT
'''

from sqlalchemy.orm import Session

from app.crud import crud_need, crud_volunteer
from app.db import models
from app.services.matching_service import MatchingService


async def trigger_need_matching(db: Session, need: models.Need):
    """
    Triggers matching analysis for a specific need.
    """
    matching_service = MatchingService(db)
    all_volunteers = crud_volunteer.get_volunteers(db)
    await matching_service.analyze_and_match(need, all_volunteers)

async def trigger_volunteer_matching(db: Session, volunteer: models.Volunteer):
    """
    Triggers matching analysis for a specific volunteer against all needs.
    """
    matching_service = MatchingService(db)
    all_needs = crud_need.get_needs(db)
    await matching_service.analyze_volunteer_against_all_needs(volunteer, all_needs)

