# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from unittest.mock import MagicMock, AsyncMock

from app.background_tasks import match_handlers
from app.crud import crud_need, crud_volunteer, crud_match
from app.services.matching_service import MatchingService
from app.schemas import schemas
from app.db import models
from app.utils.security import get_password_hash 

class MockBackgroundTasks:
    def __init__(self):
        self.tasks = []
        self.db_session = None

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))

    async def run_tasks(self):
        for func, args, kwargs in self.tasks:
            if func.__name__ == 'trigger_need_matching':
                need_id = args[0]
                need_obj = crud_need.get_need(self.db_session, need_id)
                all_volunteers = crud_volunteer.get_volunteers(self.db_session)
                if need_obj:
                    await func(self.db_session, need_obj, all_volunteers)
                else:
                    print(f"Warning: Mocked trigger_need_matching received ID {need_id} but need not found.")
            else:
                await func(*args, **kwargs)
        self.tasks.clear()


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
async def test_create_need(db_session: Session, mocker):
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_need_create@example.com")

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mock_trigger_need_matching = mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')
    
    mocker.patch('app.crud.crud_volunteer.get_volunteers', return_value=[owner_volunteer])

    need_data = schemas.NeedCreate(
        title="Food Delivery",
        description="Deliver food to elderly",
        required_tasks="Driving, Lifting",
        required_skills="Driving license",
        num_volunteers_needed=5,
        format="in-person",
        location_details="Downtown area",
        contact_name="Charity Org",
        contact_email="contact@charity.org",
        contact_phone="111-222-3333",
    )
    need = await crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id, background_tasks=mock_bg_tasks)

    assert need.id is not None
    assert need.title == "Food Delivery"
    assert need.num_volunteers_needed == 5
    assert need.format == "in-person"
    assert need.owner_id == owner_volunteer.id

    await mock_bg_tasks.run_tasks()

    mock_trigger_need_matching.assert_called_once_with(need.id)

@pytest.mark.asyncio
async def test_create_need_integrity_error(mocker, db_session: Session):
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_need_integrity@example.com")

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mock_trigger_need_matching = mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')
    mocker.patch('app.crud.crud_volunteer.get_volunteers', return_value=[owner_volunteer])

    need_data = schemas.NeedCreate(
        title="Duplicate Need",
        description="This need will cause an integrity error",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Test Contact",
        contact_email="test@example.com",
    )

    mocker.patch.object(db_session, 'add', side_effect=IntegrityError("test", {}, "test"))
    mocker.patch.object(db_session, 'rollback')

    result = await crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id, background_tasks=mock_bg_tasks)

    assert result is None
    db_session.rollback.assert_called_once()
    mock_trigger_need_matching.assert_not_called()

@pytest.mark.asyncio
async def test_get_need(db_session: Session, mocker):
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_need_get@example.com")

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')
    mocker.patch('app.crud.crud_volunteer.get_volunteers', return_value=[owner_volunteer])

    need_data = schemas.NeedCreate(
        title="Online Tutoring",
        description="Help students with math",
        num_volunteers_needed=2,
        format="virtual",
        contact_name="School",
        contact_email="school@example.com",
    )
    created_need = await crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id, background_tasks=mock_bg_tasks)

    fetched_need = crud_need.get_need(db_session, created_need.id)
    assert fetched_need is not None
    assert fetched_need.title == "Online Tutoring"
    assert fetched_need.owner_id == owner_volunteer.id

    not_found_need = crud_need.get_need(db_session, 999)
    assert not_found_need is None

