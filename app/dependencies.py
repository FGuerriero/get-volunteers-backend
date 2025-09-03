"""
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Tue Jul 08 2025
# SPDX-License-Identifier: MIT
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import crud_volunteer
from app.db.database import get_db
from app.db.models import Volunteer
from app.schemas import schemas


def verify_token(token: str, credentials_exception: HTTPException) -> schemas.TokenData:
    """
    Verifies a JWT token and returns the token data.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    return token_data


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def get_current_volunteer(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Volunteer:
    """
    FastAPI dependency to get the current authenticated volunteer.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_token(token, credentials_exception)
    volunteer = crud_volunteer.get_volunteer_by_email(db, email=token_data.email)
    if volunteer is None:
        raise credentials_exception
    return volunteer


def get_current_active_volunteer(current_volunteer: Volunteer = Depends(get_current_volunteer)) -> Volunteer:
    """
    FastAPI dependency to get the current authenticated and active volunteer.
    """
    if not current_volunteer.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive volunteer")
    return current_volunteer


def get_current_manager(current_volunteer: Volunteer = Depends(get_current_active_volunteer)) -> Volunteer:
    """
    FastAPI dependency to get the current authenticated manager.
    """
    if not current_volunteer.is_manager:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager access required")
    return current_volunteer
