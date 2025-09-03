# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session 
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Safety check to prevent tests from running against production database
if os.getenv("TESTING") != "1":
    os.environ["TESTING"] = "1"

# Create test database engine and session
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

from app.db.database import Base, get_db
from app.app import app
from app.db.models import Volunteer
from tests.test_helpers import MockBackgroundTasks
from fastapi import BackgroundTasks
import pytest_asyncio


@pytest.fixture(name="db_session", scope="function")
def db_session_fixture():
    """
    Creates a new database session for each test, with all tables created.
    Uses simple session creation for SQLite in-memory database.
    """
    # Create the tables in the test database
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    db = TestSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after the test to ensure a clean slate
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(name="client")
def client_fixture(db_session: Session, mocker):
    """
    Provides a FastAPI TestClient that overrides the get_db dependency
    to use the test database session and mocks all background tasks.
    """
    def override_get_db():
        yield db_session
    
    def override_background_tasks():
        return MockBackgroundTasks()

    # Mock all background task functions globally
    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[BackgroundTasks] = override_background_tasks
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

# Helper fixture to create and authenticate a test volunteer
@pytest.fixture(name="authenticated_volunteer_and_token")
def authenticated_volunteer_and_token_fixture(client: TestClient, db_session: Session, mocker):
    # Mock background tasks to prevent database access issues
    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    
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