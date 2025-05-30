#!/usr/bin/env python3
"""
Start StudyWise AI FastAPI Backend
"""

import uvicorn
from api.main import app, get_settings

if __name__ == "__main__":
    settings = get_settings()

    print("🚀 Starting StudyWise AI API...")
    print(f"   Server: http://{settings.host}:{settings.port}")
    print(f"   Docs: http://{settings.host}:{settings.port}/docs")
    print(f"   Debug: {settings.debug}")

    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
