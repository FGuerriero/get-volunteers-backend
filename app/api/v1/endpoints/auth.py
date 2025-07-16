"""
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Tue Jul 08 2025
# SPDX-License-Identifier: MIT
"""

from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import crud_volunteer
from app.db import models
from app.db.database import get_db
from app.dependencies import create_access_token, get_current_active_volunteer
from app.schemas import schemas
from app.utils.security import verify_password

router = APIRouter(
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
)


@router.post("/register", response_model=schemas.Volunteer, status_code=status.HTTP_201_CREATED)
async def register_volunteer(
    volunteer: schemas.VolunteerCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Registers a new Volunteer (who is also the user).
    """
    db_volunteer = crud_volunteer.get_volunteer_by_email(db, email=volunteer.email)
    if db_volunteer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    return await crud_volunteer.create_volunteer(
        db, volunteer, background_tasks
    )


@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Authenticates a volunteer and returns an access token.
    """
    volunteer = crud_volunteer.get_volunteer_by_email(db, email=form_data.username)
    if not volunteer or not verify_password(form_data.password, volunteer.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not volunteer.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive volunteer")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(data={"sub": volunteer.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/volunteers/me/", response_model=schemas.Volunteer)
async def read_volunteers_me(current_volunteer: models.Volunteer = Depends(get_current_active_volunteer)):
    """
    Retrieves the current authenticated volunteer's profile.
    """
    return current_volunteer
