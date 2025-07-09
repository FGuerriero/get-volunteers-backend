# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

.PHONY: install test coverage format lint run venv

# Python venv activation for Windows environment
activate-venv/Win: 
	.\.venv\Scripts\Activate.ps1

# Install project dependencies
install:
	pip install -r requirements.txt

# Run all tests
test:
	pytest

# Run tests and generate coverage report
coverage:
	pytest --cov=app --cov-report=term-missing --cov-report=html

# Format code using Ruff
format:
	ruff format .

# Lint code using Ruff and fix auto-fixable issues
lint:
	ruff check . --fix

# Run the FastAPI application with auto-reload
run:
	uvicorn app.app:app --reload

# Activate the Python virtual environment
# Use 'make venv'
# For Windows PowerShell/CMD:
# make sure to run 'make venv' from within your PowerShell/CMD session
# or use 'source ./.venv/Scripts/activate' if you have Git Bash/WSL.
venv:
	@echo   Activating virtual environment...
	@echo    For Windows Command Prompt/PowerShell, run: '.\.venv\Scripts\Activate.ps1' or '.\.venv\Scripts\activate'
	@echo    For Git Bash/WSL/Linux/macOS, run: source './.venv/bin/activate'
	@echo    This 'make venv' command itself cannot activate the environment for the current shell session.

# Alembic Migration Commands
# Create a new migration script (e.g., make migrate-new message="Add users table")
migrate-new:
	alembic revision --autogenerate -m "$(message)"

# Apply all pending migrations to the database
migrate-up:
	alembic upgrade head

# Revert the last migration (use with caution!)
migrate-down:
	alembic downgrade -1