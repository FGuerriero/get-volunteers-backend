# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import pytest
from unittest.mock import MagicMock
from app.db.database import get_db, SessionLocal # Import SessionLocal

def test_get_db_closes_session(mocker):
    """
    Tests that the database session is properly closed by the get_db dependency,
    even if an exception occurs.
    """
    
    mock_db_session = MagicMock()

    mocker.patch('app.db.database.SessionLocal', return_value=mock_db_session)

    db_generator = get_db()

    db = next(db_generator)

    assert db is mock_db_session

    with pytest.raises(ValueError):
        db_generator.throw(ValueError("Simulated error during dependency usage"))

    # Assert that db.close() was called on the mock session
    mock_db_session.close.assert_called_once()