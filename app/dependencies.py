'''
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Tue Jul 08 2025
# SPDX-License-Identifier: MIT
'''

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.schemas import schemas
from app.db.database import get_db
from app.crud import crud_volunteer 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")

def verify_password(plain_password: str, password: str) -> bool:
    """
    Verifies a plain password against a hashed password.
    """
    return pwd_context.verify(plain_password, password)

def get_password_hash(password: str) -> str:
    """
    Hashes a plain password.
    """
    return pwd_context.hash(password)

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

def get_current_volunteer(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.Volunteer:
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

def get_current_active_volunteer(current_volunteer: models.Volunteer = Depends(get_current_volunteer)) -> models.Volunteer:
    """
    FastAPI dependency to get the current authenticated and active volunteer.
    """
    if not current_volunteer.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive volunteer")
    return current_volunteer