@pytest.mark.asyncio
async def test_get_needs(db_session: Session, mocker):
    owner_volunteer1 = create_dummy_volunteer(db_session, email="owner_need_get_1@example.com")
    owner_volunteer2 = create_dummy_volunteer(db_session, email="owner_need_get_2@example.com")
    owner_volunteer3 = create_dummy_volunteer(db_session, email="owner_need_get_3@example.com")

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')
    mocker.patch('app.crud.crud_volunteer.get_volunteers', return_value=[owner_volunteer1, owner_volunteer2, owner_volunteer3])

    await crud_need.create_need(db_session, schemas.NeedCreate(title="N1", description="desc", num_volunteers_needed=1, format="virtual", contact_name="C1", contact_email="c1@e.com"), owner_id=owner_volunteer1.id, background_tasks=mock_bg_tasks)
    await crud_need.create_need(db_session, schemas.NeedCreate(title="N2", description="desc", num_volunteers_needed=1, format="virtual", contact_name="C2", contact_email="c2@e.com"), owner_id=owner_volunteer2.id, background_tasks=mock_bg_tasks)
    await crud_need.create_need(db_session, schemas.NeedCreate(title="N3", description="desc", num_volunteers_needed=1, format="virtual", contact_name="C3", contact_email="c3@e.com"), owner_id=owner_volunteer3.id, background_tasks=mock_bg_tasks)

    needs = crud_need.get_needs(db_session, skip=0, limit=2)
    assert len(needs) == 2
    assert needs[0].title == "N1"
    assert needs[1].title == "N2"

    all_needs = crud_need.get_needs(db_session)
    assert len(all_needs) == 3

@pytest.mark.asyncio
async def test_update_need(db_session: Session, mocker):
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_need_update@example.com")

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mock_trigger_need_matching = mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')
    mocker.patch('app.crud.crud_volunteer.get_volunteers', return_value=[owner_volunteer])

    need_data = schemas.NeedCreate(
        title="Old Title",
        description="Old Description",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Org",
        contact_email="org@example.com",
    )
    created_need = await crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id, background_tasks=mock_bg_tasks)

    await mock_bg_tasks.run_tasks()
    mock_trigger_need_matching.reset_mock()
    update_data = schemas.NeedCreate(
        title="New Title",
        description="Updated Description",
        num_volunteers_needed=2,
        format="in-person",
        contact_name="Org",
        contact_email="org@example.com",
    )
    updated_need = await crud_need.update_need(db_session, created_need.id, update_data, owner_id=owner_volunteer.id, background_tasks=mock_bg_tasks)

    assert updated_need is not None
    assert updated_need.title == "New Title"
    assert updated_need.description == "Updated Description"
    assert updated_need.num_volunteers_needed == 2
    assert updated_need.format == "in-person"
    assert updated_need.owner_id == owner_volunteer.id

    await mock_bg_tasks.run_tasks()
    mock_trigger_need_matching.assert_called_once_with(updated_need.id)

    other_volunteer = create_dummy_volunteer(db_session, email="other_owner_need_update@example.com")
    non_existent_update_by_other_volunteer = await crud_need.update_need(db_session, created_need.id, update_data, owner_id=other_volunteer.id, background_tasks=mock_bg_tasks)
    assert non_existent_update_by_other_volunteer is None

    non_existent_update = await crud_need.update_need(db_session, 999, update_data, owner_id=owner_volunteer.id, background_tasks=mock_bg_tasks)
    assert non_existent_update is None

@pytest.mark.asyncio
async def test_delete_need(db_session: Session, mocker):
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_need_delete@example.com")

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')
    mocker.patch('app.crud.crud_volunteer.get_volunteers', return_value=[owner_volunteer])

    need_data = schemas.NeedCreate(
        title="Delete This",
        description="Delete this need",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Temp",
        contact_email="temp@example.com",
    )
    created_need = await crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id, background_tasks=mock_bg_tasks)

    success = crud_need.delete_need(db_session, created_need.id, owner_id=owner_volunteer.id)
    assert success is True
    assert crud_need.get_need(db_session, created_need.id) is None

    other_volunteer = create_dummy_volunteer(db_session, email="other_owner_need_delete@example.com")
    fail_by_other_volunteer = crud_need.delete_need(db_session, created_need.id, owner_id=other_volunteer.id)
    assert fail_by_other_volunteer is False

    fail = crud_need.delete_need(db_session, 999, owner_id=owner_volunteer.id)
    assert fail is False

