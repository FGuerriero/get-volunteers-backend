# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, AsyncMock

from app.background_tasks import match_handlers
from app.crud import crud_volunteer, crud_need, crud_match
from app.db import models
from app.services.matching_service import MatchingService
from app.schemas import schemas
from app.utils.security import get_password_hash

class MockBackgroundTasks:
    def __init__(self):
        self.tasks = []
        self.db_session = None

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))

    async def run_tasks(self):
        for func, args, kwargs in self.tasks:
            if func.__name__ == 'trigger_volunteer_matching':
                volunteer_id = args[0]
                volunteer_obj = crud_volunteer.get_volunteer(self.db_session, volunteer_id)
                if volunteer_obj:
                    await func(self.db_session, volunteer_obj)
                else:
                    print(f"Warning: Mocked trigger_volunteer_matching received ID {volunteer_id} but volunteer not found.")
            else:
                await func(*args, **kwargs)
        self.tasks.clear()

# Helper to create a dummy volunteer for ownership
def create_dummy_volunteer(db_session: Session, email: str = "dummy_owner@example.com"):
    volunteer = models.Volunteer(
        name="Dummy Owner",
        email=email,
        password=get_password_hash("password"),
        is_active=1
    )
    db_session.add(volunteer)
    db_session.commit()
    db_session.refresh(volunteer)
    return volunteer

@pytest.mark.asyncio
async def test_create_volunteer(db_session: Session, mocker):
    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mock_trigger_volunteer_matching = mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.crud.crud_need.get_needs', return_value=[])

    volunteer_data = schemas.VolunteerCreate(
        name="Test Volunteer",
        email="test@example.com",
        password="securepassword",
        phone="123-456-7890",
        about_me="Passionate about helping",
        skills="Coding, Teaching",
        volunteer_interests="Education, Environment",
        location="New York",
        availability="Weekends",
    )
    volunteer = await crud_volunteer.create_volunteer(db_session, volunteer_data, background_tasks=mock_bg_tasks)

    assert volunteer.id is not None
    assert volunteer.name == "Test Volunteer"
    assert volunteer.email == "test@example.com"
    assert volunteer.phone == "123-456-7890"
    assert volunteer.password is not None
    assert volunteer.is_active == 1

    await mock_bg_tasks.run_tasks()
    mock_trigger_volunteer_matching.assert_called_once_with(volunteer.id)

    duplicate_volunteer_data = schemas.VolunteerCreate(
        name="Duplicate Volunteer",
        email="test@example.com",
        password="anotherpassword"
    )
    mock_trigger_volunteer_matching.reset_mock()
    duplicate_volunteer = await crud_volunteer.create_volunteer(db_session, duplicate_volunteer_data, background_tasks=mock_bg_tasks)
    assert duplicate_volunteer is None
    mock_trigger_volunteer_matching.assert_not_called()


@pytest.mark.asyncio
async def test_get_volunteer(db_session: Session, mocker):
    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.crud.crud_need.get_needs', return_value=[])

    volunteer_data = schemas.VolunteerCreate(name="Get Volunteer", email="get@example.com", password="password123")
    created_volunteer = await crud_volunteer.create_volunteer(db_session, volunteer_data, background_tasks=mock_bg_tasks)

    fetched_volunteer = crud_volunteer.get_volunteer(db_session, created_volunteer.id)
    assert fetched_volunteer is not None
    assert fetched_volunteer.email == "get@example.com"

    not_found_volunteer = crud_volunteer.get_volunteer(db_session, 999)
    assert not_found_volunteer is None

@pytest.mark.asyncio
async def test_get_volunteer_by_email(db_session: Session, mocker):
    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.crud.crud_need.get_needs', return_value=[])

    volunteer_data = schemas.VolunteerCreate(name="Email Volunteer", email="email@example.com", password="password123")
    await crud_volunteer.create_volunteer(db_session, volunteer_data, background_tasks=mock_bg_tasks)

    fetched_volunteer = crud_volunteer.get_volunteer_by_email(db_session, "email@example.com")
    assert fetched_volunteer is not None
    assert fetched_volunteer.name == "Email Volunteer"

    not_found_volunteer = crud_volunteer.get_volunteer_by_email(db_session, "nonexistent@example.com")
    assert not_found_volunteer is None

