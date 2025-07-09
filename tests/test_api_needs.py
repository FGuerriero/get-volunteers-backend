# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock
from app.dependencies import get_current_active_volunteer 
from app.db.models import Volunteer 
from app.crud import crud_volunteer, crud_need
from app.schemas import schemas
from app.utils.security import get_password_hash

def test_create_need_authenticated(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    test_volunteer_email, token = authenticated_volunteer_and_token

    test_volunteer = crud_volunteer.get_volunteer_by_email(db_session, test_volunteer_email)
    assert test_volunteer is not None

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=test_volunteer)

    response = client.post(
        "/api/v1/needs/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Auth Need",
            "description": "Description for auth need",
            "num_volunteers_needed": 1,
            "format": "virtual",
            "contact_name": "Auth Contact",
            "contact_email": "auth_contact@example.com",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Auth Need"
    assert data["owner_id"] == test_volunteer.id
    assert "id" in data

def test_create_need_unauthenticated(client: TestClient):
    response = client.post(
        "/api/v1/needs/",
        json={
            "title": "Unauth Need",
            "description": "Description for unauth need",
            "num_volunteers_needed": 1,
            "format": "virtual",
            "contact_name": "Unauth Contact",
            "contact_email": "unauth_contact@example.com",
        },
    )
    assert response.status_code == 401

def test_read_needs_public(client: TestClient, db_session: Session):
    volunteer = Volunteer(email="public_need_owner@example.com", name="Public Owner", password=get_password_hash("hashedpassword"), is_active=1)
    db_session.add(volunteer)
    db_session.commit()
    db_session.refresh(volunteer)

    crud_need.create_need(db_session, schemas.NeedCreate(title="Need One Public", description="Desc One", num_volunteers_needed=1, format="in-person", contact_name="C1", contact_email="c1@e.com"), owner_id=volunteer.id)
    crud_need.create_need(db_session, schemas.NeedCreate(title="Need Two Public", description="Desc Two", num_volunteers_needed=2, format="virtual", contact_name="C2", contact_email="c2@e.com"), owner_id=volunteer.id)

    response = client.get("/api/v1/needs/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2 # May be more if other tests created needs
    assert any(n["title"] == "Need One Public" for n in data)
    assert any(n["title"] == "Need Two Public" for n in data)

def test_read_need_public(client: TestClient, db_session: Session):
    volunteer = Volunteer(email="single_need_owner@example.com", name="Single Owner", password=get_password_hash("hashedpassword"), is_active=1)
    db_session.add(volunteer)
    db_session.commit()
    db_session.refresh(volunteer)

    created_need = crud_need.create_need(db_session, schemas.NeedCreate(title="Single Need Public", description="Single need desc", num_volunteers_needed=1, format="virtual", contact_name="Single C", contact_email="single@e.com"), owner_id=volunteer.id)
    need_id = created_need.id

    response = client.get(f"/api/v1/needs/{need_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Single Need Public"
    assert data["id"] == need_id

    response = client.get("/api/v1/needs/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Need not found"

def test_update_need_authenticated_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    owner_volunteer_email, owner_token = authenticated_volunteer_and_token

    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    assert owner_volunteer is not None

    need_create_response = client.post(
        "/api/v1/needs/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Owner Need", "description": "Owner desc", "num_volunteers_needed": 1, "format": "virtual", "contact_name": "Owner C", "contact_email": "owner@e.com"},
    )
    assert need_create_response.status_code == 201
    need_id = need_create_response.json()["id"]

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)

    update_data = {
        "title": "Updated Owner Need",
        "description": "Updated owner desc",
        "num_volunteers_needed": 2,
        "format": "in-person",
        "contact_name": "Owner C",
        "contact_email": "owner@e.com",
    }
    response = client.put(f"/api/v1/needs/{need_id}", json=update_data, headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Owner Need"
    assert data["description"] == "Updated owner desc"
    assert data["num_volunteers_needed"] == 2
    assert data["format"] == "in-person"
    assert data["id"] == need_id
    assert data["owner_id"] == owner_volunteer.id

def test_update_need_authenticated_not_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    owner_volunteer_email, owner_token = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    assert owner_volunteer is not None
    
    not_owner_email = "not_owner_need_volunteer@example.com"
    not_owner_password = "notownerneedpassword"
    not_owner_create_data = schemas.VolunteerCreate(
        name="Not Owner Need Volunteer",
        email=not_owner_email,
        password=not_owner_password
    )
    not_owner_volunteer = crud_volunteer.create_volunteer(db_session, not_owner_create_data)
    
    not_owner_token_response = client.post(
        "/api/v1/login",
        data={"username": not_owner_email, "password": not_owner_password}
    )
    not_owner_token = not_owner_token_response.json()["access_token"]

    need_create_response = client.post(
        "/api/v1/needs/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Another Need", "description": "Another desc", "num_volunteers_needed": 1, "format": "virtual", "contact_name": "Another C", "contact_email": "another@e.com"},
    )
    assert need_create_response.status_code == 201
    need_id = need_create_response.json()["id"]

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=not_owner_volunteer)

    update_data = {
        "title": "Attempted Update Need",
        "description": "Attempted update desc",
        "num_volunteers_needed": 1,
        "format": "virtual",
        "contact_name": "Another C",
        "contact_email": "another@e.com",
    }
    response = client.put(f"/api/v1/needs/{need_id}", json=update_data, headers={"Authorization": f"Bearer {not_owner_token}"})
    assert response.status_code == 404 
    assert "not found or you don't have permission" in response.json()["detail"]

def test_update_need_unauthenticated(client: TestClient, db_session: Session, authenticated_volunteer_and_token):
    owner_volunteer_email, owner_token = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    assert owner_volunteer is not None

    need_create_response = client.post(
        "/api/v1/needs/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Unauth Update Need", "description": "Unauth update desc", "num_volunteers_needed": 1, "format": "virtual", "contact_name": "Unauth C", "contact_email": "unauth@e.com"},
    )
    assert need_create_response.status_code == 201
    need_id = need_create_response.json()["id"]

    update_data = {"title": "Should Not Update Need", "description": "Should not update desc", "num_volunteers_needed": 1, "format": "virtual", "contact_name": "Unauth C", "contact_email": "unauth@e.com"}
    response = client.put(f"/api/v1/needs/{need_id}", json=update_data)
    assert response.status_code == 401 

