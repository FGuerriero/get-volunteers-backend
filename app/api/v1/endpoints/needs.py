# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_need
from app.db.database import get_db
from app.db.models import Volunteer
from app.dependencies import get_current_active_volunteer, get_current_manager
from app.schemas import schemas

router = APIRouter(
    prefix="/needs",
    tags=["Needs"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=schemas.Need, status_code=status.HTTP_201_CREATED)
async def create_need(
    need: schemas.NeedCreate,
    background_tasks: BackgroundTasks,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer),
    db: Session = Depends(get_db),
):
    """
    Creates a new need associated with the authenticated volunteer.
    """
    return await crud_need.create_need(
        db=db, need=need, owner_id=current_volunteer.id, background_tasks=background_tasks
    )


@router.get("/", response_model=List[schemas.Need])
def read_needs(
    current_volunteer: Volunteer = Depends(get_current_active_volunteer),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Retrieves needs. Managers see all needs, volunteers see only their own.
    """
    if current_volunteer.is_manager:
        needs = crud_need.get_needs(db, skip=skip, limit=limit)
    else:
        needs = crud_need.get_needs_by_owner(db, owner_id=current_volunteer.id, skip=skip, limit=limit)
    return needs


@router.get("/{need_id}", response_model=schemas.Need)
def read_need(
    need_id: int,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer),
    db: Session = Depends(get_db)
):
    """
    Retrieves a single need by ID. Managers can access any need, volunteers only their own.
    """
    db_need = crud_need.get_need(db, need_id=need_id)
    if db_need is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Need not found")
    
    # Check access permissions
    if not current_volunteer.is_manager and db_need.owner_id != current_volunteer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return db_need


@router.put("/{need_id}", response_model=schemas.Need)
async def update_need(
    need_id: int,
    need: schemas.NeedCreate,
    background_tasks: BackgroundTasks,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer),
    db: Session = Depends(get_db),
):
    """
    Updates an existing need. Managers can update any need, volunteers only their own.
    """
    # Check if need exists and get access permissions
    db_need = crud_need.get_need(db, need_id=need_id)
    if db_need is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Need not found")
    
    # Check permissions
    if not current_volunteer.is_manager and db_need.owner_id != current_volunteer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Update the need
    updated_need = await crud_need.update_need(db, need_id, need, current_volunteer.id, background_tasks, is_manager=current_volunteer.is_manager)
    return updated_need


@router.delete("/{need_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_need(
    need_id: int,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer),
    db: Session = Depends(get_db),
):
    """
    Deletes a need. Managers can delete any need, volunteers only their own.
    """
    # Check if need exists and get access permissions
    db_need = crud_need.get_need(db, need_id=need_id)
    if db_need is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Need not found")
    
    # Check permissions
    if not current_volunteer.is_manager and db_need.owner_id != current_volunteer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Delete the need
    success = crud_need.delete_need(db, need_id, current_volunteer.id, is_manager=current_volunteer.is_manager)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need not found or an unexpected error occurred during deletion",
        )
    return {"message": "Need deleted successfully"}