@pytest.mark.asyncio
async def test_trigger_need_matching_need_not_found(db_session: Session, mocker, capsys):
    """
    Tests the warning message in app/background_tasks/match_handlers.py when need is not found.
    Covers app/background_tasks/match_handlers.py line 27.
    """
    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mocker.patch('app.crud.crud_need.get_need', return_value=None)
    mocker.patch('app.crud.crud_volunteer.get_volunteers', return_value=[])

    mock_analyze_and_match = mocker.patch('app.services.matching_service.MatchingService.analyze_and_match')

    await match_handlers.trigger_need_matching(99999)

    captured = capsys.readouterr()
    assert "Background Task Warning: Need with ID 99999 not found for matching." in captured.out
    mock_analyze_and_match.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_and_match_no_volunteers(db_session: Session, mocker, capsys):
    """
    Tests analyze_and_match when no volunteers are available.
    Covers app/services/matching_service.py lines 118-119.
    """
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_for_no_vol_test@example.com")
    need_data = schemas.NeedCreate(title="Need with No Vols", description="Desc", num_volunteers_needed=1, format="virtual", contact_name="C", contact_email="c@e.com")
    need = await crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id, background_tasks=MagicMock())

    mocker.patch('app.crud.crud_volunteer.get_volunteers', return_value=[])

    mock_call_gemini_api = mocker.patch('app.services.matching_service.MatchingService._call_gemini_api')
    
    matching_service = MatchingService(db_session)
    await matching_service.analyze_and_match(need, [])

    captured = capsys.readouterr()
    assert f"No volunteers available to match for Need ID {need.id}" in captured.out
    mock_call_gemini_api.assert_not_called()
    assert not crud_match.get_matches_for_need(db_session, need.id)

@pytest.mark.asyncio
async def test_analyze_and_match_gemini_suggests_non_existent_volunteer(db_session: Session, mocker, capsys):
    """
    Tests analyze_and_match when Gemini suggests a non-existent volunteer ID.
    Covers app/services/matching_service.py lines 165-168.
    """
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_for_non_existent_vol_test@example.com")
    need_data = schemas.NeedCreate(title="Need for Non-Existent Vol", description="Desc", num_volunteers_needed=1, format="virtual", contact_name="C", contact_email="c@e.com")
    need = await crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id, background_tasks=MagicMock())

    existing_volunteer = create_dummy_volunteer(db_session, email="existing_vol_for_test@example.com")

    mock_gemini_response = [
        {"volunteer_id": existing_volunteer.id, "match_details": "Good match"},
        {"volunteer_id": 99999, "match_details": "Non-existent volunteer"}
    ]
    mocker.patch('app.services.matching_service.MatchingService._call_gemini_api', new_callable=AsyncMock, return_value=mock_gemini_response)
    
    original_get_volunteer = crud_volunteer.get_volunteer
    def mock_get_volunteer_side_effect(db, vol_id):
        if vol_id == 99999:
            return None
        return original_get_volunteer(db, vol_id)
    mocker.patch('app.crud.crud_volunteer.get_volunteer', side_effect=mock_get_volunteer_side_effect)

    from app.services.matching_service import MatchingService
    matching_service = MatchingService(db_session)
    await matching_service.analyze_and_match(need, [existing_volunteer])

    captured = capsys.readouterr()
    normalized_output = ' '.join(captured.out.split()).strip()
    expected_message = f"Warning: Gemini suggested non-existent volunteer ID 99999 for Need ID {need.id}"
    assert expected_message in normalized_output
    
    matches = crud_match.get_matches_for_need(db_session, need.id)
    assert len(matches) == 1
    assert matches[0].volunteer_id == existing_volunteer.id

