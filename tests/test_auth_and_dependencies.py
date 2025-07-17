'''
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Thu Jul 17 2025
# SPDX-License-Identifier: MIT
'''

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock
from datetime import timedelta, datetime, timezone

from app.crud import crud_volunteer
from app.schemas import schemas
from app.db.models import Volunteer
from app.utils.security import get_password_hash
from app.dependencies import create_access_token
from app.config import settings


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: TestClient, db_session: Session):
    """
    Tests login with non-existent email or incorrect password.
    """
    response = client.post(
        "/api/v1/login",
        data={"username": "nonexistent@example.com", "password": "anypassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

    volunteer_data = schemas.VolunteerCreate(
        name="Login Test User",
        email="login_test@example.com",
        password="correctpassword"
    )
    await crud_volunteer.create_volunteer(db_session, volunteer_data, background_tasks=MagicMock())

    response = client.post(
        "/api/v1/login",
        data={"username": "login_test@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

@pytest.mark.asyncio
async def test_login_inactive_volunteer(client: TestClient, db_session: Session):
    """
    Tests login attempt with an inactive volunteer account.
    """
    volunteer_data = schemas.VolunteerCreate(
        name="Inactive User",
        email="inactive@example.com",
        password="inactivepassword"
    )
    db_volunteer = Volunteer(
        name=volunteer_data.name,
        email=volunteer_data.email,
        password=get_password_hash(volunteer_data.password),
        is_active=0
    )
    db_session.add(db_volunteer)
    db_session.commit()
    db_session.refresh(db_volunteer)

    response = client.post(
        "/api/v1/login",
        data={"username": "inactive@example.com", "password": "inactivepassword"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive volunteer"

@pytest.mark.asyncio
async def test_get_current_active_volunteer_missing_email_in_token(client: TestClient, db_session: Session, mocker):
    """
    Tests get_current_active_volunteer when token_data.email is missing.
    """
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"exp": expires}
    malformed_token = create_access_token(to_encode)

    response = client.get(
        "/api/v1/volunteers/me/",
        headers={"Authorization": f"Bearer {malformed_token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_get_current_active_volunteer_not_found_in_db(client: TestClient, db_session: Session, mocker):
    """
    Tests get_current_active_volunteer when volunteer is not found in DB.
    """
    non_existent_email = "non_existent_in_db@example.com"
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": non_existent_email, "exp": expires}
    token_for_non_existent_user = create_access_token(to_encode)

    mocker.patch('app.crud.crud_volunteer.get_volunteer_by_email', return_value=None)

    response = client.get(
        "/api/v1/volunteers/me/",
        headers={"Authorization": f"Bearer {token_for_non_existent_user}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_get_current_active_volunteer_inactive(client: TestClient, db_session: Session, mocker):
    """
    Tests get_current_active_volunteer when the volunteer is inactive.
    """
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
        "/api/v1/volunteers/me/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive volunteer"

@pytest.mark.asyncio
async def test_register_volunteer_existing_email(client: TestClient, db_session: Session):
    """
    Tests registering a volunteer with an email that is already registered.
    """
    volunteer_data = schemas.VolunteerCreate(
        name="Existing Email User",
        email="existing_email_for_reg_test@example.com",
        password="password123"
    )
    response = client.post("/api/v1/register", json=volunteer_data.model_dump())
    assert response.status_code == 201

    duplicate_volunteer_data = schemas.VolunteerCreate(
        name="Another User",
        email="existing_email_for_reg_test@example.com",
        password="anotherpassword"
    )
    response = client.post("/api/v1/register", json=duplicate_volunteer_data.model_dump())
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

@pytest.mark.asyncio
async def test_read_volunteers_me_authenticated_success(client: TestClient, db_session: Session, authenticated_volunteer_and_token):
    """
    Tests successful retrieval of the current authenticated volunteer's profile.
    """
    owner_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    
    response = client.get(
        "/api/v1/volunteers/me/",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    
    assert response.status_code == 200
    
    response_data = response.json()
    assert response_data["email"] == owner_email
    assert response_data["id"] == owner_volunteer.id
    assert response_data["is_active"] is True
    assert response_data["name"] == "Auth Test Volunteer"
