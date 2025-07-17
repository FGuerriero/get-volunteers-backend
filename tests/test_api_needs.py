# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from app.crud import crud_need, crud_volunteer, crud_match
from app.schemas import schemas
from fastapi import BackgroundTasks

class MockBackgroundTasks:
    def __init__(self):
        self.tasks = []
        self.db_session = None

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))

    async def run_tasks(self):
        for func, args, kwargs in self.tasks:
            if func.__module__.startswith('app.crud.crud_match'):
                func(self.db_session, *args, **kwargs)
            else:
                if func.__name__ == 'trigger_volunteer_matching':
                    volunteer_id = args[0]
                    volunteer_obj = crud_volunteer.get_volunteer(self.db_session, volunteer_id)
                    if volunteer_obj:
                        await func(self.db_session, volunteer_obj)
                    else:
                        print(f"Warning: Mocked trigger_volunteer_matching received ID {volunteer_id} but volunteer not found.")
                elif func.__name__ == 'trigger_need_matching':
                    need_id = args[0]
                    need_obj = crud_need.get_need(self.db_session, need_id)
                    all_volunteers = crud_volunteer.get_volunteers(self.db_session)
                    if need_obj:
                        await func(self.db_session, need_obj, all_volunteers)
                    else:
                        print(f"Warning: Mocked trigger_need_matching received ID {need_id} but need not found.")
                else:
                    await func(*args, **kwargs)
        self.tasks.clear()

