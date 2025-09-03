# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_volunteer
from app.db.database import get_db
from app.db.models import Volunteer
from app.dependencies import get_current_active_volunteer, get_current_manager
from app.schemas import schemas

router = APIRouter(
    prefix="/volunteers",
    tags=["Volunteers"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.Volunteer])
def read_volunteers(skip: int = 0, limit: int = 100, current_manager: Volunteer = Depends(get_current_manager), db: Session = Depends(get_db)):
    """
    Retrieves a list of all volunteer profiles. (Manager access required)
    """
    volunteers = crud_volunteer.get_volunteers(db, skip=skip, limit=limit)
    return volunteers


@router.get("/{volunteer_id}", response_model=schemas.Volunteer)
def read_volunteer(volunteer_id: int, current_manager: Volunteer = Depends(get_current_manager), db: Session = Depends(get_db)):
    """
    Retrieves a single volunteer profile by ID. (Manager access required)
    """
    db_volunteer = crud_volunteer.get_volunteer(db, volunteer_id=volunteer_id)
    if db_volunteer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found")
    return db_volunteer


@router.put("/{volunteer_id}", response_model=schemas.Volunteer)
async def update_volunteer(
    volunteer_id: int,
    volunteer: schemas.VolunteerCreate,
    background_tasks: BackgroundTasks,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer),
    db: Session = Depends(get_db),
):
    """
    Updates an existing volunteer profile. Only the owner can update their profile.
    """
    if volunteer_id != current_volunteer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own volunteer profile."
        )

    db_volunteer = await crud_volunteer.update_volunteer(db, volunteer_id, volunteer, background_tasks)
    if db_volunteer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volunteer not found or an unexpected error occurred during update.",
        )
    return db_volunteer


@router.delete("/{volunteer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_volunteer(
    volunteer_id: int,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer),
    db: Session = Depends(get_db),
):
    """
    Deletes a volunteer profile. Only the owner can delete their profile.
    """
    if volunteer_id != current_volunteer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own volunteer profile."
        )

    success = crud_volunteer.delete_volunteer(db, volunteer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volunteer not found or an unexpected error occurred during deletion.",
        )
    return {"message": "Volunteer deleted successfully"}
