# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.crud import crud_volunteer, crud_need, crud_match
from app.schemas import schemas
from fastapi import BackgroundTasks

class MockBackgroundTasks:
    def __init__(self):
        self.tasks = []
        self.db_session = None

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))

    async def run_tasks(self):
        for func, args, kwargs in self.tasks:
            await func(*args, **kwargs)
        self.tasks.clear()

@pytest.mark.asyncio
async def test_register_volunteer_and_check_matching(client: TestClient, db_session: Session, mocker):
    mock_background_tasks_for_api = MockBackgroundTasks()
    mock_background_tasks_for_api.db_session = db_session

    client.app.dependency_overrides[BackgroundTasks] = lambda: mock_background_tasks_for_api

    mock_trigger_volunteer_matching = mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')

    try:
        crud_match.delete_all_matches(db_session)
        
        existing_dummy_owner = crud_volunteer.get_volunteer_by_email(db_session, "dummy_owner@example.com")
        if existing_dummy_owner:
            crud_volunteer.delete_volunteer(db_session, existing_dummy_owner.id)
        
        existing_test_volunteer = crud_volunteer.get_volunteer_by_email(db_session, "matchable@example.com")
        if existing_test_volunteer:
            crud_volunteer.delete_volunteer(db_session, existing_test_volunteer.id)

        test_need_data = schemas.NeedCreate(
            title="Test Need for Volunteer Matching",
            description="A need that requires someone with good communication skills and interest in community.",
            required_tasks="Talking, Listening",
            required_skills="Communication, Empathy",
            num_volunteers_needed=1,
            format="in-person",
            contact_name="Need Contact",
            contact_email="need@example.com"
        )
        dummy_owner_data = schemas.VolunteerCreate(
            name="Dummy Owner", email="dummy_owner@example.com", password="dummy_password"
        )
        dummy_owner_mock_bg = MockBackgroundTasks()
        dummy_owner_mock_bg.db_session = db_session
        dummy_owner = await crud_volunteer.create_volunteer(db_session, dummy_owner_data, dummy_owner_mock_bg)
        await dummy_owner_mock_bg.run_tasks()

        test_need_mock_bg = MockBackgroundTasks()
        test_need_mock_bg.db_session = db_session
        test_need = await crud_need.create_need(db_session, test_need_data, dummy_owner.id, test_need_mock_bg)
        await test_need_mock_bg.run_tasks()
        
        def mock_trigger_volunteer_side_effect(volunteer_id: int):
            crud_match.delete_matches_for_volunteer(db_session, volunteer_id)
            crud_match.create_match(
                db_session,
                volunteer_id,
                test_need.id,
                "Volunteer's communication skills and interests align with the test need."
            )
        
        mock_trigger_volunteer_matching.side_effect = mock_trigger_volunteer_side_effect

        volunteer_data = {
            "name": "Matchable Volunteer",
            "email": "matchable@example.com",
            "password": "testpassword",
            "phone": "123-456-7890",
            "about_me": "Loves helping people and has great communication skills.",
            "skills": "Communication, Active Listening, Problem Solving",
            "volunteer_interests": "Community Support, Socializing",
            "location": "Anywhere",
            "availability": "Flexible"
        }
        response = client.post("/api/v1/register", json=volunteer_data) 
        assert response.status_code == 201
        created_volunteer = response.json()
        created_volunteer_id = created_volunteer["id"]

        await mock_background_tasks_for_api.run_tasks()

        matches = crud_match.get_matches_for_volunteer(db_session, created_volunteer_id)
        assert len(matches) >= 1
        assert any(m.need_id == test_need.id for m in matches)
        assert any("communication" in m.match_details.lower() for m in matches)
    finally:
        client.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_update_volunteer_and_check_matching(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    mock_background_tasks_for_api = MockBackgroundTasks()
    mock_background_tasks_for_api.db_session = db_session

    client.app.dependency_overrides[BackgroundTasks] = lambda: mock_background_tasks_for_api

    mock_trigger_volunteer_matching = mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')

    try:
        crud_match.delete_all_matches(db_session)

        owner_volunteer_email, owner_token = authenticated_volunteer_and_token
        owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
        owner_volunteer_id = owner_volunteer.id
        assert owner_volunteer is not None

        unmatching_need_data = schemas.NeedCreate(
            title="Unmatching Need",
            description="Requires very specific skills like Quantum Physics and Advanced Rocketry.",
            required_tasks="Complex calculations",
            required_skills="Quantum Physics, Rocket Science",
            num_volunteers_needed=1,
            format="virtual",
            contact_name="Sci Contact",
            contact_email="sci@example.com"
        )
        unmatching_need_mock_bg = MockBackgroundTasks()
        unmatching_need_mock_bg.db_session = db_session
        unmatching_need = await crud_need.create_need(db_session, unmatching_need_data, owner_volunteer_id, unmatching_need_mock_bg)
        await unmatching_need_mock_bg.run_tasks()
        
        matching_need_data = schemas.NeedCreate(
            title="Matching Need",
            description="Requires strong organizational skills and event planning.",
            required_tasks="Organize, Plan",
            required_skills="Organization, Event Planning",
            num_volunteers_needed=1,
            format="in-person",
            contact_name="Event Contact",
            contact_email="event@example.com"
        )
        matching_need_mock_bg = MockBackgroundTasks()
        matching_need_mock_bg.db_session = db_session
        matching_need = await crud_need.create_need(db_session, matching_need_data, owner_volunteer_id, matching_need_mock_bg)
        await matching_need_mock_bg.run_tasks()

        initial_matches = crud_match.get_matches_for_volunteer(db_session, owner_volunteer_id)
        assert not any(m.need_id == matching_need.id for m in initial_matches)

        mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)

        def mock_trigger_volunteer_update_side_effect(volunteer_id: int):
            crud_match.delete_matches_for_volunteer(db_session, volunteer_id)
            crud_match.create_match(
                db_session,
                volunteer_id,
                matching_need.id,
                "Volunteer's updated skills in organization and event planning match the need."
            )

        mock_trigger_volunteer_matching.side_effect = mock_trigger_volunteer_update_side_effect

        update_data = {
            "name": "Updated Owner Volunteer",
            "email": owner_volunteer_email,
            "phone": "555-555-5555",
            "password": "newsecurepassword",
            "skills": "Organization, Event Planning, Communication"
        }
        response = client.put(
            f"/api/v1/volunteers/{owner_volunteer_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200

        await mock_background_tasks_for_api.run_tasks()

        updated_matches = crud_match.get_matches_for_volunteer(db_session, owner_volunteer_id)
        assert any(m.need_id == matching_need.id for m in updated_matches)
        assert any("organization" in m.match_details.lower() or "event planning" in m.match_details.lower() for m in updated_matches)

        assert not any(m.need_id == unmatching_need.id for m in updated_matches)
    finally:
        client.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_create_volunteer_authenticated_via_register(client: TestClient, db_session: Session, mocker):
    mock_background_tasks_for_api = MockBackgroundTasks()
    mock_background_tasks_for_api.db_session = db_session

    client.app.dependency_overrides[BackgroundTasks] = lambda: mock_background_tasks_for_api

    try:
        volunteer_data = {
            "name": "Test Register Volunteer",
            "email": "test_register@example.com",
            "password": "registerpassword",
            "phone": "111-222-3333",
            "about_me": "Test user for registration",
            "skills": "Testing",
            "volunteer_interests": "Testing",
            "location": "Test City",
            "availability": "Anytime"
        }
        
        response = client.post("/api/v1/register", json=volunteer_data) 

        assert response.status_code == 201
        assert "id" in response.json()
        assert response.json()["email"] == "test_register@example.com"

        await mock_background_tasks_for_api.run_tasks()
    finally:
        client.app.dependency_overrides = {}


def test_create_volunteer_unauthenticated(client: TestClient):
    response = client.post(
        "/api/v1/volunteers/",
        json={
            "name": "Unauth Volunteer",
            "email": "unauth_volunteer@example.com",
            "password": "unauthpassword"
        },
    )
    assert response.status_code == 405


@pytest.mark.asyncio
async def test_read_volunteers_public(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker): 
    _, _ = authenticated_volunteer_and_token
    
    volunteer1_data = schemas.VolunteerCreate(name="Public Vol One", email="public_one@example.com", password="pass1")
    volunteer2_data = schemas.VolunteerCreate(name="Public Vol Two", email="public_two@example.com", password="pass2")
    
    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    
    await crud_volunteer.create_volunteer(db_session, volunteer1_data, mock_bg_tasks)
    await crud_volunteer.create_volunteer(db_session, volunteer2_data, mock_bg_tasks)
    await mock_bg_tasks.run_tasks() 

    response = client.get("/api/v1/volunteers/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3 
    assert any(v["email"] == "public_one@example.com" for v in data)
    assert any(v["email"] == "public_two@example.com" for v in data)

@pytest.mark.asyncio
async def test_read_volunteer_public(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    _, _ = authenticated_volunteer_and_token

    volunteer_data = schemas.VolunteerCreate(name="Single Public Vol", email="single_public@example.com", password="pass3")
    
    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    
    created_volunteer = await crud_volunteer.create_volunteer(db_session, volunteer_data, mock_bg_tasks)
    await mock_bg_tasks.run_tasks()
    
    volunteer_id = created_volunteer.id

    response = client.get(f"/api/v1/volunteers/{volunteer_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Single Public Vol"
    assert data["email"] == "single_public@example.com"
    assert data["id"] == volunteer_id

    response = client.get("/api/v1/volunteers/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Volunteer not found"

@pytest.mark.asyncio
async def test_update_volunteer_authenticated_owner_basic(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    mock_background_tasks_for_api = MockBackgroundTasks()
    mock_background_tasks_for_api.db_session = db_session

    client.app.dependency_overrides[BackgroundTasks] = lambda: mock_background_tasks_for_api

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')

    try:
        owner_volunteer_email, owner_token = authenticated_volunteer_and_token
        owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
        owner_volunteer_id = owner_volunteer.id
        assert owner_volunteer is not None

        mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)

        update_data = {
            "name": "Updated Owner Volunteer Basic",
            "email": owner_volunteer_email,
            "phone": "555-555-5555",
            "password": "newsecurepassword"
        }
        response = client.put(
            f"/api/v1/volunteers/{owner_volunteer_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Owner Volunteer Basic"
        assert data["phone"] == "555-555-5555"
        assert data["id"] == owner_volunteer_id

        login_response = client.post(
            "/api/v1/login",
            data={"username": owner_volunteer_email, "password": "newsecurepassword"}
        )
        assert login_response.status_code == 200
        
        await mock_background_tasks_for_api.run_tasks()
    finally:
        client.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_update_volunteer_authenticated_not_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    mock_background_tasks_for_api = MockBackgroundTasks()
    mock_background_tasks_for_api.db_session = db_session

    client.app.dependency_overrides[BackgroundTasks] = lambda: mock_background_tasks_for_api

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')

    try:
        owner_volunteer_email, _ = authenticated_volunteer_and_token
        
        owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
        owner_volunteer_id = owner_volunteer.id
        assert owner_volunteer is not None
        
        not_owner_email = "not_owner_volunteer@example.com"
        not_owner_password = "notownerpassword"
        not_owner_create_data = schemas.VolunteerCreate(
            name="Not Owner Volunteer",
            email=not_owner_email,
            password=not_owner_password
        )
        mock_bg_tasks = MockBackgroundTasks()
        mock_bg_tasks.db_session = db_session
        not_owner_volunteer = await crud_volunteer.create_volunteer(db_session, not_owner_create_data, mock_bg_tasks)
        await mock_bg_tasks.run_tasks()
        
        not_owner_token_response = client.post(
            "/api/v1/login",
            data={"username": not_owner_email, "password": not_owner_password}
        )
        assert not_owner_token_response.status_code == 200
        not_owner_token = not_owner_token_response.json()["access_token"]

        mocker.patch('app.dependencies.get_current_active_volunteer', return_value=not_owner_volunteer)

        update_data = {
            "name": "Attempted Update",
            "email": owner_volunteer_email,
            "phone": "123-123-1234",
            "password": "some_password_to_pass_validation"
        }
        response = client.put(f"/api/v1/volunteers/{owner_volunteer_id}", json=update_data, headers={"Authorization": f"Bearer {not_owner_token}"})
        assert response.status_code == 403 
        assert "You can only update your own volunteer profile." in response.json()["detail"]
    finally:
        client.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_update_volunteer_unauthenticated(client: TestClient, db_session: Session, authenticated_volunteer_and_token):
    owner_volunteer_email, _ = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    owner_volunteer_id = owner_volunteer.id
    assert owner_volunteer is not None

    update_data = {"name": "Should Not Update", "email": owner_volunteer_email, "password": "any_password"}
    response = client.put(f"/api/v1/volunteers/{owner_volunteer_id}", json=update_data)
    assert response.status_code == 401 

@pytest.mark.asyncio
async def test_delete_volunteer_authenticated_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    owner_volunteer_email, owner_token = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    owner_volunteer_id = owner_volunteer.id
    assert owner_volunteer is not None

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)

    response = client.delete(f"/api/v1/volunteers/{owner_volunteer_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 204

    response = client.get(f"/api/v1/volunteers/{owner_volunteer_id}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_volunteer_authenticated_not_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    mock_background_tasks_for_api = MockBackgroundTasks()
    mock_background_tasks_for_api.db_session = db_session

    client.app.dependency_overrides[BackgroundTasks] = lambda: mock_background_tasks_for_api

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')

    try:
        owner_volunteer_email, _ = authenticated_volunteer_and_token
        
        owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
        owner_volunteer_id = owner_volunteer.id
        assert owner_volunteer is not None
        
        not_owner_email = "not_owner_delete_volunteer@example.com"
        not_owner_password = "notownerdeletepassword"
        not_owner_create_data = schemas.VolunteerCreate(
            name="Not Owner Delete Volunteer",
            email=not_owner_email,
            password=not_owner_password
        )
        
        mock_bg_tasks = MockBackgroundTasks()
        mock_bg_tasks.db_session = db_session
        
        not_owner_volunteer = await crud_volunteer.create_volunteer(db_session, not_owner_create_data, mock_bg_tasks)

        await mock_bg_tasks.run_tasks()
        
        not_owner_token_response = client.post(
            "/api/v1/login",
            data={"username": not_owner_email, "password": not_owner_password}
        )
        assert not_owner_token_response.status_code == 200
        not_owner_token = not_owner_token_response.json()["access_token"]

        mocker.patch('app.dependencies.get_current_active_volunteer', return_value=not_owner_volunteer)

        response = client.delete(f"/api/v1/volunteers/{owner_volunteer_id}", headers={"Authorization": f"Bearer {not_owner_token}"})
        assert response.status_code == 403 
        assert "You can only delete your own volunteer profile." in response.json()["detail"]
    finally:
        client.app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_delete_volunteer_unauthenticated(client: TestClient, db_session: Session, authenticated_volunteer_and_token):
    owner_volunteer_email, _ = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    owner_volunteer_id = owner_volunteer.id
    assert owner_volunteer is not None

    response = client.delete(f"/api/v1/volunteers/{owner_volunteer_id}")
    assert response.status_code == 401