@pytest.mark.asyncio
async def test_get_volunteers(db_session: Session, mocker):
    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.crud.crud_need.get_needs', return_value=[])

    await crud_volunteer.create_volunteer(db_session, schemas.VolunteerCreate(name="V1", email="v1@example.com", password="p1"), background_tasks=mock_bg_tasks)
    await crud_volunteer.create_volunteer(db_session, schemas.VolunteerCreate(name="V2", email="v2@example.com", password="p2"), background_tasks=mock_bg_tasks)
    await crud_volunteer.create_volunteer(db_session, schemas.VolunteerCreate(name="V3", email="v3@example.com", password="p3"), background_tasks=mock_bg_tasks)

    volunteers = crud_volunteer.get_volunteers(db_session, skip=0, limit=2)
    assert len(volunteers) == 2
    assert volunteers[0].name == "V1"
    assert volunteers[1].name == "V2"

    all_volunteers = crud_volunteer.get_volunteers(db_session)
    assert len(all_volunteers) == 3

@pytest.mark.asyncio
async def test_update_volunteer(db_session: Session, mocker):
    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mock_trigger_volunteer_matching = mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.crud.crud_need.get_needs', return_value=[])

    volunteer_data = schemas.VolunteerCreate(name="Old Name", email="old@example.com", password="oldpassword")
    created_volunteer = await crud_volunteer.create_volunteer(db_session, volunteer_data, background_tasks=mock_bg_tasks)

    await mock_bg_tasks.run_tasks()
    mock_trigger_volunteer_matching.reset_mock()

    update_data = schemas.VolunteerCreate(name="New Name", phone="987-654-3210", email="old@example.com", password="newpassword")
    updated_volunteer = await crud_volunteer.update_volunteer(db_session, created_volunteer.id, update_data, background_tasks=mock_bg_tasks)

    assert updated_volunteer is not None
    assert updated_volunteer.name == "New Name"
    assert updated_volunteer.phone == "987-654-3210"
    assert get_password_hash("newpassword") != get_password_hash("oldpassword")

    await mock_bg_tasks.run_tasks()
    mock_trigger_volunteer_matching.assert_called_once_with(updated_volunteer.id)

    non_existent_update = await crud_volunteer.update_volunteer(db_session, 999, update_data, background_tasks=mock_bg_tasks)
    assert non_existent_update is None
    mock_trigger_volunteer_matching.assert_called_once()

@pytest.mark.asyncio
async def test_delete_volunteer(db_session: Session, mocker):
    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mocker.patch('app.crud.crud_need.get_needs', return_value=[])

    volunteer_data = schemas.VolunteerCreate(name="Delete Me", email="delete@example.com", password="deletepassword")
    created_volunteer = await crud_volunteer.create_volunteer(db_session, volunteer_data, background_tasks=mock_bg_tasks)

    mock_delete_matches_for_volunteer = mocker.patch('app.crud.crud_match.delete_matches_for_volunteer')

    success = crud_volunteer.delete_volunteer(db_session, created_volunteer.id)
    assert success is True
    assert crud_volunteer.get_volunteer(db_session, created_volunteer.id) is None
    mock_delete_matches_for_volunteer.assert_called_once_with(db_session, created_volunteer.id)


    fail = crud_volunteer.delete_volunteer(db_session, 999)
    assert fail is False

