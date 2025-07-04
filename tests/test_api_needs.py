from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_create_need(client: TestClient, db_session: Session):
    response = client.post(
        "/api/v1/needs/",
        json={
            "title": "API Test Need",
            "description": "Need description for API test",
            "required_tasks": "Task 1, Task 2",
            "required_skills": "Skill A, Skill B",
            "num_volunteers_needed": 3,
            "format": "virtual",
            "location_details": None,
            "contact_name": "API Contact",
            "contact_email": "api_contact@example.com",
            "contact_phone": "999-888-7777",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "API Test Need"
    assert data["description"] == "Need description for API test"
    assert data["num_volunteers_needed"] == 3
    assert data["format"] == "virtual"
    assert "id" in data

def test_read_needs(client: TestClient, db_session: Session):
    client.post(
        "/api/v1/needs/",
        json={
            "title": "Need One",
            "description": "Desc One",
            "num_volunteers_needed": 1,
            "format": "in-person",
            "contact_name": "C1",
            "contact_email": "c1@e.com",
        },
    )
    client.post(
        "/api/v1/needs/",
        json={
            "title": "Need Two",
            "description": "Desc Two",
            "num_volunteers_needed": 2,
            "format": "virtual",
            "contact_name": "C2",
            "contact_email": "c2@e.com",
        },
    )

    response = client.get("/api/v1/needs/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2 # Could be more if other tests added
    assert any(n["title"] == "Need One" for n in data)
    assert any(n["title"] == "Need Two" for n in data)

    # Test skip and limit
    response = client.get("/api/v1/needs/?skip=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

def test_read_need(client: TestClient, db_session: Session):
    create_response = client.post(
        "/api/v1/needs/",
        json={
            "title": "Single Need",
            "description": "Single need desc",
            "num_volunteers_needed": 1,
            "format": "virtual",
            "contact_name": "Single C",
            "contact_email": "single@e.com",
        },
    )
    need_id = create_response.json()["id"]

    response = client.get(f"/api/v1/needs/{need_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Single Need"
    assert data["id"] == need_id

    # Test not found
    response = client.get("/api/v1/needs/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Need not found"

def test_update_need(client: TestClient, db_session: Session):
    create_response = client.post(
        "/api/v1/needs/",
        json={
            "title": "Old Need Title",
            "description": "Old Need Desc",
            "num_volunteers_needed": 1,
            "format": "virtual",
            "contact_name": "Old C",
            "contact_email": "old@e.com",
        },
    )
    need_id = create_response.json()["id"]

    update_data = {
        "title": "Updated Need Title",
        "description": "Updated Need Desc",
        "num_volunteers_needed": 2,
        "format": "in-person",
        "contact_name": "Old C",
        "contact_email": "old@e.com",
    }
    response = client.put(f"/api/v1/needs/{need_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Need Title"
    assert data["description"] == "Updated Need Desc"
    assert data["num_volunteers_needed"] == 2
    assert data["format"] == "in-person"
    assert data["id"] == need_id

    # Test update non-existent
    response = client.put("/api/v1/needs/99999", json=update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Need not found"

def test_delete_need(client: TestClient, db_session: Session):
    create_response = client.post(
        "/api/v1/needs/",
        json={
            "title": "Delete This Need",
            "description": "Desc to delete",
            "num_volunteers_needed": 1,
            "format": "virtual",
            "contact_name": "Del C",
            "contact_email": "del@e.com",
        },
    )
    need_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/needs/{need_id}")
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/api/v1/needs/{need_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Need not found"

    # Test delete non-existent
    response = client.delete("/api/v1/needs/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Need not found"