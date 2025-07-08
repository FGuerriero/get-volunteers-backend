# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_volunteer
from app.db.database import get_db
from app.schemas import schemas

router = APIRouter(
    prefix="/volunteers",
    tags=["Volunteers"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=schemas.Volunteer, status_code=status.HTTP_201_CREATED)
def create_volunteer(volunteer: schemas.VolunteerCreate, db: Session = Depends(get_db)):
    db_volunteer = crud_volunteer.get_volunteer_by_email(db, email=volunteer.email)
    if db_volunteer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    return crud_volunteer.create_volunteer(db=db, volunteer=volunteer)


@router.get("/", response_model=List[schemas.Volunteer])
def read_volunteers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    volunteers = crud_volunteer.get_volunteers(db, skip=skip, limit=limit)
    return volunteers


@router.get("/{volunteer_id}", response_model=schemas.Volunteer)
def read_volunteer(volunteer_id: int, db: Session = Depends(get_db)):
    db_volunteer = crud_volunteer.get_volunteer(db, volunteer_id=volunteer_id)
    if db_volunteer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found"
        )
    return db_volunteer


@router.put("/{volunteer_id}", response_model=schemas.Volunteer)
def update_volunteer(
    volunteer_id: int, volunteer: schemas.VolunteerCreate, db: Session = Depends(get_db)
):
    db_volunteer = crud_volunteer.update_volunteer(db, volunteer_id, volunteer)
    if db_volunteer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found"
        )
    return db_volunteer


@router.delete("/{volunteer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_volunteer(volunteer_id: int, db: Session = Depends(get_db)):
    success = crud_volunteer.delete_volunteer(db, volunteer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found"
        )
    return {"message": "Volunteer deleted successfully"}
