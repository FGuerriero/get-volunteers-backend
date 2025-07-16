# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from app.crud import crud_need, crud_volunteer, crud_match
from app.schemas import schemas
from app.db.models import Volunteer, Need
from fastapi import BackgroundTasks
from app.app import app # Corrected: Import the FastAPI app instance from app.app

# Helper to manage background tasks in tests
class MockBackgroundTasks:
    def __init__(self):
        self.tasks = []
        self.db_session = None # To hold the db_session for synchronous crud_match calls

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))

    async def run_tasks(self):
        for func, args, kwargs in self.tasks:
            # For match_handlers, they get their own session via get_db()
            # For crud_match.delete_matches_for_need, it expects a db session
            if func.__module__.startswith('app.crud.crud_match'):
                # crud_match functions are synchronous and expect a db session as the first arg
                func(self.db_session, *args, **kwargs)
            else:
                # For async match_handlers, they will get their own session
                await func(*args, **kwargs)
        self.tasks.clear() # Clear tasks after running


# client and db_session fixtures are imported from conftest.py
# authenticated_volunteer_and_token fixture is imported from conftest.py (returns email, token)

@pytest.mark.asyncio
async def test_create_need_authenticated_and_check_matching(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    # Set up mock for BackgroundTasks
    mock_background_tasks_for_api = MockBackgroundTasks()
    mock_background_tasks_for_api.db_session = db_session
    client.app.dependency_overrides[BackgroundTasks] = lambda: mock_background_tasks_for_api

    # --- NEW MOCKING STRATEGY: Patch where MatchingService is imported and used ---
    # Patch analyze_and_match in crud_need, as crud_need.create_need calls it
    mock_analyze_and_match_in_crud_need = mocker.patch('app.crud.crud_need.MatchingService.analyze_and_match')
    # Patch reanalyze_all_matches in crud_volunteer, as crud_volunteer.create_volunteer calls it
    mock_reanalyze_all_matches_in_crud_volunteer = mocker.patch('app.crud.crud_volunteer.MatchingService.reanalyze_all_matches')

    try:
        # Clear all existing matches to ensure a clean test state
        crud_match.delete_all_matches(db_session)

        owner_email, owner_token = authenticated_volunteer_and_token
        owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
        assert owner_volunteer is not None

        # Create a volunteer that the new need can match against
        matchable_volunteer_data = schemas.VolunteerCreate(
            name="Matchable Volunteer for Need",
            email="matchable_for_need@example.com",
            password="securepassword",
            skills="Project Management, Communication",
            volunteer_interests="Community Events"
        )
        # Define the side effect for mock_reanalyze_all_matches_in_crud_volunteer during setup
        def mock_reanalyze_side_effect_setup(*args, **kwargs):
            pass # We don't need any matches created during this setup phase
        mock_reanalyze_all_matches_in_crud_volunteer.side_effect = mock_reanalyze_side_effect_setup

        matchable_volunteer = await crud_volunteer.create_volunteer(db_session, matchable_volunteer_data)
        assert matchable_volunteer is not None
        # Reset the mock after setup to prepare for the main test logic
        mock_reanalyze_all_matches_in_crud_volunteer.reset_mock()
        mock_reanalyze_all_matches_in_crud_volunteer.side_effect = None # Clear side effect

        # Define the side effect for the mocked analyze_and_match for need creation
        def mock_analyze_need_side_effect(need_param, all_volunteers_param):
            crud_match.delete_matches_for_need(db_session, need_param.id)
            crud_match.create_match(
                db_session,
                matchable_volunteer.id, # Use the matchable volunteer created above
                need_param.id,
                "Volunteer's project management skills and community interests align with this need."
            )
        mock_analyze_and_match_in_crud_need.side_effect = mock_analyze_need_side_effect

        need_data = schemas.NeedCreate(
            title="Community Project Lead",
            description="Lead a community project, requires good organizational skills.",
            required_tasks="Organize, Plan, Communicate",
            required_skills="Project Management, Leadership, Communication",
            num_volunteers_needed=1,
            format="in-person",
            contact_name="Org Contact",
            contact_email="org@example.com",
            contact_phone="987-654-3210"
        )

        response = client.post(
            "/api/v1/needs/",
            json=need_data.model_dump(),
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 201
        created_need = response.json()
        created_need_id = created_need["id"]
        assert created_need["owner_id"] == owner_volunteer.id

        # Manually run the background tasks that were added during need creation
        await mock_background_tasks_for_api.run_tasks()

        # Assert that matches were created for the new need
        matches = crud_match.get_matches_for_need(db_session, created_need_id)
        assert len(matches) >= 1
        assert any(m.volunteer_id == matchable_volunteer.id for m in matches)
        assert any("project management" in m.match_details.lower() for m in matches)

    finally:
        client.app.dependency_overrides = {}


def test_create_need_unauthenticated(client: TestClient):
    need_data = schemas.NeedCreate(
        title="Unauthorized Need",
        description="This should fail.",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Anon",
        contact_email="anon@example.com"
    )
    response = client.post("/api/v1/needs/", json=need_data.model_dump())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_read_needs_public(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    # Mock MatchingService methods during setup
    mocker.patch('app.crud.crud_need.MatchingService.analyze_and_match')
    mocker.patch('app.crud.crud_volunteer.MatchingService.reanalyze_all_matches')

    need1_data = schemas.NeedCreate(title="Public Need One", description="Desc 1", num_volunteers_needed=1, format="in-person", contact_name="C1", contact_email="c1@e.com")
    need2_data = schemas.NeedCreate(title="Public Need Two", description="Desc 2", num_volunteers_needed=2, format="virtual", contact_name="C2", contact_email="c2@e.com")

    await crud_need.create_need(db_session, need1_data, owner_volunteer.id)
    await crud_need.create_need(db_session, need2_data, owner_volunteer.id)

    response = client.get("/api/v1/needs/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(n["title"] == "Public Need One" for n in data)
    assert any(n["title"] == "Public Need Two" for n in data)

@pytest.mark.asyncio
async def test_read_need_public(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    # Mock MatchingService methods during setup
    mocker.patch('app.crud.crud_need.MatchingService.analyze_and_match')
    mocker.patch('app.crud.crud_volunteer.MatchingService.reanalyze_all_matches')

    need_data = schemas.NeedCreate(title="Single Public Need", description="Single desc", num_volunteers_needed=1, format="in-person", contact_name="C3", contact_email="c3@e.com")
    created_need = await crud_need.create_need(db_session, need_data, owner_volunteer.id)
    
    response = client.get(f"/api/v1/needs/{created_need.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Single Public Need"
    assert data["id"] == created_need.id

    response = client.get("/api/v1/needs/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Need not found"

@pytest.mark.asyncio
async def test_update_need_authenticated_owner_and_check_matching(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    # Set up mock for BackgroundTasks
    mock_background_tasks_for_api = MockBackgroundTasks()
    mock_background_tasks_for_api.db_session = db_session
    client.app.dependency_overrides[BackgroundTasks] = lambda: mock_background_tasks_for_api

    # --- NEW MOCKING STRATEGY ---
    # Patch analyze_and_match in crud_need
    mock_analyze_and_match_in_crud_need = mocker.patch('app.crud.crud_need.MatchingService.analyze_and_match')
    # Patch reanalyze_all_matches in crud_volunteer
    mock_reanalyze_all_matches_in_crud_volunteer = mocker.patch('app.crud.crud_volunteer.MatchingService.reanalyze_all_matches')

    try:
        # Clear all existing matches to ensure a clean test state
        crud_match.delete_all_matches(db_session)

        owner_email, owner_token = authenticated_volunteer_and_token
        owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
        assert owner_volunteer is not None

        # Create an initial need
        initial_need_data = schemas.NeedCreate(
            title="Initial Need",
            description="Initial description.",
            required_tasks="Old tasks",
            required_skills="Old skills",
            num_volunteers_needed=1,
            format="in-person",
            contact_name="Initial Contact",
            contact_email="initial@example.com"
        )
        # Define side effect for analyze_and_match during initial need creation
        def initial_analyze_side_effect(*args, **kwargs):
            # This mock ensures that initial need creation doesn't create matches
            pass
        mock_analyze_and_match_in_crud_need.side_effect = initial_analyze_side_effect

        initial_need = await crud_need.create_need(db_session, initial_need_data, owner_volunteer.id)
        assert initial_need is not None
        # Reset the mock's side_effect for the update phase
        mock_analyze_and_match_in_crud_need.reset_mock()
        mock_analyze_and_match_in_crud_need.side_effect = None # Clear side effect


        # Create a volunteer that will match the UPDATED need
        updated_matchable_volunteer_data = schemas.VolunteerCreate(
            name="Updated Matchable Volunteer",
            email="updated_matchable@example.com",
            password="securepassword",
            skills="Event Planning, Coordination",
            volunteer_interests="Community Events, Organizing"
        )
        # Define side effect for reanalyze_all_matches during volunteer creation
        def reanalyze_side_effect_for_setup(*args, **kwargs):
            pass # No matches needed during this setup
        mock_reanalyze_all_matches_in_crud_volunteer.side_effect = reanalyze_side_effect_for_setup

        updated_matchable_volunteer = await crud_volunteer.create_volunteer(db_session, updated_matchable_volunteer_data)
        assert updated_matchable_volunteer is not None
        # Reset the mock's side_effect for reanalyze_all_matches after setup
        mock_reanalyze_all_matches_in_crud_volunteer.reset_mock()
        mock_reanalyze_all_matches_in_crud_volunteer.side_effect = None # Clear side effect


        # Ensure no matches initially for the updated_matchable_volunteer with initial_need
        initial_matches = crud_match.get_matches_for_need(db_session, initial_need.id)
        assert not any(m.volunteer_id == updated_matchable_volunteer.id for m in initial_matches)

        # Define the side effect for the mocked analyze_and_match for the update
        def mock_analyze_need_update_side_effect(need_param, all_volunteers_param):
            crud_match.delete_matches_for_need(db_session, need_param.id)
            crud_match.create_match(
                db_session,
                updated_matchable_volunteer.id,
                need_param.id,
                "Volunteer's event planning and coordination skills match the updated need."
            )
        mock_analyze_and_match_in_crud_need.side_effect = mock_analyze_need_update_side_effect


        update_data = schemas.NeedCreate(
            title="Updated Community Event",
            description="Organize a large community event.",
            required_tasks="Event Logistics, Volunteer Coordination",
            required_skills="Event Planning, Coordination, Problem Solving",
            num_volunteers_needed=2,
            format="in-person",
            contact_name="New Contact",
            contact_email="new@example.com",
            contact_phone="111-222-3333"
        )

        response = client.put(
            f"/api/v1/needs/{initial_need.id}",
            json=update_data.model_dump(),
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        updated_need = response.json()
        assert updated_need["title"] == "Updated Community Event"
        assert updated_need["num_volunteers_needed"] == 2

        # Manually run the background tasks that were added during update
        await mock_background_tasks_for_api.run_tasks()

        # Assert that matches were updated for the need
        matches = crud_match.get_matches_for_need(db_session, initial_need.id)
        assert any(m.volunteer_id == updated_matchable_volunteer.id for m in matches)
        assert any("event planning" in m.match_details.lower() for m in matches)

    finally:
        client.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_update_need_authenticated_not_owner(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    # Mock MatchingService methods during setup
    mocker.patch('app.crud.crud_need.MatchingService.analyze_and_match')
    mock_reanalyze_all_matches_in_crud_volunteer = mocker.patch('app.crud.crud_volunteer.MatchingService.reanalyze_all_matches')
    def reanalyze_side_effect_for_setup(*args, **kwargs):
        pass
    mock_reanalyze_all_matches_in_crud_volunteer.side_effect = reanalyze_side_effect_for_setup


    # Create a need by the owner
    need_by_owner = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Owner's Need", description="Owned by test user", num_volunteers_needed=1, format="virtual", contact_name="Owner", contact_email="owner@e.com"
    ), owner_volunteer.id)
    assert need_by_owner is not None

    # Create another volunteer (not the owner) and get their token
    not_owner_email = "not_owner_needs@example.com"
    not_owner_password = "notownerpassword"
    not_owner_data = schemas.VolunteerCreate(name="Not Owner", email=not_owner_email, password=not_owner_password)
    not_owner_volunteer = await crud_volunteer.create_volunteer(db_session, not_owner_data)
    assert not_owner_volunteer is not None

    not_owner_token_response = client.post("/api/v1/login", data={"username": not_owner_email, "password": not_owner_password})
    assert not_owner_token_response.status_code == 200
    not_owner_token = not_owner_token_response.json()["access_token"]

    # Mock get_current_active_volunteer to return the non-owner
    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=not_owner_volunteer)

    update_data = schemas.NeedCreate(
        title="Attempted Update", description="Should not update", num_volunteers_needed=1, format="in-person", contact_name="Fail", contact_email="fail@e.com"
    )

    response = client.put(
        f"/api/v1/needs/{need_by_owner.id}",
        json=update_data.model_dump(),
        headers={"Authorization": f"Bearer {not_owner_token}"}
    )
    assert response.status_code == 404 # Should be 404 because the query filters by owner_id


@pytest.mark.asyncio # Added async marker
async def test_update_need_unauthenticated(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    # Mock MatchingService methods during setup
    mocker.patch('app.crud.crud_need.MatchingService.analyze_and_match')
    mocker.patch('app.crud.crud_volunteer.MatchingService.reanalyze_all_matches')

    need_by_owner = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Unauth Update Need", description="Owned by test user", num_volunteers_needed=1, format="virtual", contact_name="Owner", contact_email="owner2@e.com"
    ), owner_volunteer.id)
    assert need_by_owner is not None

    update_data = schemas.NeedCreate(
        title="Attempted Unauth Update", description="Should not update", num_volunteers_needed=1, format="in-person", contact_name="Fail", contact_email="fail2@e.com"
    )

    response = client.put(f"/api/v1/needs/{need_by_owner.id}", json=update_data.model_dump())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_need_authenticated_owner(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    # Mock MatchingService methods during setup
    mocker.patch('app.crud.crud_need.MatchingService.analyze_and_match')
    mocker.patch('app.crud.crud_volunteer.MatchingService.reanalyze_all_matches')

    # Create a need by the owner
    need_to_delete = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Need to Delete", description="Will be deleted", num_volunteers_needed=1, format="virtual", contact_name="Del", contact_email="del@e.com"
    ), owner_volunteer.id)
    assert need_to_delete is not None

    # Create a dummy match for the need to ensure deletion works
    crud_match.create_match(db_session, owner_volunteer.id, need_to_delete.id, "Dummy match for deletion test")
    assert len(crud_match.get_matches_for_need(db_session, need_to_delete.id)) == 1

    response = client.delete(
        f"/api/v1/needs/{need_to_delete.id}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 204

    # Verify need is deleted
    assert crud_need.get_need(db_session, need_to_delete.id) is None
    # Verify matches for the need are deleted
    assert len(crud_match.get_matches_for_need(db_session, need_to_delete.id)) == 0


@pytest.mark.asyncio
async def test_delete_need_authenticated_not_owner(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    # Mock MatchingService methods during setup
    mocker.patch('app.crud.crud_need.MatchingService.analyze_and_match')
    mock_reanalyze_all_matches_in_crud_volunteer = mocker.patch('app.crud.crud_volunteer.MatchingService.reanalyze_all_matches')
    def reanalyze_side_effect_for_setup(*args, **kwargs):
        pass
    mock_reanalyze_all_matches_in_crud_volunteer.side_effect = reanalyze_side_effect_for_setup

    # Create a need by the owner
    need_by_owner = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Owner's Need for Delete", description="Owned by test user", num_volunteers_needed=1, format="virtual", contact_name="Owner", contact_email="owner_del@e.com"
    ), owner_volunteer.id)
    assert need_by_owner is not None

    # Create another volunteer (not the owner) and get their token
    not_owner_email = "not_owner_delete_needs@example.com"
    not_owner_password = "notownerdeletepassword"
    not_owner_data = schemas.VolunteerCreate(name="Not Owner Del", email=not_owner_email, password=not_owner_password)
    not_owner_volunteer = await crud_volunteer.create_volunteer(db_session, not_owner_data)
    assert not_owner_volunteer is not None

    not_owner_token_response = client.post("/api/v1/login", data={"username": not_owner_email, "password": not_owner_password})
    assert not_owner_token_response.status_code == 200
    not_owner_token = not_owner_token_response.json()["access_token"]

    # Mock get_current_active_volunteer to return the non-owner
    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=not_owner_volunteer)

    response = client.delete(
        f"/api/v1/needs/{need_by_owner.id}",
        headers={"Authorization": f"Bearer {not_owner_token}"}
    )
    assert response.status_code == 404 # Should be 404 because the query filters by owner_id


@pytest.mark.asyncio # Added async marker
async def test_delete_need_unauthenticated(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    # Mock MatchingService methods during setup
    mocker.patch('app.crud.crud_need.MatchingService.analyze_and_match')
    mocker.patch('app.crud.crud_volunteer.MatchingService.reanalyze_all_matches')

    need_to_delete = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Unauth Delete Need", description="Will be deleted", num_volunteers_needed=1, format="virtual", contact_name="Unauth", contact_email="unauth@e.com"
    ), owner_volunteer.id)
    assert need_to_delete is not None

    response = client.delete(f"/api/v1/needs/{need_to_delete.id}")
    assert response.status_code == 401
