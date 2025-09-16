# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.crud import crud_volunteer, crud_need, crud_match
from app.schemas import schemas
from tests.test_helpers import MockBackgroundTasks

@pytest.mark.asyncio
async def test_register_volunteer_and_check_matching(client: TestClient, db_session: Session, mocker):
    mock_trigger_volunteer_matching = mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')

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
    dummy_owner = await crud_volunteer.create_volunteer(db_session, dummy_owner_data, dummy_owner_mock_bg)

    test_need_mock_bg = MockBackgroundTasks()
    test_need = await crud_need.create_need(db_session, test_need_data, dummy_owner.id, test_need_mock_bg)
    
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

    matches = crud_match.get_matches_for_volunteer(db_session, created_volunteer_id)
    assert len(matches) >= 1
    assert any(m.need_id == test_need.id for m in matches)
    assert any("communication" in m.match_details.lower() for m in matches)


@pytest.mark.asyncio
async def test_read_volunteers_manager_only(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker): 
    owner_email, owner_token = authenticated_volunteer_and_token
    
    # Make the authenticated volunteer a manager
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    owner_volunteer.is_manager = 1
    db_session.commit()
    
    volunteer1_data = schemas.VolunteerCreate(name="Vol One", email="vol_one@example.com", password="pass1")
    volunteer2_data = schemas.VolunteerCreate(name="Vol Two", email="vol_two@example.com", password="pass2")
    
    mock_bg_tasks = MockBackgroundTasks()

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.dependencies.get_current_manager', return_value=owner_volunteer)
    
    await crud_volunteer.create_volunteer(db_session, volunteer1_data, mock_bg_tasks)
    await crud_volunteer.create_volunteer(db_session, volunteer2_data, mock_bg_tasks)

    response = client.get("/api/v1/volunteers", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3 
    assert any(v["email"] == "vol_one@example.com" for v in data)
    assert any(v["email"] == "vol_two@example.com" for v in data)

@pytest.mark.asyncio
async def test_read_volunteers_non_manager_blocked(client: TestClient, db_session: Session, authenticated_volunteer_and_token):
    owner_email, owner_token = authenticated_volunteer_and_token
    
    # Ensure the authenticated volunteer is NOT a manager
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    owner_volunteer.is_manager = 0
    db_session.commit()

    response = client.get("/api/v1/volunteers", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Manager access required"

@pytest.mark.asyncio
async def test_read_volunteer_manager_only(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, owner_token = authenticated_volunteer_and_token
    
    # Make the authenticated volunteer a manager
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    owner_volunteer.is_manager = 1
    db_session.commit()

    volunteer_data = schemas.VolunteerCreate(name="Single Vol", email="single_vol@example.com", password="pass3")
    
    mock_bg_tasks = MockBackgroundTasks()

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.dependencies.get_current_manager', return_value=owner_volunteer)
    
    created_volunteer = await crud_volunteer.create_volunteer(db_session, volunteer_data, mock_bg_tasks)
    
    volunteer_id = created_volunteer.id

    response = client.get(f"/api/v1/volunteers/{volunteer_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Single Vol"
    assert data["email"] == "single_vol@example.com"
    assert data["id"] == volunteer_id

    response = client.get("/api/v1/volunteers/99999", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Volunteer not found"

@pytest.mark.asyncio
async def test_update_volunteer_authenticated_owner_basic(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')

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

@pytest.mark.asyncio
async def test_update_volunteer_not_found(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    owner_volunteer_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    
    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)
    mocker.patch('app.crud.crud_volunteer.update_volunteer', return_value=None)
    
    update_data = {
        "name": "Updated", "email": owner_volunteer_email, "password": "pass"
    }
    response = client.put(f"/api/v1/volunteers/{owner_volunteer.id}", json=update_data, headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 404
    assert "Volunteer not found or an unexpected error occurred during update" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_volunteer_not_found(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    owner_volunteer_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    
    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)
    mocker.patch('app.crud.crud_volunteer.delete_volunteer', return_value=False)
    
    response = client.delete(f"/api/v1/volunteers/{owner_volunteer.id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 404
    assert "Volunteer not found or an unexpected error occurred during deletion" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_volunteer_authenticated_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    owner_volunteer_email, owner_token = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    owner_volunteer_id = owner_volunteer.id
    assert owner_volunteer is not None
    
    # Create a separate manager to test GET after deletion
    manager_email = "manager_for_delete_test@example.com"
    manager_password = "managerpassword"
    manager_create_data = schemas.VolunteerCreate(
        name="Manager For Delete Test",
        email=manager_email,
        password=manager_password
    )
    
    mock_bg_tasks = MockBackgroundTasks()
    
    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    
    manager_volunteer = await crud_volunteer.create_volunteer(db_session, manager_create_data, mock_bg_tasks)
    
    # Make the manager a manager
    manager_volunteer.is_manager = 1
    db_session.commit()
    
    # Get manager token
    manager_token_response = client.post(
        "/api/v1/login",
        data={"username": manager_email, "password": manager_password}
    )
    assert manager_token_response.status_code == 200
    manager_token = manager_token_response.json()["access_token"]

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)

    response = client.delete(f"/api/v1/volunteers/{owner_volunteer_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 204

    # Use manager token to verify deletion
    mocker.patch('app.dependencies.get_current_manager', return_value=manager_volunteer)
    response = client.get(f"/api/v1/volunteers/{owner_volunteer_id}", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_read_volunteers_me_authenticated_success(client: TestClient, db_session: Session, authenticated_volunteer_and_token):
    """
    Tests successful retrieval of the current authenticated volunteer's profile.
    """
    owner_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    
    response = client.get(
        "/api/v1/volunteers/me",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    
    assert response.status_code == 200
    
    response_data = response.json()
    assert response_data["email"] == owner_email
    assert response_data["id"] == owner_volunteer.id
    assert response_data["is_active"] is True
    assert response_data["name"] == "Auth Test Volunteer"

@pytest.mark.asyncio
async def test_get_current_active_volunteer_missing_email_in_token(client: TestClient, db_session: Session, mocker):
    """
    Tests get_current_active_volunteer when token_data.email is missing.
    """
    from datetime import timedelta, datetime, timezone
    from app.dependencies import create_access_token
    from app.config import settings
    
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"exp": expires}
    malformed_token = create_access_token(to_encode)

    response = client.get(
        "/api/v1/volunteers/me",
        headers={"Authorization": f"Bearer {malformed_token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_get_current_active_volunteer_not_found_in_db(client: TestClient, db_session: Session, mocker):
    """
    Tests get_current_active_volunteer when volunteer is not found in DB.
    """
    from datetime import timedelta, datetime, timezone
    from app.dependencies import create_access_token
    from app.config import settings
    
    non_existent_email = "non_existent_in_db@example.com"
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": non_existent_email, "exp": expires}
    token_for_non_existent_user = create_access_token(to_encode)

    mocker.patch('app.crud.crud_volunteer.get_volunteer_by_email', return_value=None)

    response = client.get(
        "/api/v1/volunteers/me",
        headers={"Authorization": f"Bearer {token_for_non_existent_user}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_get_current_active_volunteer_inactive(client: TestClient, db_session: Session, mocker):
    """
    Tests get_current_active_volunteer when the volunteer is inactive.
    """
    from datetime import timedelta, datetime, timezone
    from app.dependencies import create_access_token
    from app.config import settings
    from app.db.models import Volunteer
    from app.utils.security import get_password_hash
    
    volunteer_email = "inactive_dependency@example.com"
    db_volunteer = Volunteer(
        name="Inactive Dep User",
        email=volunteer_email,
        password=get_password_hash("password"),
        is_active=0
    )
    db_session.add(db_volunteer)
    db_session.commit()
    db_session.refresh(db_volunteer)

    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": volunteer_email, "exp": expires}
    token = create_access_token(to_encode)

    mocker.patch('app.crud.crud_volunteer.get_volunteer_by_email', return_value=db_volunteer)

    response = client.get(
        "/api/v1/volunteers/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive volunteer"