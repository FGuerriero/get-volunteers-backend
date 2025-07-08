# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_create_volunteer(client: TestClient, db_session: Session):
    response = client.post(
        "/api/v1/volunteers/",
        json={
            "name": "API Test Volunteer",
            "email": "api_test@example.com",
            "phone": "111-222-3333",
            "about_me": "Loves FastAPI",
            "skills": "Python, Testing",
            "volunteer_interests": "Tech, Mentoring",
            "location": "Remote",
            "availability": "Weekdays",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API Test Volunteer"
    assert data["email"] == "api_test@example.com"
    assert "id" in data

    # Test duplicate email
    response = client.post(
        "/api/v1/volunteers/",
        json={
            "name": "Another Test Volunteer",
            "email": "api_test@example.com", # Duplicate email
            "phone": "444-555-6666",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_read_volunteers(client: TestClient, db_session: Session):
    client.post(
        "/api/v1/volunteers/",
        json={"name": "Volunteer One", "email": "one@example.com"},
    )
    client.post(
        "/api/v1/volunteers/",
        json={"name": "Volunteer Two", "email": "two@example.com"},
    )

    response = client.get("/api/v1/volunteers/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2 # Could be more if other tests added
    assert any(v["email"] == "one@example.com" for v in data)
    assert any(v["email"] == "two@example.com" for v in data)

    # Test skip and limit
    response = client.get("/api/v1/volunteers/?skip=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

def test_read_volunteer(client: TestClient, db_session: Session):
    create_response = client.post(
        "/api/v1/volunteers/",
        json={"name": "Single Volunteer", "email": "single@example.com"},
    )
    volunteer_id = create_response.json()["id"]

    response = client.get(f"/api/v1/volunteers/{volunteer_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Single Volunteer"
    assert data["email"] == "single@example.com"
    assert data["id"] == volunteer_id

    # Test not found
    response = client.get("/api/v1/volunteers/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Volunteer not found"

def test_update_volunteer(client: TestClient, db_session: Session):
    create_response = client.post(
        "/api/v1/volunteers/",
        json={"name": "Old Name", "email": "old_update@example.com"},
    )
    volunteer_id = create_response.json()["id"]

    update_data = {
        "name": "Updated Name",
        "email": "old_update@example.com", # Email must be provided, but doesn't change
        "phone": "555-555-5555",
    }
    response = client.put(f"/api/v1/volunteers/{volunteer_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["phone"] == "555-555-5555"
    assert data["id"] == volunteer_id

    # Test update non-existent
    response = client.put("/api/v1/volunteers/99999", json=update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Volunteer not found"

def test_delete_volunteer(client: TestClient, db_session: Session):
    create_response = client.post(
        "/api/v1/volunteers/",
        json={"name": "Delete Me", "email": "delete_me@example.com"},
    )
    volunteer_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/volunteers/{volunteer_id}")
    assert response.status_code == 204 # No Content

    # Verify it's gone
    response = client.get(f"/api/v1/volunteers/{volunteer_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Volunteer not found"

    # Test delete non-existent
    response = client.delete("/api/v1/volunteers/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Volunteer not found"