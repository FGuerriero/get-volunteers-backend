# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from app.crud import crud_need, crud_volunteer, crud_match
from app.schemas import schemas
from tests.test_helpers import MockBackgroundTasks

@pytest.mark.asyncio
async def test_create_need_authenticated_and_check_matching(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    mock_matching_service_class = mocker.patch('app.services.matching_service.MatchingService')
    mock_matching_service_instance = mock_matching_service_class.return_value
    mock_matching_service_instance.reanalyze_all_matches.side_effect = MagicMock()
    mock_matching_service_instance.analyze_and_match.side_effect = MagicMock()

    mock_trigger_volunteer_matching = mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mock_trigger_volunteer_matching.side_effect = MagicMock()

    mock_trigger_need_matching = mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    crud_match.delete_all_matches(db_session)

    owner_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    matchable_volunteer_data = schemas.VolunteerCreate(
        name="Matchable Volunteer for Need",
        email="matchable_for_need@example.com",
        password="securepassword",
        skills="Project Management, Communication",
        volunteer_interests="Community Events"
    )
    
    mock_bg_tasks = MockBackgroundTasks()
    matchable_volunteer = await crud_volunteer.create_volunteer(db_session, matchable_volunteer_data, mock_bg_tasks)
    assert matchable_volunteer is not None
    
    def mock_trigger_need_side_effect(need_id: int):
        need_param = crud_need.get_need(db_session, need_id)
        all_volunteers_param = crud_volunteer.get_volunteers(db_session)

        if need_param and all_volunteers_param:
            crud_match.delete_matches_for_need(db_session, need_param.id)
            crud_match.create_match(
                db_session,
                matchable_volunteer.id,
                need_param.id,
                "Volunteer's project management skills and community interests align with this need."
            )
    mock_trigger_need_matching.side_effect = mock_trigger_need_side_effect

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

    matches = crud_match.get_matches_for_need(db_session, created_need_id)
    assert len(matches) >= 1
    assert any(m.volunteer_id == matchable_volunteer.id for m in matches)
    assert any("project management" in m.match_details.lower() for m in matches)


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

def test_read_needs_unauthenticated(client: TestClient):
    response = client.get("/api/v1/needs/")
    assert response.status_code == 401

def test_read_need_unauthenticated(client: TestClient):
    response = client.get("/api/v1/needs/1")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_read_needs_manager_access(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    
    # Make the authenticated volunteer a manager
    owner_volunteer.is_manager = 1
    db_session.commit()
    
    # Create another volunteer with needs
    other_volunteer_data = schemas.VolunteerCreate(name="Other Vol", email="other@example.com", password="pass")
    mock_bg_tasks = MockBackgroundTasks()
    
    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')
    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)
    
    other_volunteer = await crud_volunteer.create_volunteer(db_session, other_volunteer_data, mock_bg_tasks)
    
    # Create needs by different owners
    need1 = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Manager Need", description="By manager", num_volunteers_needed=1, 
        format="virtual", contact_name="M", contact_email="m@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    
    need2 = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Other Need", description="By other", num_volunteers_needed=1, 
        format="virtual", contact_name="O", contact_email="o@e.com"
    ), other_volunteer.id, mock_bg_tasks)
    
    # Manager should see all needs
    response = client.get("/api/v1/needs/", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(n["title"] == "Manager Need" for n in data)
    assert any(n["title"] == "Other Need" for n in data)

@pytest.mark.asyncio
async def test_read_needs_volunteer_own_only(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    
    # Ensure volunteer is NOT a manager
    owner_volunteer.is_manager = 0
    db_session.commit()
    
    # Create another volunteer with needs
    other_volunteer_data = schemas.VolunteerCreate(name="Other Vol", email="other2@example.com", password="pass")
    mock_bg_tasks = MockBackgroundTasks()
    
    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')
    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)
    
    other_volunteer = await crud_volunteer.create_volunteer(db_session, other_volunteer_data, mock_bg_tasks)
    
    # Create needs by different owners
    need1 = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Owner Need", description="By owner", num_volunteers_needed=1, 
        format="virtual", contact_name="O", contact_email="o@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    
    need2 = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Other Need", description="By other", num_volunteers_needed=1, 
        format="virtual", contact_name="X", contact_email="x@e.com"
    ), other_volunteer.id, mock_bg_tasks)
    
    # Volunteer should see only their own needs
    response = client.get("/api/v1/needs/", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Owner Need"
    assert data[0]["owner_id"] == owner_volunteer.id

@pytest.mark.asyncio
async def test_read_need_authenticated_owner(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    owner_volunteer.is_manager = 0
    db_session.commit()
    
    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)
    
    mock_bg_tasks = MockBackgroundTasks()
    need = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Owner Need", description="By owner", num_volunteers_needed=1,
        format="virtual", contact_name="O", contact_email="o@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    
    response = client.get(f"/api/v1/needs/{need.id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200
    assert response.json()["title"] == "Owner Need"

@pytest.mark.asyncio
async def test_update_need_authenticated_owner(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    owner_volunteer.is_manager = 0
    db_session.commit()
    
    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)
    
    mock_bg_tasks = MockBackgroundTasks()
    need = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Update Need", description="To update", num_volunteers_needed=1,
        format="virtual", contact_name="U", contact_email="u@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    
    update_data = schemas.NeedCreate(
        title="Updated Need", description="Updated", num_volunteers_needed=2,
        format="in-person", contact_name="Updated", contact_email="updated@e.com"
    )
    
    response = client.put(f"/api/v1/needs/{need.id}", json=update_data.model_dump(), headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Need"

@pytest.mark.asyncio
async def test_delete_need_authenticated_owner(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    owner_volunteer.is_manager = 0
    db_session.commit()
    
    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)
    
    mock_bg_tasks = MockBackgroundTasks()
    need = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Delete Need", description="To delete", num_volunteers_needed=1,
        format="virtual", contact_name="D", contact_email="d@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    
    response = client.delete(f"/api/v1/needs/{need.id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_delete_need_failure(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    owner_volunteer.is_manager = 0
    db_session.commit()
    
    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)
    mocker.patch('app.crud.crud_need.delete_need', return_value=False)
    
    mock_bg_tasks = MockBackgroundTasks()
    need = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Fail Delete", description="Fail", num_volunteers_needed=1,
        format="virtual", contact_name="F", contact_email="f@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    
    response = client.delete(f"/api/v1/needs/{need.id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 404
    assert "Need not found or an unexpected error occurred during deletion" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_need_authenticated_not_owner(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    mock_bg_tasks = MockBackgroundTasks()

    need_by_owner = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Owner's Need", description="Owned by test user", num_volunteers_needed=1, format="virtual", contact_name="Owner", contact_email="owner@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    assert need_by_owner is not None

    not_owner_email = "not_owner_needs@example.com"
    not_owner_password = "notownerpassword"
    not_owner_data = schemas.VolunteerCreate(name="Not Owner", email=not_owner_email, password=not_owner_password)
    
    not_owner_volunteer = await crud_volunteer.create_volunteer(db_session, not_owner_data, mock_bg_tasks)
    assert not_owner_volunteer is not None

    not_owner_token_response = client.post("/api/v1/login", data={"username": not_owner_email, "password": not_owner_password})
    assert not_owner_token_response.status_code == 200
    not_owner_token = not_owner_token_response.json()["access_token"]

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=not_owner_volunteer)

    update_data = schemas.NeedCreate(
        title="Attempted Update", 
        description="Should not update", 
        num_volunteers_needed=1, 
        format="in-person", 
        contact_name="Fail", 
        contact_email="fail@e.com"
    )

    response = client.put(
        f"/api/v1/needs/{need_by_owner.id}",
        json=update_data.model_dump(),
        headers={"Authorization": f"Bearer {not_owner_token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"