@pytest.mark.asyncio
async def test_trigger_volunteer_matching_volunteer_not_found(db_session: Session, mocker, capsys):
    """
    Tests the warning message in app/background_tasks/match_handlers.py when volunteer is not found.
    Covers app/background_tasks/match_handlers.py line 45.
    """
    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mocker.patch('app.crud.crud_volunteer.get_volunteer', return_value=None)
    mocker.patch('app.crud.crud_need.get_needs', return_value=[])

    mock_analyze_volunteer_against_all_needs = mocker.patch('app.services.matching_service.MatchingService.analyze_volunteer_against_all_needs')

    await match_handlers.trigger_volunteer_matching(99999)

    captured = capsys.readouterr()
    assert "Background Task Warning: Volunteer with ID 99999 not found for matching." in captured.out
    mock_analyze_volunteer_against_all_needs.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_volunteer_against_all_needs_no_needs(db_session: Session, mocker, capsys):
    """
    Tests analyze_volunteer_against_all_needs when no needs are available.
    Covers app/services/matching_service.py lines 186-187.
    """
    volunteer_data = schemas.VolunteerCreate(name="Volunteer with No Needs", email="no_needs_vol@example.com", password="pass")
    volunteer = await crud_volunteer.create_volunteer(db_session, volunteer_data, background_tasks=MagicMock())

    mocker.patch('app.crud.crud_need.get_needs', return_value=[])

    mock_call_gemini_api = mocker.patch('app.services.matching_service.MatchingService._call_gemini_api')
    
    matching_service = MatchingService(db_session)
    await matching_service.analyze_volunteer_against_all_needs(volunteer, [])

    captured = capsys.readouterr()
    assert f"No needs available to match for Volunteer ID {volunteer.id}" in captured.out
    mock_call_gemini_api.assert_not_called()
    assert not crud_match.get_matches_for_volunteer(db_session, volunteer.id)

@pytest.mark.asyncio
async def test_analyze_volunteer_against_all_needs_gemini_suggests_non_existent_need(db_session: Session, mocker, capsys):
    """
    Tests analyze_volunteer_against_all_needs when Gemini suggests a non-existent need ID.
    Covers app/services/matching_service.py lines 226-229.
    """
    volunteer_data = schemas.VolunteerCreate(name="Volunteer for Non-Existent Need", email="non_existent_need_vol@example.com", password="pass")
    volunteer = await crud_volunteer.create_volunteer(db_session, volunteer_data, background_tasks=MagicMock())

    owner_volunteer = create_dummy_volunteer(db_session, email="owner_for_dummy_need@example.com")
    existing_need = await crud_need.create_need(db_session, schemas.NeedCreate(title="Existing Need", description="Desc", num_volunteers_needed=1, format="virtual", contact_name="C", contact_email="c@e.com"), owner_id=owner_volunteer.id, background_tasks=MagicMock()) # Await this call

    mock_gemini_response = [
        {"need_id": existing_need.id, "match_details": "Good match"},
        {"need_id": 99999, "match_details": "Non-existent need"}
    ]
    mocker.patch('app.services.matching_service.MatchingService._call_gemini_api', new_callable=AsyncMock, return_value=mock_gemini_response)
    
    original_get_need = crud_need.get_need
    def mock_get_need_side_effect(db, need_id):
        if need_id == 99999:
            return None
        return original_get_need(db, need_id)
    mocker.patch('app.crud.crud_need.get_need', side_effect=mock_get_need_side_effect)

    from app.services.matching_service import MatchingService
    matching_service = MatchingService(db_session)
    await matching_service.analyze_volunteer_against_all_needs(volunteer, [existing_need])

    captured = capsys.readouterr()
    normalized_output = ' '.join(captured.out.split()).strip()
    assert f"Warning: Gemini suggested non-existent need ID 99999 for Volunteer ID {volunteer.id}" in normalized_output
    
    matches = crud_match.get_matches_for_volunteer(db_session, volunteer.id)
    assert len(matches) == 1
    assert matches[0].need_id == existing_need.id

