# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.crud import crud_need
from app.schemas import schemas

def test_create_need(db_session: Session):
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
    need = crud_need.create_need(db_session, need_data)

    assert need.id is not None
    assert need.title == "Food Delivery"
    assert need.num_volunteers_needed == 5
    assert need.format == "in-person"

def test_create_need_integrity_error(mocker, db_session: Session):
    """
    Tests the IntegrityError handling in create_need.
    Mocks db.add to raise an IntegrityError.
    """
    need_data = schemas.NeedCreate(
        title="Duplicate Need",
        description="This need will cause an integrity error",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Test Contact",
        contact_email="test@example.com",
    )

    # Mock the db.add method to raise IntegrityError
    mocker.patch.object(db_session, 'add', side_effect=IntegrityError("test", {}, "test"))
    mocker.patch.object(db_session, 'rollback') # Ensure rollback is called

    result = crud_need.create_need(db_session, need_data)

    assert result is None
    db_session.rollback.assert_called_once()

def test_get_need(db_session: Session):
    need_data = schemas.NeedCreate(
        title="Online Tutoring",
        description="Help students with math",
        num_volunteers_needed=2,
        format="virtual",
        contact_name="School",
        contact_email="school@example.com",
    )
    created_need = crud_need.create_need(db_session, need_data)

    fetched_need = crud_need.get_need(db_session, created_need.id)
    assert fetched_need is not None
    assert fetched_need.title == "Online Tutoring"

    not_found_need = crud_need.get_need(db_session, 999)
    assert not_found_need is None

def test_get_needs(db_session: Session):
    crud_need.create_need(db_session, schemas.NeedCreate(title="N1", description="desc", num_volunteers_needed=1, format="virtual", contact_name="C1", contact_email="c1@e.com"))
    crud_need.create_need(db_session, schemas.NeedCreate(title="N2", description="desc", num_volunteers_needed=1, format="virtual", contact_name="C2", contact_email="c2@e.com"))
    crud_need.create_need(db_session, schemas.NeedCreate(title="N3", description="desc", num_volunteers_needed=1, format="virtual", contact_name="C3", contact_email="c3@e.com"))

    needs = crud_need.get_needs(db_session, skip=0, limit=2)
    assert len(needs) == 2
    assert needs[0].title == "N1"
    assert needs[1].title == "N2"

    all_needs = crud_need.get_needs(db_session)
    assert len(all_needs) == 3

def test_update_need(db_session: Session):
    need_data = schemas.NeedCreate(
        title="Old Title",
        description="Old Description",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Org",
        contact_email="org@example.com",
    )
    created_need = crud_need.create_need(db_session, need_data)

    update_data = schemas.NeedCreate(
        title="New Title",
        description="Updated Description",
        num_volunteers_needed=2,
        format="in-person",
        contact_name="Org",
        contact_email="org@example.com",
    )
    updated_need = crud_need.update_need(db_session, created_need.id, update_data)

    assert updated_need is not None
    assert updated_need.title == "New Title"
    assert updated_need.description == "Updated Description"
    assert updated_need.num_volunteers_needed == 2
    assert updated_need.format == "in-person"

    # Test update non-existent
    non_existent_update = crud_need.update_need(db_session, 999, update_data)
    assert non_existent_update is None

def test_delete_need(db_session: Session):
    need_data = schemas.NeedCreate(
        title="Delete This",
        description="Delete this need",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Temp",
        contact_email="temp@example.com",
    )
    created_need = crud_need.create_need(db_session, need_data)

    success = crud_need.delete_need(db_session, created_need.id)
    assert success is True
    assert crud_need.get_need(db_session, created_need.id) is None

    # Test delete non-existent
    fail = crud_need.delete_need(db_session, 999)
    assert fail is False