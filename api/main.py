"""
FastAPI backend for StudyWise AI
Main application entry point
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from api.routers import chat, flashcards, documents, users, system, admin, simple_auth
from api.core.config import get_settings
from api.core.dependencies import get_study_assistant
from api.core.exceptions import StudyWiseAPIException, api_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Initialize services on startup, cleanup on shutdown.
    """
    # TODO: Initialize StudyAssistant and other services
    yield
    # TODO: Cleanup resources


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI app instance
    """
    settings = get_settings()

    app = FastAPI(
        title="StudyWise AI API",
        description="Conversational RAG and Flashcard Learning Platform",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Add exception handlers
    app.add_exception_handler(StudyWiseAPIException, api_exception_handler)

    # Root and health endpoints at app level
    @app.get("/")
    async def root() -> dict:
        """Root endpoint."""
        return {
            "message": "StudyWise AI API",
            "version": "1.0.0",
            "status": "running"
        }

    @app.get("/health")
    async def health_check() -> dict:
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "service": "StudyWise AI API"
        }

    # Include routers
    app.include_router(simple_auth.router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
    app.include_router(flashcards.router, prefix="/api/v1/flashcards", tags=["flashcards"])
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