@pytest.mark.asyncio
async def test_analyze_and_match_gemini_invalid_data_format(db_session: Session, mocker, capsys):
    """
    Tests analyze_and_match when Gemini returns invalid match data format.
    Covers app/services/matching_service.py lines 169-172 (implicitly via invalid format check).
    """
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_for_invalid_format_test@example.com")
    need_data = schemas.NeedCreate(title="Need for Invalid Format", description="Desc", num_volunteers_needed=1, format="virtual", contact_name="C", contact_email="c@e.com")
    need = await crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id, background_tasks=MagicMock())

    existing_volunteer = create_dummy_volunteer(db_session, email="existing_vol_for_invalid_format@example.com")

    mock_gemini_response = [
        {"volunteer_id": existing_volunteer.id, "match_details": "Valid match"},
        {"volunteer_id": "not_an_int", "match_details": "Invalid ID type"},
        {"match_details": "Missing ID"}
    ]
    mocker.patch('app.services.matching_service.MatchingService._call_gemini_api', new_callable=AsyncMock, return_value=mock_gemini_response)
    
    matching_service = MatchingService(db_session)
    await matching_service.analyze_and_match(need, [existing_volunteer])

    captured = capsys.readouterr()
    assert f"Warning: Gemini returned invalid match data format for Need ID {need.id}:" in captured.out
    
    matches = crud_match.get_matches_for_need(db_session, need.id)
    assert len(matches) == 1
    assert matches[0].volunteer_id == existing_volunteer.id

@pytest.mark.asyncio
async def test_update_need_manager_access(db_session: Session, mocker):
    """Test update_need with manager access"""
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_manager_update@example.com")
    manager_volunteer = create_dummy_volunteer(db_session, email="manager_update@example.com")
    manager_volunteer.is_manager = 1
    db_session.commit()

    mock_bg_tasks = MockBackgroundTasks()
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    need_data = schemas.NeedCreate(
        title="Manager Update Need",
        description="Manager can update",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Manager",
        contact_email="manager@example.com",
    )
    created_need = await crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id, background_tasks=mock_bg_tasks)

    update_data = schemas.NeedCreate(
        title="Updated by Manager",
        description="Manager updated this",
        num_volunteers_needed=2,
        format="in-person",
        contact_name="Manager",
        contact_email="manager@example.com",
    )
    updated_need = await crud_need.update_need(db_session, created_need.id, update_data, owner_id=manager_volunteer.id, background_tasks=mock_bg_tasks, is_manager=True)

    assert updated_need is not None
    assert updated_need.title == "Updated by Manager"

@pytest.mark.asyncio
async def test_delete_need_manager_access(db_session: Session, mocker):
    """Test delete_need with manager access"""
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_manager_delete@example.com")
    manager_volunteer = create_dummy_volunteer(db_session, email="manager_delete@example.com")
    manager_volunteer.is_manager = 1
    db_session.commit()

    mock_bg_tasks = MockBackgroundTasks()
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    need_data = schemas.NeedCreate(
        title="Manager Delete Need",
        description="Manager can delete",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Manager",
        contact_email="manager@example.com",
    )
    created_need = await crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id, background_tasks=mock_bg_tasks)

    success = crud_need.delete_need(db_session, created_need.id, owner_id=manager_volunteer.id, is_manager=True)
    assert success is True
    assert crud_need.get_need(db_session, created_need.id) is None

@pytest.mark.asyncio
async def test_analyze_and_match_gemini_no_valid_matches(db_session: Session, mocker, capsys):
    """
    Tests analyze_and_match when Gemini returns no valid matches or None.
    Covers app/services/matching_service.py lines 173-174 (implicitly via no matches created).
    """
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_for_no_valid_matches_test@example.com")
    need_data = schemas.NeedCreate(title="Need for No Valid Matches", description="Desc", num_volunteers_needed=1, format="virtual", contact_name="C", contact_email="c@e.com")
    need = await crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id, background_tasks=MagicMock())

    existing_volunteer = create_dummy_volunteer(db_session, email="existing_vol_for_no_valid_matches@example.com")

    mocker.patch('app.services.matching_service.MatchingService._call_gemini_api', new_callable=AsyncMock, return_value=[])
    
    matching_service = MatchingService(db_session)
    await matching_service.analyze_and_match(need, [existing_volunteer])

    captured = capsys.readouterr()
    assert f"Gemini did not return valid matches for Need ID {need.id}" in captured.out
    
    matches = crud_match.get_matches_for_need(db_session, need.id)
    assert len(matches) == 0
