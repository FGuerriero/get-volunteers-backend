# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_volunteer
from app.db.database import get_db
from app.db.models import Volunteer
from app.dependencies import get_current_active_volunteer
from app.schemas import schemas

router = APIRouter(
    prefix="/volunteers",
    tags=["Volunteers"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Volunteer, status_code=status.HTTP_201_CREATED)
def create_volunteer(
    volunteer: schemas.VolunteerCreate,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer), 
    db: Session = Depends(get_db)
):
    """
    Creates a new volunteer profile. Note: In this simplified model,
    the 'create_volunteer' endpoint is primarily for initial registration.
    Subsequent updates should use the PUT endpoint.
    """
    db_volunteer = crud_volunteer.get_volunteer_by_email(db, email=volunteer.email)
    if db_volunteer:
        if db_volunteer.id == current_volunteer.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Volunteer profile with this email already exists for you. Use PUT to update."
            )
        else:
            # If the email belongs to another volunteer, it's a conflict.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered by another volunteer."
            )
    
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Volunteer profiles are created via the /register endpoint."
    )


@router.get("/", response_model=List[schemas.Volunteer])
def read_volunteers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieves a list of all volunteer profiles. (Publicly accessible)
    """
    volunteers = crud_volunteer.get_volunteers(db, skip=skip, limit=limit)
    return volunteers

@router.get("/{volunteer_id}", response_model=schemas.Volunteer)
def read_volunteer(volunteer_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single volunteer profile by ID. (Publicly accessible)
    """
    db_volunteer = crud_volunteer.get_volunteer(db, volunteer_id=volunteer_id)
    if db_volunteer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volunteer not found"
        )
    return db_volunteer

@router.put("/{volunteer_id}", response_model=schemas.Volunteer)
def update_volunteer(
    volunteer_id: int,
    volunteer: schemas.VolunteerCreate,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer), 
    db: Session = Depends(get_db)
):
    """
    Updates an existing volunteer profile. Only the owner can update their profile.
    """
    if volunteer_id != current_volunteer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own volunteer profile."
        )
    
    db_volunteer = crud_volunteer.update_volunteer(db, volunteer_id, volunteer)
    if db_volunteer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, # Should not happen if ID matches current_volunteer.id
            detail="Volunteer not found or an unexpected error occurred during update."
        )
    return db_volunteer

@router.delete("/{volunteer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_volunteer(
    volunteer_id: int,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer), 
    db: Session = Depends(get_db)
):
    """
    Deletes a volunteer profile. Only the owner can delete their profile.
    """
    if volunteer_id != current_volunteer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own volunteer profile."
        )

    success = crud_volunteer.delete_volunteer(db, volunteer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volunteer not found or an unexpected error occurred during deletion."
        )
    return {"message": "Volunteer deleted successfully"}