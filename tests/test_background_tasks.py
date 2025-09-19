# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.background_tasks import match_handlers
from app.crud import crud_need, crud_volunteer
from app.schemas import schemas
from tests.test_helpers import MockBackgroundTasks

@pytest.mark.asyncio
async def test_trigger_need_matching_need_not_found(db_session: Session, mocker, capsys):
    """Test trigger_need_matching when need is not found"""
    mocker.patch('app.background_tasks.match_handlers.get_db', return_value=iter([db_session]))
    mocker.patch('app.crud.crud_need.get_need', return_value=None)
    
    await match_handlers.trigger_need_matching(99999)
    
    captured = capsys.readouterr()
    assert "Background Task Warning: Need with ID 99999 not found for matching." in captured.out

@pytest.mark.asyncio
async def test_trigger_volunteer_matching_volunteer_not_found(db_session: Session, mocker, capsys):
    """Test trigger_volunteer_matching when volunteer is not found"""
    mocker.patch('app.background_tasks.match_handlers.get_db', return_value=iter([db_session]))
    mocker.patch('app.crud.crud_volunteer.get_volunteer', return_value=None)
    
    await match_handlers.trigger_volunteer_matching(99999)
    
    captured = capsys.readouterr()
    assert "Background Task Warning: Volunteer with ID 99999 not found for matching." in captured.out

@pytest.mark.asyncio
async def test_matching_service_no_volunteers(db_session: Session, mocker, capsys):
    """Test analyze_need_against_all_volunteers when no volunteers available"""
    from app.services.matching_service import MatchingService
    from app.db.models import Need
    
    need = Need(id=1, title="Test", description="Test", num_volunteers_needed=1)
    service = MatchingService(db_session)
    
    await service.analyze_need_against_all_volunteers(need, [])
    
    captured = capsys.readouterr()
    assert "No volunteers available to match for Need ID 1" in captured.out

@pytest.mark.asyncio
async def test_matching_service_no_needs(db_session: Session, mocker, capsys):
    """Test analyze_volunteer_against_all_needs when no needs available"""
    from app.services.matching_service import MatchingService
    from app.db.models import Volunteer
    
    volunteer = Volunteer(id=1, name="Test", email="test@test.com")
    service = MatchingService(db_session)
    
    await service.analyze_volunteer_against_all_needs(volunteer, [])
    
    captured = capsys.readouterr()
    assert "No needs available to match for Volunteer ID 1" in captured.out