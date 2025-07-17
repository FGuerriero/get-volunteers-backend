# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from sqlalchemy.orm import  Session 
from fastapi.testclient import TestClient

from app.config import settings
from app.db.database import Base, get_db

# Temporarily set the database URL to an in-memory SQLite for testing
# This must happen *before* importing app.app if app.app initializes
# database components based on settings.
settings.database_url = "sqlite:///:memory:"

# Re-import or re-create engine and SessionLocal based on the new settings.database_url
# This ensures that the app's database connection uses the in-memory SQLite.
# We need to do this explicitly because app.db.database.py might have already
# initialized its engine based on the original settings.
from app.db.database import engine, SessionLocal # Re-import after setting test DB URL

# Import the main FastAPI app
from app.app import app
from app.db.models import Volunteer


@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    Creates a new database session for the entire test session, with all tables created.
    Rolls back the session after the test to ensure a clean state.
    """
    # Create the tables in the test database
    Base.metadata.create_all(bind=engine)
    db = SessionLocal() # Use the SessionLocal from app.db.database
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after the test to ensure a clean slate for the next test run
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def client_fixture(db_session: Session):
    """
    Provides a FastAPI TestClient that overrides the get_db dependency
    to use the test database session.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# Helper fixture to create and authenticate a test volunteer
@pytest.fixture(name="authenticated_volunteer_and_token")
def authenticated_volunteer_and_token_fixture(client: TestClient):
    email = "auth_test_volunteer@example.com"
    password = "testpassword"

    # Register the volunteer
    register_response = client.post(
        "/api/v1/register",
        json={
            "name": "Auth Test Volunteer",
            "email": email,
            "password": password,
            "phone": "123-456-7890",
            "about_me": "Test user for auth",
            "skills": "Testing",
            "volunteer_interests": "Auth",
            "location": "Test City",
            "availability": "Anytime"
        }
    )
    assert register_response.status_code == 201
    
    # Login to get a token
    token_response = client.post(
        "/api/v1/login",
        data={"username": email, "password": password}
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]

    return email, token