#!/usr/bin/env python3
"""
Simple StudyWise AI FastAPI Backend for testing frontend connection
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Optional
import uvicorn
import uuid

# Simple in-memory storage for uploaded documents (for demo purposes)
uploaded_documents = []

app = FastAPI(
    title="StudyWise AI API (Simple)",
    description="Simple backend for testing frontend connection",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:8082",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:8082"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "StudyWise AI API (Simple Mode)",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "StudyWise AI API"
    }

@app.get("/api/v1/system/health")
async def system_health():
    return {
        "status": "healthy",
        "service": "StudyWise AI API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/documents")
async def list_documents():
    # Return both mock and uploaded documents
    mock_documents = [
        {
            "document_id": "doc-1",
            "title": "Sample Document 1",
            "file_name": "sample1.pdf",
            "file_size": 1024000,
            "file_type": ".pdf",
            "status": "completed",
            "created_at": "2025-01-16T10:00:00Z",
            "chunks_count": 5,
            "flashcards_count": 10
        },
        {
            "document_id": "doc-2", 
            "title": "Sample Document 2",
            "file_name": "sample2.txt",
            "file_size": 512000,
            "file_type": ".txt",
            "status": "completed",
            "created_at": "2025-01-16T11:00:00Z",
            "chunks_count": 3,
            "flashcards_count": 6
        }
    ]
    
    # Combine with uploaded documents
    all_documents = mock_documents + uploaded_documents
    
    return {
        "documents": all_documents,
        "total": len(all_documents),
        "skip": 0,
        "limit": 20,
        "has_next": False
    }

@app.get("/api/v1/flashcards")
async def list_flashcards():
    # Return mock flashcards for testing
    return {
        "flashcards": [
            {
                "id": "fc-1",
                "question": "What is machine learning?",
                "answer": "Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed.",
                "tags": ["ai", "ml"],
                "level": "beginner",
                "created_at": "2025-01-16T10:00:00Z",
                "user_id": "user-123"
            },
            {
                "id": "fc-2",
                "question": "What is a neural network?",
                "answer": "A neural network is a computing system inspired by biological neural networks that learns to perform tasks by considering examples.",
                "tags": ["ai", "neural-networks"],
                "level": "intermediate", 
                "created_at": "2025-01-16T10:30:00Z",
                "user_id": "user-123"
            }
        ],
        "total": 2,
        "has_more": False
    }

@app.get("/api/v1/flashcards/due-today")
async def flashcards_due_today():
    # Return mock due flashcards
    return {
        "flashcards": [
            {
                "id": "fc-1",
                "question": "What is machine learning?",
                "answer": "Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed.",
                "tags": ["ai", "ml"],
                "level": "beginner",
                "created_at": "2025-01-16T10:00:00Z",
                "user_id": "user-123"
            }
        ],
        "total": 1,
        "has_more": False
    }

@app.get("/api/v1/users/{user_id}/stats")
async def user_stats(user_id: str):
    return {
        "total_documents": 2,
        "total_flashcards": 15,
        "cards_due_today": 5,
        "study_streak": 3,
        "total_reviews": 45,
        "accuracy_rate": 0.85
    }

@app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    tags: str = Form(""),
    generate_flashcards: bool = Form(True)
):
    """
    Simple document upload endpoint for testing.
    Accepts files and returns a mock successful response.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a name")
    
    allowed_extensions = ['.pdf', '.txt', '.md', '.docx']
    file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    if f'.{file_extension}' not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Read file content to simulate processing
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File appears to be empty")
    
    # Generate mock response
    document_id = str(uuid.uuid4())
    document_title = title or file.filename
    file_size = len(content)
    
    # Simulate flashcard generation
    flashcards_created = 5 if generate_flashcards else 0
    
    # Store the uploaded document
    uploaded_doc = {
        "document_id": document_id,
        "title": document_title,
        "file_name": file.filename,
        "file_size": file_size,
        "file_type": f".{file_extension}",
        "status": "completed",
        "created_at": datetime.now().isoformat(),
        "chunks_count": 3,
        "flashcards_count": flashcards_created
    }
    uploaded_documents.append(uploaded_doc)
    
    return {
        "document_id": document_id,
        "title": document_title,
        "status": "success",
        "message": f"Document '{document_title}' processed successfully",
        "file_type": f".{file_extension}",
        "file_size": file_size,
        "chunks_created": 3,
        "flashcards_created": flashcards_created,
        "processing_time": 2.5,
        "supabase_id": document_id,
        "weaviate_id": f"weaviate_{document_id}",
        "errors": []
    }

if __name__ == "__main__":
    print("🚀 Starting Simple StudyWise AI API...")
    print("   Server: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    
    uvicorn.run(
        "simple_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )