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
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()