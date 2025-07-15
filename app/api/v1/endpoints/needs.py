# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas import schemas
from app.crud import crud_need
from app.db.database import get_db
from app.dependencies import get_current_active_volunteer 
from app.db.models import Volunteer 

router = APIRouter(
    prefix="/needs",
    tags=["Needs"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Need, status_code=status.HTTP_201_CREATED)
async def create_need(
    need: schemas.NeedCreate,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer),
    db: Session = Depends(get_db)
):
    """
    Creates a new need associated with the authenticated volunteer.
    """
    # Pass the owner_id (current_volunteer.id) to the CRUD function
    return await crud_need.create_need(db=db, need=need, owner_id=current_volunteer.id)

@router.get("/", response_model=List[schemas.Need])
def read_needs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieves a list of all needs. (Publicly accessible)
    """
    needs = crud_need.get_needs(db, skip=skip, limit=limit)
    return needs

@router.get("/{need_id}", response_model=schemas.Need)
def read_need(need_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single need by ID. (Publicly accessible)
    """
    db_need = crud_need.get_need(db, need_id=need_id)
    if db_need is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need not found"
        )
    return db_need

@router.put("/{need_id}", response_model=schemas.Need)
async def update_need(
    need_id: int,
    need: schemas.NeedCreate,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer),
    db: Session = Depends(get_db)
):
    """
    Updates an existing need. Only the owner can update their need.
    """
    db_need = await crud_need.update_need(db, need_id, need, current_volunteer.id)
    if db_need is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need not found or you don't have permission to update it"
        )
    return db_need

@router.delete("/{need_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_need(
    need_id: int,
    current_volunteer: Volunteer = Depends(get_current_active_volunteer),
    db: Session = Depends(get_db)
):
    """
    Deletes a need. Only the owner can delete their need.
    """
    success = crud_need.delete_need(db, need_id, current_volunteer.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need not found or you don't have permission to delete it"
        )
    return {"message": "Need deleted successfully"}