@pytest.mark.asyncio
async def test_create_need_authenticated_and_check_matching(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    mock_background_tasks_for_api = MockBackgroundTasks()
    mock_background_tasks_for_api.db_session = db_session
    client.app.dependency_overrides[BackgroundTasks] = lambda: mock_background_tasks_for_api

    mock_matching_service_class = mocker.patch('app.services.matching_service.MatchingService')
    mock_matching_service_instance = mock_matching_service_class.return_value
    mock_matching_service_instance.reanalyze_all_matches.side_effect = MagicMock()
    mock_matching_service_instance.analyze_and_match.side_effect = MagicMock()

    mock_trigger_volunteer_matching = mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mock_trigger_volunteer_matching.side_effect = MagicMock()

    mock_trigger_need_matching = mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    try:
        crud_match.delete_all_matches(db_session)

        owner_email, owner_token = authenticated_volunteer_and_token
        owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
        assert owner_volunteer is not None

        matchable_volunteer_data = schemas.VolunteerCreate(
            name="Matchable Volunteer for Need",
            email="matchable_for_need@example.com",
            password="securepassword",
            skills="Project Management, Communication",
            volunteer_interests="Community Events"
        )
        
        matchable_volunteer = await crud_volunteer.create_volunteer(db_session, matchable_volunteer_data, mock_background_tasks_for_api)
        assert matchable_volunteer is not None
        
        def mock_trigger_need_side_effect(need_id: int):
            need_param = crud_need.get_need(db_session, need_id)
            all_volunteers_param = crud_volunteer.get_volunteers(db_session)

            if need_param and all_volunteers_param:
                crud_match.delete_matches_for_need(db_session, need_param.id)
                crud_match.create_match(
                    db_session,
                    matchable_volunteer.id,
                    need_param.id,
                    "Volunteer's project management skills and community interests align with this need."
                )
        mock_trigger_need_matching.side_effect = mock_trigger_need_side_effect

        need_data = schemas.NeedCreate(
            title="Community Project Lead",
            description="Lead a community project, requires good organizational skills.",
            required_tasks="Organize, Plan, Communicate",
            required_skills="Project Management, Leadership, Communication",
            num_volunteers_needed=1,
            format="in-person",
            contact_name="Org Contact",
            contact_email="org@example.com",
            contact_phone="987-654-3210"
        )

        response = client.post(
            "/api/v1/needs/",
            json=need_data.model_dump(),
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 201
        created_need = response.json()
        created_need_id = created_need["id"]
        assert created_need["owner_id"] == owner_volunteer.id

        await mock_background_tasks_for_api.run_tasks()

        matches = crud_match.get_matches_for_need(db_session, created_need_id)
        assert len(matches) >= 1
        assert any(m.volunteer_id == matchable_volunteer.id for m in matches)
        assert any("project management" in m.match_details.lower() for m in matches)

    finally:
        client.app.dependency_overrides = {}


def test_create_need_unauthenticated(client: TestClient):
    need_data = schemas.NeedCreate(
        title="Unauthorized Need",
        description="This should fail.",
        num_volunteers_needed=1,
        format="virtual",
        contact_name="Anon",
        contact_email="anon@example.com"
    )
    response = client.post("/api/v1/needs/", json=need_data.model_dump())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_read_needs_public(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    mock_matching_service_class = mocker.patch('app.services.matching_service.MatchingService')
    mock_matching_service_instance = mock_matching_service_class.return_value
    mock_matching_service_instance.reanalyze_all_matches.side_effect = MagicMock()
    mock_matching_service_instance.analyze_and_match.side_effect = MagicMock()

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    need1_data = schemas.NeedCreate(title="Public Need One", description="Desc 1", num_volunteers_needed=1, format="in-person", contact_name="C1", contact_email="c1@e.com")
    need2_data = schemas.NeedCreate(title="Public Need Two", description="Desc 2", num_volunteers_needed=2, format="virtual", contact_name="C2", contact_email="c2@e.com")

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    await crud_need.create_need(db_session, need1_data, owner_volunteer.id, mock_bg_tasks)
    await crud_need.create_need(db_session, need2_data, owner_volunteer.id, mock_bg_tasks)

    response = client.get("/api/v1/needs/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(n["title"] == "Public Need One" for n in data)
    assert any(n["title"] == "Public Need Two" for n in data)

@pytest.mark.asyncio
async def test_read_need_public(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    mock_matching_service_class = mocker.patch('app.services.matching_service.MatchingService')
    mock_matching_service_instance = mock_matching_service_class.return_value
    mock_matching_service_instance.reanalyze_all_matches.side_effect = MagicMock()
    mock_matching_service_instance.analyze_and_match.side_effect = MagicMock()

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    need_data = schemas.NeedCreate(title="Single Public Need", description="Single desc", num_volunteers_needed=1, format="in-person", contact_name="C3", contact_email="c3@e.com")
    created_need = await crud_need.create_need(db_session, need_data, owner_volunteer.id, mock_bg_tasks)
    
    response = client.get(f"/api/v1/needs/{created_need.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Single Public Need"
    assert data["id"] == created_need.id

    response = client.get("/api/v1/needs/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Need not found"

@pytest.mark.asyncio
async def test_update_need_authenticated_owner_and_check_matching(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    mock_background_tasks_for_api = MockBackgroundTasks()
    mock_background_tasks_for_api.db_session = db_session
    client.app.dependency_overrides[BackgroundTasks] = lambda: mock_background_tasks_for_api

    mock_matching_service_class = mocker.patch('app.services.matching_service.MatchingService')
    mock_matching_service_instance = mock_matching_service_class.return_value
    mock_matching_service_instance.reanalyze_all_matches.side_effect = MagicMock()
    mock_matching_service_instance.analyze_and_match.side_effect = MagicMock()

    mock_trigger_volunteer_matching = mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mock_trigger_volunteer_matching.side_effect = MagicMock()

    mock_trigger_need_matching = mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    try:
        crud_match.delete_all_matches(db_session)

        owner_email, owner_token = authenticated_volunteer_and_token
        owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
        assert owner_volunteer is not None

        mock_trigger_need_matching.side_effect = MagicMock()

        initial_need = await crud_need.create_need(db_session, schemas.NeedCreate(
            title="Initial Need",
            description="Initial description.",
            required_tasks="Old tasks",
            required_skills="Old skills",
            num_volunteers_needed=1,
            format="in-person",
            contact_name="Initial Contact",
            contact_email="initial@example.com"
        ), owner_volunteer.id, mock_background_tasks_for_api)
        assert initial_need is not None
        
        mock_trigger_need_matching.side_effect = MagicMock()

        updated_matchable_volunteer_data = schemas.VolunteerCreate(
            name="Updated Matchable Volunteer",
            email="updated_matchable@example.com",
            password="securepassword",
            skills="Event Planning, Coordination",
            volunteer_interests="Community Events, Organizing"
        )
        
        updated_matchable_volunteer = await crud_volunteer.create_volunteer(db_session, updated_matchable_volunteer_data, mock_background_tasks_for_api)
        assert updated_matchable_volunteer is not None
        
        initial_matches = crud_match.get_matches_for_need(db_session, initial_need.id)
        assert not any(m.volunteer_id == updated_matchable_volunteer.id for m in initial_matches)

        def mock_analyze_need_update_side_effect(need_id: int):
            need_param = crud_need.get_need(db_session, need_id)
            all_volunteers_param = crud_volunteer.get_volunteers(db_session)

            if need_param and all_volunteers_param:
                crud_match.delete_matches_for_need(db_session, need_param.id)
                crud_match.create_match(
                    db_session,
                    updated_matchable_volunteer.id,
                    need_param.id,
                    "Volunteer's event planning and coordination skills match the updated need."
                )
        mock_trigger_need_matching.side_effect = mock_analyze_need_update_side_effect


        update_data = schemas.NeedCreate(
            title="Updated Community Event",
            description="Organize a large community event.",
            required_tasks="Event Logistics, Volunteer Coordination",
            required_skills="Event Planning, Coordination, Problem Solving",
            num_volunteers_needed=2,
            format="in-person",
            contact_name="New Contact",
            contact_email="new@example.com",
            contact_phone="111-222-3333"
        )

        response = client.put(
            f"/api/v1/needs/{initial_need.id}",
            json=update_data.model_dump(),
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        updated_need = response.json()
        assert updated_need["title"] == "Updated Community Event"
        assert updated_need["num_volunteers_needed"] == 2

        await mock_background_tasks_for_api.run_tasks()

        matches = crud_match.get_matches_for_need(db_session, initial_need.id)
        assert any(m.volunteer_id == updated_matchable_volunteer.id for m in matches)
        assert any("event planning" in m.match_details.lower() for m in matches)

    finally:
        client.app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_update_need_authenticated_not_owner(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    mock_matching_service_class = mocker.patch('app.services.matching_service.MatchingService')
    mock_matching_service_instance = mock_matching_service_class.return_value
    mock_matching_service_instance.reanalyze_all_matches.side_effect = MagicMock()
    mock_matching_service_instance.analyze_and_match.side_effect = MagicMock()

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    need_by_owner = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Owner's Need", description="Owned by test user", num_volunteers_needed=1, format="virtual", contact_name="Owner", contact_email="owner@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    assert need_by_owner is not None

    not_owner_email = "not_owner_needs@example.com"
    not_owner_password = "notownerpassword"
    not_owner_data = schemas.VolunteerCreate(name="Not Owner", email=not_owner_email, password=not_owner_password)
    
    not_owner_volunteer = await crud_volunteer.create_volunteer(db_session, not_owner_data, mock_bg_tasks)
    assert not_owner_volunteer is not None

    not_owner_token_response = client.post("/api/v1/login", data={"username": not_owner_email, "password": not_owner_password})
    assert not_owner_token_response.status_code == 200
    not_owner_token = not_owner_token_response.json()["access_token"]

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=not_owner_volunteer)

    update_data = schemas.NeedCreate(
        title="Attempted Update", 
        description="Should not update", 
        num_volunteers_needed=1, 
        format="in-person", 
        contact_name="Fail", 
        contact_email="fail@e.com"
    )

    response = client.put(
        f"/api/v1/needs/{need_by_owner.id}",
        json=update_data.model_dump(),
        headers={"Authorization": f"Bearer {not_owner_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_need_unauthenticated(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    mock_matching_service_class = mocker.patch('app.services.matching_service.MatchingService')
    mock_matching_service_instance = mock_matching_service_class.return_value
    mock_matching_service_instance.reanalyze_all_matches.side_effect = MagicMock()
    mock_matching_service_instance.analyze_and_match.side_effect = MagicMock()

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    need_by_owner = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Unauth Update Need", description="Owned by test user", num_volunteers_needed=1, format="virtual", contact_name="Owner", contact_email="owner2@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    assert need_by_owner is not None

    update_data = schemas.NeedCreate(
        title="Attempted Unauth Update", 
        description="Should not update", 
        num_volunteers_needed=1, 
        format="in-person", 
        contact_name="Fail", 
        contact_email="fail2@e.com"
    )

    response = client.put(f"/api/v1/needs/{need_by_owner.id}", json=update_data.model_dump())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_need_authenticated_owner(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, owner_token = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    mock_matching_service_class = mocker.patch('app.services.matching_service.MatchingService')
    mock_matching_service_instance = mock_matching_service_class.return_value
    mock_matching_service_instance.reanalyze_all_matches.side_effect = MagicMock()
    mock_matching_service_instance.analyze_and_match.side_effect = MagicMock()

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    need_to_delete = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Need to Delete", description="Will be deleted", num_volunteers_needed=1, format="virtual", contact_name="Del", contact_email="del@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    assert need_to_delete is not None

    crud_match.create_match(db_session, owner_volunteer.id, need_to_delete.id, "Dummy match for deletion test")
    assert len(crud_match.get_matches_for_need(db_session, need_to_delete.id)) == 1

    response = client.delete(
        f"/api/v1/needs/{need_to_delete.id}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 204

    assert crud_need.get_need(db_session, need_to_delete.id) is None

    assert len(crud_match.get_matches_for_need(db_session, need_to_delete.id)) == 0


@pytest.mark.asyncio
async def test_delete_need_authenticated_not_owner(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    mock_matching_service_class = mocker.patch('app.services.matching_service.MatchingService')
    mock_matching_service_instance = mock_matching_service_class.return_value
    mock_matching_service_instance.reanalyze_all_matches.side_effect = MagicMock()
    mock_matching_service_instance.analyze_and_match.side_effect = MagicMock()

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    need_by_owner = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Owner's Need for Delete", description="Owned by test user", num_volunteers_needed=1, format="virtual", contact_name="Owner", contact_email="owner_del@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    assert need_by_owner is not None

    not_owner_email = "not_owner_delete_needs@example.com"
    not_owner_password = "notownerdeletepassword"
    not_owner_data = schemas.VolunteerCreate(name="Not Owner Del", email=not_owner_email, password=not_owner_password)
    not_owner_volunteer = await crud_volunteer.create_volunteer(db_session, not_owner_data, mock_bg_tasks)
    assert not_owner_volunteer is not None

    not_owner_token_response = client.post("/api/v1/login", data={"username": not_owner_email, "password": not_owner_password})
    assert not_owner_token_response.status_code == 200
    not_owner_token = not_owner_token_response.json()["access_token"]

    mocker.patch('app.dependencies.get_current_active_volunteer', return_value=not_owner_volunteer)

    response = client.delete(
        f"/api/v1/needs/{need_by_owner.id}",
        headers={"Authorization": f"Bearer {not_owner_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_need_unauthenticated(client: TestClient, db_session: Session, authenticated_volunteer_and_token, mocker):
    owner_email, _ = authenticated_volunteer_and_token
    owner_volunteer = crud_volunteer.get_volunteer_by_email(db_session, owner_email)
    assert owner_volunteer is not None

    mock_matching_service_class = mocker.patch('app.services.matching_service.MatchingService')
    mock_matching_service_instance = mock_matching_service_class.return_value
    mock_matching_service_instance.reanalyze_all_matches.side_effect = MagicMock()
    mock_matching_service_instance.analyze_and_match.side_effect = MagicMock()

    mocker.patch('app.background_tasks.match_handlers.trigger_volunteer_matching')
    mocker.patch('app.background_tasks.match_handlers.trigger_need_matching')

    mock_bg_tasks = MockBackgroundTasks()
    mock_bg_tasks.db_session = db_session

    need_to_delete = await crud_need.create_need(db_session, schemas.NeedCreate(
        title="Unauth Delete Need", description="Will be deleted", num_volunteers_needed=1, format="virtual", contact_name="Unauth", contact_email="unauth@e.com"
    ), owner_volunteer.id, mock_bg_tasks)
    assert need_to_delete is not None

    response = client.delete(f"/api/v1/needs/{need_to_delete.id}")
    assert response.status_code == 401
