from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app import models, schemas
from app.database import engine, get_db, Base
from app.config import settings

# Use lifespan for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Attempting to connect to database and create tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created or already exist.")
    except OperationalError as e:
        print(f"Error connecting to database or creating tables: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during database startup: {e}")
    yield
    # No shutdown logic needed for this simple case yet, but it would go here.

app = FastAPI(
    title="getVolunteer Backend API",
    description="API for connecting volunteers with needs.",
    version="0.1.0",
    lifespan=lifespan # Assign the lifespan context manager
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