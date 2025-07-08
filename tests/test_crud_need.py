# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from unittest.mock import MagicMock

from app.crud import crud_need
from app.schemas import schemas
from app.db import models
from app.dependencies import get_password_hash 

def create_dummy_volunteer(db_session: Session, email: str = "dummy_owner@example.com"):
    volunteer = models.Volunteer(
        name="Dummy Owner",
        email=email,
        password=get_password_hash("password"),
        is_active=1
    )
    db_session.add(volunteer)
    db_session.commit()
    db_session.refresh(volunteer)
    return volunteer

def test_create_need(db_session: Session):
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_need_create@example.com")

    need_data = schemas.NeedCreate(
        title="Food Delivery",
        description="Deliver food to elderly",
        required_tasks="Driving, Lifting",
        required_skills="Driving license",
        num_volunteers_needed=5,
        format="in-person",
        location_details="Downtown area",
        contact_name="Charity Org",
        contact_email="contact@charity.org",
        contact_phone="111-222-3333",
    )
    need = crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id)

    assert need.id is not None
    assert need.title == "Food Delivery"
    assert need.num_volunteers_needed == 5
    assert need.format == "in-person"
    assert need.owner_id == owner_volunteer.id

def test_create_need_integrity_error(mocker, db_session: Session):
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_need_integrity@example.com")

    need_data = schemas.NeedCreate(
        title="Duplicate Need",
        description="This need will cause an integrity error",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Test Contact",
        contact_email="test@example.com",
    )

    mocker.patch.object(db_session, 'add', side_effect=IntegrityError("test", {}, "test"))
    mocker.patch.object(db_session, 'rollback')

    result = crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id)

    assert result is None
    db_session.rollback.assert_called_once()

def test_get_need(db_session: Session):
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_need_get@example.com")

    need_data = schemas.NeedCreate(
        title="Online Tutoring",
        description="Help students with math",
        num_volunteers_needed=2,
        format="virtual",
        contact_name="School",
        contact_email="school@example.com",
    )
    created_need = crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id)

    fetched_need = crud_need.get_need(db_session, created_need.id)
    assert fetched_need is not None
    assert fetched_need.title == "Online Tutoring"
    assert fetched_need.owner_id == owner_volunteer.id

    not_found_need = crud_need.get_need(db_session, 999)
    assert not_found_need is None

def test_get_needs(db_session: Session):
    owner_volunteer1 = create_dummy_volunteer(db_session, email="owner_need_get_1@example.com")
    owner_volunteer2 = create_dummy_volunteer(db_session, email="owner_need_get_2@example.com")
    owner_volunteer3 = create_dummy_volunteer(db_session, email="owner_need_get_3@example.com")

    crud_need.create_need(db_session, schemas.NeedCreate(title="N1", description="desc", num_volunteers_needed=1, format="virtual", contact_name="C1", contact_email="c1@e.com"), owner_id=owner_volunteer1.id)
    crud_need.create_need(db_session, schemas.NeedCreate(title="N2", description="desc", num_volunteers_needed=1, format="virtual", contact_name="C2", contact_email="c2@e.com"), owner_id=owner_volunteer2.id)
    crud_need.create_need(db_session, schemas.NeedCreate(title="N3", description="desc", num_volunteers_needed=1, format="virtual", contact_name="C3", contact_email="c3@e.com"), owner_id=owner_volunteer3.id)

    needs = crud_need.get_needs(db_session, skip=0, limit=2)
    assert len(needs) == 2
    assert needs[0].title == "N1"
    assert needs[1].title == "N2"

    all_needs = crud_need.get_needs(db_session)
    assert len(all_needs) == 3

def test_update_need(db_session: Session):
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_need_update@example.com")

    need_data = schemas.NeedCreate(
        title="Old Title",
        description="Old Description",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Org",
        contact_email="org@example.com",
    )
    created_need = crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id)

    update_data = schemas.NeedCreate(
        title="New Title",
        description="Updated Description",
        num_volunteers_needed=2,
        format="in-person",
        contact_name="Org",
        contact_email="org@example.com",
    )
    updated_need = crud_need.update_need(db_session, created_need.id, update_data, owner_id=owner_volunteer.id)

    assert updated_need is not None
    assert updated_need.title == "New Title"
    assert updated_need.description == "Updated Description"
    assert updated_need.num_volunteers_needed == 2
    assert updated_need.format == "in-person"
    assert updated_need.owner_id == owner_volunteer.id

    other_volunteer = create_dummy_volunteer(db_session, email="other_owner_need_update@example.com")
    non_existent_update_by_other_volunteer = crud_need.update_need(db_session, created_need.id, update_data, owner_id=other_volunteer.id)
    assert non_existent_update_by_other_volunteer is None

    non_existent_update = crud_need.update_need(db_session, 999, update_data, owner_id=owner_volunteer.id)
    assert non_existent_update is None

def test_delete_need(db_session: Session):
    owner_volunteer = create_dummy_volunteer(db_session, email="owner_need_delete@example.com")

    need_data = schemas.NeedCreate(
        title="Delete This",
        description="Delete this need",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Temp",
        contact_email="temp@example.com",
    )
    created_need = crud_need.create_need(db_session, need_data, owner_id=owner_volunteer.id)

    success = crud_need.delete_need(db_session, created_need.id, owner_id=owner_volunteer.id)
    assert success is True
    assert crud_need.get_need(db_session, created_need.id) is None

    other_volunteer = create_dummy_volunteer(db_session, email="other_owner_need_delete@example.com")
    fail_by_other_volunteer = crud_need.delete_need(db_session, created_need.id, owner_id=other_volunteer.id)
    assert fail_by_other_volunteer is False

    fail = crud_need.delete_need(db_session, 999, owner_id=owner_volunteer.id)
    assert fail is False