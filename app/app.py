# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import auth, needs, volunteers


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("FastAPI application starting up. Database migrations are managed by Alembic.")
    yield
    print("FastAPI application shutting down.")


app = FastAPI(
    title="getVolunteer Backend API",
    description="API for connecting volunteers with needs.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(volunteers.router, prefix="/api/v1")
app.include_router(needs.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
