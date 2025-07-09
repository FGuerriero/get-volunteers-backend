# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock
from app.crud import crud_volunteer, crud_need
from app.dependencies import get_current_active_volunteer 
from app.db.models import Volunteer
from app.schemas import schemas


def test_create_volunteer_authenticated(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    test_volunteer_email, token = authenticated_volunteer_and_token
    
    test_volunteer = crud_volunteer.get_volunteer_by_email(db_session, test_volunteer_email)
    assert test_volunteer is not None

    # Mock get_current_active_volunteer to return our test_volunteer
    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=test_volunteer)

    response = client.post(
        "/api/v1/volunteers/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "New Volunteer Profile",
            "email": "new_profile@example.com",
            "password": "newsecurepassword", 
            "phone": "111-222-3333",
            "about_me": "New Profile Test",
            "skills": "New Skills",
            "volunteer_interests": "New Interests",
            "location": "New Location",
            "availability": "New Availability",
        },
    )
    assert response.status_code == 405 
    assert response.json()["detail"] == "Volunteer profiles are created via the /register endpoint."


def test_create_volunteer_unauthenticated(client: TestClient):
    response = client.post(
        "/api/v1/volunteers/",
        json={
            "name": "Unauth Volunteer",
            "email": "unauth_volunteer@example.com",
            "password": "unauthpassword"
        },
    )
    assert response.status_code == 401 

def test_read_volunteers_public(client: TestClient, db_session: Session, authenticated_volunteer_and_token):
    volunteer1_data = schemas.VolunteerCreate(name="Public Vol One", email="public_one@example.com", password="pass1")
    volunteer2_data = schemas.VolunteerCreate(name="Public Vol Two", email="public_two@example.com", password="pass2")
    crud_volunteer.create_volunteer(db_session, volunteer1_data)
    crud_volunteer.create_volunteer(db_session, volunteer2_data)

    response = client.get("/api/v1/volunteers/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(v["email"] == "public_one@example.com" for v in data)
    assert any(v["email"] == "public_two@example.com" for v in data)

def test_read_volunteer_public(client: TestClient, db_session: Session, authenticated_volunteer_and_token):
    volunteer_data = schemas.VolunteerCreate(name="Single Public Vol", email="single_public@example.com", password="pass3")
    created_volunteer = crud_volunteer.create_volunteer(db_session, volunteer_data)
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

def test_update_volunteer_authenticated_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    owner_volunteer_email, owner_token = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    assert owner_volunteer is not None

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)

    update_data = {
        "name": "Updated Owner Volunteer",
        "email": owner_volunteer.email,
        "phone": "555-555-5555",
        "password": "newsecurepassword" 
    }
    response = client.put(f"/api/v1/volunteers/{owner_volunteer.id}", json=update_data, headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Owner Volunteer"
    assert data["phone"] == "555-555-5555"
    assert data["id"] == owner_volunteer.id

    login_response = client.post(
        "/api/v1/login",
        data={"username": owner_volunteer.email, "password": "newsecurepassword"}
    )
    assert login_response.status_code == 200

def test_update_volunteer_authenticated_not_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    owner_volunteer_email, owner_token = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    assert owner_volunteer is not None
    
    not_owner_email = "not_owner_volunteer@example.com"
    not_owner_password = "notownerpassword"
    not_owner_create_data = schemas.VolunteerCreate(
        name="Not Owner Volunteer",
        email=not_owner_email,
        password=not_owner_password
    )
    not_owner_volunteer = crud_volunteer.create_volunteer(db_session, not_owner_create_data)
    
    not_owner_token_response = client.post(
        "/api/v1/login",
        data={"username": not_owner_email, "password": not_owner_password}
    )
    not_owner_token = not_owner_token_response.json()["access_token"]

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=not_owner_volunteer)

    update_data = {
        "name": "Attempted Update",
        "email": owner_volunteer.email,
        "phone": "123-123-1234",
        "password": "some_password_to_pass_validation"
    }
    response = client.put(f"/api/v1/volunteers/{owner_volunteer.id}", json=update_data, headers={"Authorization": f"Bearer {not_owner_token}"})
    assert response.status_code == 403 
    assert "You can only update your own volunteer profile." in response.json()["detail"]

def test_update_volunteer_unauthenticated(client: TestClient, db_session: Session, authenticated_volunteer_and_token):
    owner_volunteer_email, _ = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    assert owner_volunteer is not None

    update_data = {"name": "Should Not Update", "email": owner_volunteer.email}
    response = client.put(f"/api/v1/volunteers/{owner_volunteer.id}", json=update_data)
    assert response.status_code == 401 

def test_delete_volunteer_authenticated_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    owner_volunteer_email, owner_token = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    assert owner_volunteer is not None

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)

    response = client.delete(f"/api/v1/volunteers/{owner_volunteer.id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 204

    response = client.get(f"/api/v1/volunteers/{owner_volunteer.id}")
    assert response.status_code == 404

def test_delete_volunteer_authenticated_not_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    owner_volunteer_email, _ = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    assert owner_volunteer is not None
    
    not_owner_email = "not_owner_delete_volunteer@example.com"
    not_owner_password = "notownerdeletepassword"
    not_owner_create_data = schemas.VolunteerCreate(
        name="Not Owner Delete Volunteer",
        email=not_owner_email,
        password=not_owner_password
    )
    not_owner_volunteer = crud_volunteer.create_volunteer(db_session, not_owner_create_data)
    
    not_owner_token_response = client.post(
        "/api/v1/login",
        data={"username": not_owner_email, "password": not_owner_password}
    )
    not_owner_token = not_owner_token_response.json()["access_token"]

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=not_owner_volunteer)

    response = client.delete(f"/api/v1/volunteers/{owner_volunteer.id}", headers={"Authorization": f"Bearer {not_owner_token}"})
    assert response.status_code == 403 
    assert "You can only delete your own volunteer profile." in response.json()["detail"]

def test_delete_volunteer_unauthenticated(client: TestClient, db_session: Session, authenticated_volunteer_and_token):
    owner_volunteer_email, _ = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    assert owner_volunteer is not None

    response = client.delete(f"/api/v1/volunteers/{owner_volunteer.id}")
    assert response.status_code == 401