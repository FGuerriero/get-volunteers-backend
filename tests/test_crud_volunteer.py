# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from sqlalchemy.orm import Session

from app.crud import crud_volunteer
from app.schemas import schemas

def test_create_volunteer(db_session: Session):
    volunteer_data = schemas.VolunteerCreate(
        name="Test Volunteer",
        email="test@example.com",
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

    # Test duplicate email
    duplicate_volunteer = crud_volunteer.create_volunteer(db_session, volunteer_data)
    assert duplicate_volunteer is None

def test_get_volunteer(db_session: Session):
    volunteer_data = schemas.VolunteerCreate(name="Get User", email="get@example.com")
    created_volunteer = crud_volunteer.create_volunteer(db_session, volunteer_data)

    fetched_volunteer = crud_volunteer.get_volunteer(db_session, created_volunteer.id)
    assert fetched_volunteer is not None
    assert fetched_volunteer.email == "get@example.com"

    not_found_volunteer = crud_volunteer.get_volunteer(db_session, 999)
    assert not_found_volunteer is None

def test_get_volunteer_by_email(db_session: Session):
    volunteer_data = schemas.VolunteerCreate(name="Email User", email="email@example.com")
    created_volunteer = crud_volunteer.create_volunteer(db_session, volunteer_data)

    fetched_volunteer = crud_volunteer.get_volunteer_by_email(db_session, "email@example.com")
    assert fetched_volunteer is not None
    assert fetched_volunteer.name == "Email User"

    not_found_volunteer = crud_volunteer.get_volunteer_by_email(db_session, "nonexistent@example.com")
    assert not_found_volunteer is None

def test_get_volunteers(db_session: Session):
    crud_volunteer.create_volunteer(db_session, schemas.VolunteerCreate(name="V1", email="v1@example.com"))
    crud_volunteer.create_volunteer(db_session, schemas.VolunteerCreate(name="V2", email="v2@example.com"))
    crud_volunteer.create_volunteer(db_session, schemas.VolunteerCreate(name="V3", email="v3@example.com"))

    volunteers = crud_volunteer.get_volunteers(db_session, skip=0, limit=2)
    assert len(volunteers) == 2
    assert volunteers[0].name == "V1"
    assert volunteers[1].name == "V2"

    all_volunteers = crud_volunteer.get_volunteers(db_session)
    assert len(all_volunteers) == 3

def test_update_volunteer(db_session: Session):
    volunteer_data = schemas.VolunteerCreate(name="Old Name", email="old@example.com")
    created_volunteer = crud_volunteer.create_volunteer(db_session, volunteer_data)

    update_data = schemas.VolunteerCreate(name="New Name", phone="987-654-3210", email="old@example.com") # Email must match for update
    updated_volunteer = crud_volunteer.update_volunteer(db_session, created_volunteer.id, update_data)

    assert updated_volunteer is not None
    assert updated_volunteer.name == "New Name"
    assert updated_volunteer.phone == "987-654-3210"

    # Test update non-existent
    non_existent_update = crud_volunteer.update_volunteer(db_session, 999, update_data)
    assert non_existent_update is None

def test_delete_volunteer(db_session: Session):
    volunteer_data = schemas.VolunteerCreate(name="Delete Me", email="delete@example.com")
    created_volunteer = crud_volunteer.create_volunteer(db_session, volunteer_data)

    success = crud_volunteer.delete_volunteer(db_session, created_volunteer.id)
    assert success is True
    assert crud_volunteer.get_volunteer(db_session, created_volunteer.id) is None

    # Test delete non-existent
    fail = crud_volunteer.delete_volunteer(db_session, 999)
    assert fail is False