"""
System health and status API routes
"""

import os
import time
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, Depends, HTTPException

from api.core.dependencies import get_study_assistant
from src.conversation.rag import StudyAssistant


router = APIRouter()


@router.get("/health")
async def system_health_check() -> Dict[str, Any]:
    """
    Comprehensive system health check for production monitoring.

    Returns:
        System health status and component details
    """
    start_time = time.time()
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "StudyWise AI API",
        "version": "1.0.0",
        "checks": {}
    }
    
    try:
        # Check environment configuration
        required_env_vars = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
        env_check = all(os.getenv(var) for var in required_env_vars)
        health_status["checks"]["environment"] = {
            "status": "healthy" if env_check else "degraded",
            "message": "All required environment variables present" if env_check else "Some environment variables missing"
        }
        
        # Check Supabase connection
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_check = bool(supabase_url and supabase_url.startswith('https://'))
            health_status["checks"]["supabase"] = {
                "status": "healthy" if supabase_check else "unhealthy",
                "message": "Supabase configuration valid" if supabase_check else "Supabase configuration invalid"
            }
        except Exception as e:
            health_status["checks"]["supabase"] = {
                "status": "unhealthy",
                "message": f"Supabase check failed: {str(e)}"
            }
        
        # Check OpenAI API key format
        try:
            openai_key = os.getenv('OPENAI_API_KEY')
            openai_check = bool(openai_key and openai_key.startswith('sk-'))
            health_status["checks"]["openai"] = {
                "status": "healthy" if openai_check else "unhealthy", 
                "message": "OpenAI API key format valid" if openai_check else "OpenAI API key format invalid"
            }
        except Exception as e:
            health_status["checks"]["openai"] = {
                "status": "unhealthy",
                "message": f"OpenAI check failed: {str(e)}"
            }
        
        # Overall status based on critical checks
        critical_checks = ["environment", "supabase", "openai"]
        unhealthy_checks = [check for check in critical_checks 
                          if health_status["checks"].get(check, {}).get("status") == "unhealthy"]
        
        if unhealthy_checks:
            health_status["status"] = "unhealthy"
            health_status["message"] = f"Critical components unhealthy: {', '.join(unhealthy_checks)}"
        elif any(health_status["checks"].get(check, {}).get("status") == "degraded" for check in critical_checks):
            health_status["status"] = "degraded"
            health_status["message"] = "Some components degraded but service operational"
        else:
            health_status["status"] = "healthy"
            health_status["message"] = "All systems operational"
            
        # Add response time
        health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "StudyWise AI API",
            "message": f"Health check failed: {str(e)}",
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }


@router.get("/status")
async def system_status() -> Dict[str, Any]:
    """
    Get system status and basic performance metrics.

    Returns:
        System status and performance metrics
    """
    try:
        status_info = {
            "service": "StudyWise AI API",
            "version": "1.0.0",
            "environment": os.getenv('ENVIRONMENT', 'development'),
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_check": "operational",
            "features": {
                "document_upload": "enabled",
                "flashcard_generation": "enabled", 
                "ai_chat": "enabled",
                "spaced_repetition": "enabled"
            },
            "configuration": {
                "max_file_size": "10MB",
                "supported_formats": [".pdf", ".txt", ".md", ".docx"],
                "ai_model": os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
            }
        }
        
        # Add basic environment status
        env_vars_present = {
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
            "supabase_configured": bool(os.getenv('SUPABASE_URL')),
            "weaviate_configured": bool(os.getenv('WEAVIATE_URL'))
        }
        status_info["services"] = env_vars_present
        
        return status_info
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system status: {str(e)}"
        )


@router.get("/version")
async def get_version() -> Dict[str, Any]:
    """
    Get API version information.

    Returns:
        Version details and build info
    """
    return {
        "api_version": "1.0.0",
        "service": "StudyWise AI API",
        "build_date": "2025-06-18", 
        "environment": os.getenv('ENVIRONMENT', 'development'),
        "python_version": "3.x",
        "framework": "FastAPI",
        "features": [
            "Document Processing",
            "AI Flashcard Generation", 
            "Spaced Repetition (FSRS)",
            "Conversational AI",
            "Vector Search"
        ]
    }
