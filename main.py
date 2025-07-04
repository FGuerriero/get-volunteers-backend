from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.db import models
from app.db.database import engine, get_db, Base
from app.config import settings
from app.db.schema import schemas

# Use lifespan for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("FastAPI application starting up. Database migrations are managed by Alembic.")
    yield
    print("FastAPI application shutting down.")

app = FastAPI(
    title="getVolunteer Backend API",
    description="API for connecting volunteers with needs.",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to getVolunteer Backend API!"}

@app.get("/health")
async def health_check():
    try:
        db: Session = next(get_db())
        db.execute("SELECT 1")
        return {"status": "ok", "database_connection": "successful"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failed: {e}"
        )