def test_delete_need_authenticated_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    owner_volunteer_email, owner_token = authenticated_volunteer_and_token
    
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_volunteer_email)
    assert owner_volunteer is not None

    need_create_response = client.post(
        "/api/v1/needs/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Delete Me Owner Need", "description": "Delete me owner desc", "num_volunteers_needed": 1, "format": "virtual", "contact_name": "Del C", "contact_email": "del@e.com"},
    )
    assert need_create_response.status_code == 201
    need_id = need_create_response.json()["id"]

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=owner_volunteer)

    response = client.delete(f"/api/v1/needs/{need_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 204

    response = client.get(f"/api/v1/needs/{need_id}")
    assert response.status_code == 404

def test_delete_need_authenticated_not_owner(client: TestClient, db_session: Session, mocker, authenticated_volunteer_and_token):
    _, owner_token = authenticated_volunteer_and_token
    
    not_owner_email = "not_owner_delete_need_volunteer@example.com"
    not_owner_password = "notownerdeleteneedpassword"
    not_owner_create_data = schemas.VolunteerCreate(
        name="Not Owner Delete Need Volunteer",
        email=not_owner_email,
        password=not_owner_password
    )
    not_owner_volunteer = crud_volunteer.create_volunteer(db_session, not_owner_create_data)
    
    not_owner_token_response = client.post(
        "/api/v1/login",
        data={"username": not_owner_email, "password": not_owner_password}
    )
    not_owner_token = not_owner_token_response.json()["access_token"]

    need_create_response = client.post(
        "/api/v1/needs/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Delete Me Other Need", "description": "Delete me other desc", "num_volunteers_needed": 1, "format": "virtual", "contact_name": "Del O", "contact_email": "delo@e.com"},
    )
    assert need_create_response.status_code == 201
    need_id = need_create_response.json()["id"]

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=not_owner_volunteer)

    response = client.delete(f"/api/v1/needs/{need_id}", headers={"Authorization": f"Bearer {not_owner_token}"})
    assert response.status_code == 404 
    assert "not found or you don't have permission" in response.json()["detail"]

def test_delete_need_unauthenticated(client: TestClient, db_session: Session, authenticated_volunteer_and_token):
    _, owner_token = authenticated_volunteer_and_token
    need_create_response = client.post(
        "/api/v1/needs/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Unauth Delete Need", "description": "Unauth delete desc", "num_volunteers_needed": 1, "format": "virtual", "contact_name": "Unauth D", "contact_email": "unauthd@e.com"},
    )
    assert need_create_response.status_code == 201
    need_id = need_create_response.json()["id"]

    response = client.delete(f"/api/v1/needs/{need_id}")
    assert response.status_code == 401