@pytest.mark.asyncio
async def test_analyze_volunteer_against_all_needs_gemini_invalid_data_format(db_session: Session, mocker, capsys):
    """
    Tests analyze_volunteer_against_all_needs when Gemini returns invalid match data format.
    Covers app/services/matching_service.py lines 230-233.
    """
    volunteer_data = schemas.VolunteerCreate(name="Volunteer for Invalid Format", email="invalid_format_vol@example.com", password="pass")
    volunteer = await crud_volunteer.create_volunteer(db_session, volunteer_data, background_tasks=MagicMock())

    owner_volunteer = create_dummy_volunteer(db_session, email="owner_for_invalid_format_need@example.com")
    existing_need = await crud_need.create_need(db_session, schemas.NeedCreate(title="Existing Need", description="Desc", num_volunteers_needed=1, format="virtual", contact_name="C", contact_email="c@e.com"), owner_id=owner_volunteer.id, background_tasks=MagicMock()) # Await this call

    mock_gemini_response = [
        {"need_id": existing_need.id, "match_details": "Valid match"},
        {"need_id": "not_an_int", "match_details": "Invalid ID type"},
        {"match_details": "Missing ID"}
    ]
    mocker.patch('app.services.matching_service.MatchingService._call_gemini_api', new_callable=AsyncMock, return_value=mock_gemini_response)
    
    from app.services.matching_service import MatchingService
    matching_service = MatchingService(db_session)
    await matching_service.analyze_volunteer_against_all_needs(volunteer, [existing_need])

    captured = capsys.readouterr()
    normalized_output = ' '.join(captured.out.split()).strip()
    assert f"Warning: Gemini returned invalid match data format for Volunteer ID {volunteer.id}:" in normalized_output
    
    matches = crud_match.get_matches_for_volunteer(db_session, volunteer.id)
    assert len(matches) == 1
    assert matches[0].need_id == existing_need.id

@pytest.mark.asyncio
async def test_analyze_volunteer_against_all_needs_gemini_no_valid_matches(db_session: Session, mocker, capsys):
    """
    Tests analyze_volunteer_against_all_needs when Gemini returns no valid matches or None.
    Covers app/services/matching_service.py lines 234-235.
    """
    volunteer_data = schemas.VolunteerCreate(name="Volunteer for No Valid Matches", email="no_valid_matches_vol@example.com", password="pass")
    volunteer = await crud_volunteer.create_volunteer(db_session, volunteer_data, background_tasks=MagicMock())

    owner_volunteer = create_dummy_volunteer(db_session, email="owner_for_no_valid_matches_need@example.com")
    existing_need = await crud_need.create_need(db_session, schemas.NeedCreate(title="Existing Need", description="Desc", num_volunteers_needed=1, format="virtual", contact_name="C", contact_email="c@e.com"), owner_id=owner_volunteer.id, background_tasks=MagicMock())

    mocker.patch('app.services.matching_service.MatchingService._call_gemini_api', new_callable=AsyncMock, return_value=[])
    
    matching_service = MatchingService(db_session)
    await matching_service.analyze_volunteer_against_all_needs(volunteer, [existing_need])

    captured = capsys.readouterr()
    assert f"Gemini did not return valid matches for Volunteer ID {volunteer.id}" in captured.out
    
    matches = crud_match.get_matches_for_volunteer(db_session, volunteer.id)
    assert len(matches) == 0

@pytest.mark.asyncio
async def test_matching_service_call_gemini_api_unexpected_response_structure(db_session: Session, mocker, capsys):
    """
    Tests _call_gemini_api when Gemini returns an unexpected content structure.
    Covers app/services/matching_service.py lines 104-108.
    """
    mock_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.candidates = []

    mocker.patch('google.generativeai.GenerativeModel', return_value=mock_model_instance)
    
    mock_model_instance.generate_content_async = AsyncMock(return_value=mock_response)

    from app.services.matching_service import MatchingService
    matching_service = MatchingService(db_session)
    
    schema = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"id": {"type": "integer"}}}}
    result = await matching_service._call_gemini_api("test prompt", schema)

    assert result is None
    captured = capsys.readouterr()
    assert "Gemini API did not return expected content structure:" in captured.out

@pytest.mark.asyncio
async def test_matching_service_call_gemini_api_exception(db_session: Session, mocker, capsys):
    """
    Tests _call_gemini_api when an exception occurs during the Gemini API call.
    Covers app/services/matching_service.py lines 106-108.
    """
    mock_model_instance = MagicMock()

    mocker.patch('google.generativeai.GenerativeModel', return_value=mock_model_instance)
    
    mock_model_instance.generate_content_async = AsyncMock(side_effect=Exception("Simulated Gemini API error"))

    matching_service = MatchingService(db_session)
    
    schema = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"id": {"type": "integer"}}}}
    result = await matching_service._call_gemini_api("test prompt", schema)

    assert result is None
    captured = capsys.readouterr()
    assert "Error calling Gemini API: Simulated Gemini API error" in captured.out

