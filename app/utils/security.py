"""
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Wed Jul 09 2025
# SPDX-License-Identifier: MIT
"""

from passlib.context import CryptContext


def get_password_hash(password: str) -> str:
    """
    Hashes a plain password.
    """
    return pwd_context.hash(password)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, password: str) -> bool:
    """
    Verifies a plain password against a hashed password.
    """
    return pwd_context.verify(plain_password, password)
