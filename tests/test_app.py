# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import os
import pytest
from unittest.mock import patch

def test_app_startup_production_mode(capsys):
    """Test app startup message in production mode"""
    with patch.dict(os.environ, {"TESTING": "0"}, clear=False):
        from app.app import lifespan, app
        
        # Simulate lifespan startup
        import asyncio
        async def test_lifespan():
            async with lifespan(app):
                pass
        
        asyncio.run(test_lifespan())
        
        captured = capsys.readouterr()
        assert "FastAPI application starting up. Database migrations are managed by Alembic." in captured.out

def test_database_url_production_mode():
    """Test database URL selection in production mode"""
    with patch.dict(os.environ, {"TESTING": "0"}, clear=False):
        # Force reimport to test the condition
        import importlib
        import app.db.database
        importlib.reload(app.db.database)
        
        from app.config import settings
        assert app.db.database.SQLALCHEMY_DATABASE_URL == settings.database_url