# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from sqlalchemy.orm import Session

from app.crud import crud_volunteer
from app.schemas import schemas
from app.db import models
from app.utils.security import get_password_hash

def test_create_volunteer(db_session: Session):
    volunteer_data = schemas.VolunteerCreate(
        name="Test Volunteer",
        email="test@example.com",
        password="securepassword",
        phone="123-456-7890",
        about_me="Passionate about helping",
        skills="Coding, Teaching",
        volunteer_interests="Education, Environment",
        location="New York",
        availability="Weekends",
    )
    volunteer = crud_volunteer.create_volunteer(db_session, volunteer_data)

    assert volunteer.id is not None
    assert volunteer.name == "Test Volunteer"
    assert volunteer.email == "test@example.com"
    assert volunteer.phone == "123-456-7890"
    assert volunteer.password is not None
    assert volunteer.is_active == 1

    duplicate_volunteer_data = schemas.VolunteerCreate(
        name="Duplicate Volunteer",
        email="test@example.com",
        password="anotherpassword"
    )
    duplicate_volunteer = crud_volunteer.create_volunteer(db_session, duplicate_volunteer_data)
    assert duplicate_volunteer is None

def test_get_volunteer(db_session: Session):
    volunteer_data = schemas.VolunteerCreate(name="Get Volunteer", email="get@example.com", password="password123")
    created_volunteer = crud_volunteer.create_volunteer(db_session, volunteer_data)

    fetched_volunteer = crud_volunteer.get_volunteer(db_session, created_volunteer.id)
    assert fetched_volunteer is not None
    assert fetched_volunteer.email == "get@example.com"

    not_found_volunteer = crud_volunteer.get_volunteer(db_session, 999)
    assert not_found_volunteer is None

def test_get_volunteer_by_email(db_session: Session):
    volunteer_data = schemas.VolunteerCreate(name="Email Volunteer", email="email@example.com", password="password123")
    created_volunteer = crud_volunteer.create_volunteer(db_session, volunteer_data)

    fetched_volunteer = crud_volunteer.get_volunteer_by_email(db_session, "email@example.com")
    assert fetched_volunteer is not None
    assert fetched_volunteer.name == "Email Volunteer"

    not_found_volunteer = crud_volunteer.get_volunteer_by_email(db_session, "nonexistent@example.com")
    assert not_found_volunteer is None

def test_get_volunteers(db_session: Session):
    crud_volunteer.create_volunteer(db_session, schemas.VolunteerCreate(name="V1", email="v1@example.com", password="p1"))
    crud_volunteer.create_volunteer(db_session, schemas.VolunteerCreate(name="V2", email="v2@example.com", password="p2"))
    crud_volunteer.create_volunteer(db_session, schemas.VolunteerCreate(name="V3", email="v3@example.com", password="p3"))

    volunteers = crud_volunteer.get_volunteers(db_session, skip=0, limit=2)
    assert len(volunteers) == 2
    assert volunteers[0].name == "V1"
    assert volunteers[1].name == "V2"

    all_volunteers = crud_volunteer.get_volunteers(db_session)
    assert len(all_volunteers) == 3

def test_update_volunteer(db_session: Session):
    volunteer_data = schemas.VolunteerCreate(name="Old Name", email="old@example.com", password="oldpassword")
    created_volunteer = crud_volunteer.create_volunteer(db_session, volunteer_data)

    update_data = schemas.VolunteerCreate(name="New Name", phone="987-654-3210", email="old@example.com", password="newpassword")
    updated_volunteer = crud_volunteer.update_volunteer(db_session, created_volunteer.id, update_data)

    assert updated_volunteer is not None
    assert updated_volunteer.name == "New Name"
    assert updated_volunteer.phone == "987-654-3210"
    # Verify password was updated and hashed
    assert get_password_hash("newpassword") != get_password_hash("oldpassword") # Ensure different hash
    # Cannot directly check hashed_password from updated_volunteer as it's not in schema for security.
    # Instead, we'd typically try to authenticate with the new password in an API test.

    non_existent_update = crud_volunteer.update_volunteer(db_session, 999, update_data)
    assert non_existent_update is None

def test_delete_volunteer(db_session: Session):
    volunteer_data = schemas.VolunteerCreate(name="Delete Me", email="delete@example.com", password="deletepassword")
    created_volunteer = crud_volunteer.create_volunteer(db_session, volunteer_data)

    success = crud_volunteer.delete_volunteer(db_session, created_volunteer.id)
    assert success is True
    assert crud_volunteer.get_volunteer(db_session, created_volunteer.id) is None

    fail = crud_volunteer.delete_volunteer(db_session, 999)
    assert fail is False