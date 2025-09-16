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
async def test_create_access_token_with_custom_expiry(db_session: Session):
    """Test create_access_token with custom expiry delta"""
    from app.dependencies import create_access_token
    from datetime import timedelta
    
    data = {"sub": "test@example.com"}
    custom_expiry = timedelta(minutes=60)
    
    token = create_access_token(data, expires_delta=custom_expiry)
    assert token is not None
    assert isinstance(token, str)



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


