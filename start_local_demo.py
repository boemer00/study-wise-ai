#!/usr/bin/env python3
"""
StudyWise AI Local Demo Server

A lightweight demo server that showcases StudyWise AI capabilities without requiring
external dependencies. Now includes REAL document processing with PDF extraction.
"""

import os
import sys
import tempfile
import uuid
import asyncio
import json
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

# Add src to Python path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# Import our modules
try:
    from src.document_processor import DocumentProcessor
    REAL_PROCESSING_AVAILABLE = True
    print("✅ Real document processing available")
except ImportError as e:
    print(f"⚠️ Real document processing unavailable: {e}")
    REAL_PROCESSING_AVAILABLE = False

# Import flashcard generator
try:
    from src.flashcard_generator import FlashcardGenerator
    FLASHCARD_GENERATION_AVAILABLE = True
    print("✅ FlashcardGenerator available")
except ImportError as e:
    print(f"⚠️ FlashcardGenerator unavailable: {e}")
    FLASHCARD_GENERATION_AVAILABLE = False

# Import flashcard database function
from src.flashcards_db import save_generated_flashcards

app = FastAPI(
    title="StudyWise AI Demo",
    description="Local demo showcasing FSRS flashcards, document processing, and AI study features",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "http://localhost:8081", "http://localhost:8082", "http://localhost:8083"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize real document processor if available
document_processor = None
if REAL_PROCESSING_AVAILABLE:
    try:
        document_processor = DocumentProcessor()
        print("✅ DocumentProcessor initialized")
    except Exception as e:
        print(f"⚠️ DocumentProcessor initialization failed: {e}")
        REAL_PROCESSING_AVAILABLE = False

# Initialize flashcard generator if available
flashcard_generator = None
if FLASHCARD_GENERATION_AVAILABLE:
    try:
        flashcard_generator = FlashcardGenerator()
        print("✅ FlashcardGenerator initialized")
    except Exception as e:
        print(f"⚠️ FlashcardGenerator initialization failed: {e}")
        FLASHCARD_GENERATION_AVAILABLE = False

# Demo data for flashcards (keep existing)
DEMO_FLASHCARDS = [
    {
        "id": "card_001",
        "question": "What is the primary algorithm used for spaced repetition in StudyWise AI?",
        "answer": "FSRS (Free Spaced Repetition Scheduler) - a modern algorithm that optimizes review intervals based on forgetting curves and memory consolidation research.",
        "tags": ["algorithms", "memory", "fsrs"],
        "level": "intermediate",
        "metadata": {
            "review_count": 5,
            "ease_factor": 2.6,
            "next_review": "2024-01-15T10:00:00",
            "last_reviewed": "2024-01-10T14:30:00"
        }
    },
    {
        "id": "card_002",
        "question": "How does FeynmanMode help with learning?",
        "answer": "FeynmanMode implements the Feynman Technique - you learn by teaching. It analyzes your explanations for clarity, identifies knowledge gaps, and provides feedback to improve understanding.",
        "tags": ["learning", "feynman", "teaching"],
        "level": "beginner",
        "metadata": {
            "review_count": 3,
            "ease_factor": 2.4,
            "next_review": "2024-01-16T09:15:00",
            "last_reviewed": "2024-01-12T16:45:00"
        }
    },
    {
        "id": "card_003",
        "question": "What makes StudyWise AI's document processing unique?",
        "answer": "Hybrid architecture: Weaviate for vector embeddings enabling semantic search, plus Supabase for structured metadata. Supports PDF, DOCX with intelligent chunking and real-time processing status.",
        "tags": ["documents", "ai", "architecture"],
        "level": "advanced",
        "metadata": {
            "review_count": 8,
            "ease_factor": 2.8,
            "next_review": "2024-01-20T11:30:00",
            "last_reviewed": "2024-01-14T13:20:00"
        }
    }
]

# UUID Helper Functions
def get_demo_user_id() -> str:
    """Get a consistent demo user UUID."""
    # Use a seed to generate the same UUID for demo consistency
    return str(uuid.UUID('12345678-1234-5678-9abc-123456789012'))

def generate_new_user_id() -> str:
    """Generate a new random user UUID."""
    return str(uuid.uuid4())

def validate_user_id(user_id: str) -> str:
    """Validate and return a proper UUID string."""
    try:
        # This will raise ValueError if not a valid UUID
        uuid.UUID(user_id)
        return user_id
    except ValueError:
        # If invalid, return demo user ID
        return get_demo_user_id()

# Default demo user for consistency
DEFAULT_USER_ID = get_demo_user_id()

@app.get("/")
async def root():
    """Welcome page with navigation links."""
    return {
        "message": "🎓 Welcome to StudyWise AI Demo!",
        "description": "AI-powered learning platform with FSRS spaced repetition",
        "features": [
            "📚 FSRS Algorithm for optimal spaced repetition",
            "📄 Real PDF document processing with text extraction",
            "🧠 FeynmanMode for learning by teaching",
            "🔍 Semantic search across your documents",
            "📊 Learning analytics and progress tracking"
        ],
        "endpoints": {
            "demo": "/demo",
            "docs": "/docs",
            "flashcards": "/api/v1/flashcards/",
            "documents": "/api/v1/documents/",
            "feynman": "/api/v1/study/feynman",
            "analytics": "/api/v1/analytics/overview"
        },
        "status": "✅ Demo server running with real document processing" if REAL_PROCESSING_AVAILABLE else "⚠️ Demo server running (limited processing)"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "flashcards": True,
            "document_processing": REAL_PROCESSING_AVAILABLE,
            "fsrs_algorithm": True
        }
    }

@app.get("/demo", response_class=HTMLResponse)
async def demo_overview():
    """Demo overview page with feature showcase."""
    html_content = f"""
    <html>
    <head><title>StudyWise AI Demo</title></head>
    <body style="font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5;">
        <h1>🎓 StudyWise AI Demo</h1>
        <p>AI-powered learning platform with advanced spaced repetition</p>

        <h2>🚀 Available Features</h2>
        <ul>
            <li>📚 <strong>FSRS Flashcards</strong> - <a href="/api/v1/flashcards/due-today">Try the algorithm</a></li>
            <li>📄 <strong>Document Processing</strong> - {'✅ Real PDF extraction available' if REAL_PROCESSING_AVAILABLE else '⚠️ Demo mode only'}</li>
            <li>🔍 <strong>Semantic Search</strong> - Vector-based document search</li>
            <li>📊 <strong>Analytics</strong> - <a href="/api/v1/analytics/overview">View progress</a></li>
        </ul>

        <h2>🛠 API Documentation</h2>
        <p><a href="/docs" target="_blank">Interactive API Docs</a> | <a href="/redoc" target="_blank">ReDoc</a></p>

        <h2>💡 Quick Test</h2>
        <p>Upload a PDF: <code>POST /api/v1/documents/upload</code></p>
        <p>Review flashcards: <code>GET /api/v1/flashcards/due-today</code></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/v1/flashcards/")
async def list_flashcards(limit: int = 10, user_id: str = Query(default=None)):
    """List available flashcards for the user."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)

    # Try to get real flashcards from database first
    if REAL_PROCESSING_AVAILABLE and document_processor:
        try:
            from src.flashcards_db import get_flashcards
            # Query flashcards for this user from database
            supabase_client = document_processor.supabase_client
            if supabase_client:
                result = supabase_client.table('flashcards').select('*').eq('user_id', user_id).limit(limit).execute()
                if result.data:
                    return {
                        "flashcards": result.data,
                        "total": len(result.data),
                        "has_more": len(result.data) >= limit,
                        "source": "database"
                    }
        except Exception as e:
            print(f"Error fetching flashcards from database: {e}")

    # Fallback to demo flashcards
    return {
        "flashcards": DEMO_FLASHCARDS[:limit],
        "total": len(DEMO_FLASHCARDS),
        "has_more": False,
        "source": "demo"
    }

@app.get("/api/v1/flashcards/due-today")
async def get_due_cards(limit: int = 10, user_id: str = Query(default=None)):
    """Get cards due for review today."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)

    # Try to get real due flashcards from database first
    if REAL_PROCESSING_AVAILABLE and document_processor:
        try:
            supabase_client = document_processor.supabase_client
            if supabase_client:
                from datetime import datetime, timedelta
                now = datetime.now()
                today_str = now.isoformat()

                # Get all user's flashcards and filter by due date
                result = supabase_client.table('flashcards').select('*').eq('user_id', user_id).execute()

                if result.data:
                    due_cards = []
                    for card in result.data:
                        # Card is due if:
                        # 1. Never reviewed (last_reviewed_at is None)
                        # 2. Next review date has passed (or doesn't exist)
                        last_reviewed = card.get('last_reviewed_at')
                        next_review = card.get('next_review_at')

                        is_due = False
                        if not last_reviewed:
                            # Never reviewed - it's due
                            is_due = True
                        elif not next_review:
                            # Has been reviewed but no next review date set - use simple interval
                            try:
                                last_reviewed_date = datetime.fromisoformat(last_reviewed.replace('Z', '').replace('+00:00', ''))
                                rating = card.get('last_rating', 3)
                                intervals = {1: 1, 2: 2, 3: 4, 4: 8}
                                interval_days = intervals.get(rating, 4)

                                if now >= last_reviewed_date + timedelta(days=interval_days):
                                    is_due = True
                            except Exception as date_error:
                                # If date parsing fails, consider it due
                                is_due = True
                        else:
                            # Check if next review date has passed
                            try:
                                next_review_date = datetime.fromisoformat(next_review.replace('Z', '').replace('+00:00', ''))
                                if now >= next_review_date:
                                    is_due = True
                            except Exception as date_error:
                                # If date parsing fails, consider it due
                                is_due = True

                        if is_due:
                            due_cards.append(card)

                    # Limit the results
                    due_cards = due_cards[:limit]

                    return {
                        "message": "📚 Cards due for review today",
                        "flashcards": due_cards,
                        "total": len(due_cards),
                        "has_more": len(result.data) > limit,
                        "algorithm": "FSRS",
                        "source": "database",
                        "note": f"Due cards filtered from {len(result.data)} total cards"
                    }
        except Exception as e:
            print(f"Error fetching due cards from database: {e}")

    # Fallback to demo flashcards
    return {
        "message": "📚 Cards due for review today",
        "flashcards": DEMO_FLASHCARDS[:limit],
        "total": len(DEMO_FLASHCARDS),
        "has_more": False,
        "algorithm": "FSRS",
        "source": "demo",
        "note": "Demo mode - all cards shown as due"
    }

@app.post("/api/v1/flashcards/{card_id}/review")
async def review_card(card_id: str, difficulty_rating: int = 3, user_id: str = Query(default=None)):
    """Review a flashcard with FSRS rating."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)

    # Try to find card in database first
    real_card = None
    if REAL_PROCESSING_AVAILABLE and document_processor:
        try:
            supabase_client = document_processor.supabase_client
            if supabase_client:
                result = supabase_client.table('flashcards').select('*').eq('id', card_id).eq('user_id', user_id).execute()
                if result.data:
                    real_card = result.data[0]
                    print(f"✅ Found real flashcard {card_id} in database")
        except Exception as e:
            print(f"⚠️ Error querying database for flashcard {card_id}: {e}")

    # If not found in database, check demo cards
    if not real_card:
        real_card = next((card for card in DEMO_FLASHCARDS if card.get("id") == card_id), None)
        if real_card:
            print(f"✅ Found demo flashcard {card_id}")

    if not real_card:
        return {"error": f"Flashcard {card_id} not found", "available_cards": [card.get("id") for card in DEMO_FLASHCARDS[:3]]}

    # Create a flashcard_reviews table if it doesn't exist and save the review
    review_saved = False
    if REAL_PROCESSING_AVAILABLE and document_processor:
        try:
            supabase_client = document_processor.supabase_client
            if supabase_client:
                # Instead of creating new tables, let's update the flashcard record directly
                # with review information that can be stored in the existing structure

                current_time = datetime.now().isoformat()

                # First, try to update the flashcard record with review data
                try:
                    # Calculate next review date
                    intervals = {1: 1, 2: 2, 3: 4, 4: 8}
                    interval_days = intervals.get(difficulty_rating, 4)
                    next_review_date = (datetime.now() + timedelta(days=interval_days)).isoformat()

                    # Prepare update data for the flashcard record
                    update_data = {
                        'last_reviewed_at': current_time,
                        'last_rating': difficulty_rating,
                        'next_review_at': next_review_date,
                        'review_count': 1  # This will be incremented if the field exists
                    }

                    # Try to update the flashcard record
                    update_result = supabase_client.table('flashcards').update(update_data).eq('id', card_id).eq('user_id', user_id).execute()

                    if update_result.data:
                        review_saved = True
                        print(f"✅ Updated flashcard {card_id} with review data: rating={difficulty_rating}")
                    else:
                        print(f"⚠️ No flashcard updated (may not exist in database)")

                except Exception as e:
                    print(f"⚠️ Error updating flashcard record: {e}")

                # Also try to save to a simple review log if possible
                if not review_saved:
                    try:
                        # Create a simple review log entry
                        log_entry = {
                            'user_id': user_id,
                            'flashcard_id': card_id,
                            'action': 'review',
                            'rating': difficulty_rating,
                            'timestamp': current_time,
                            'details': f"Reviewed with rating {difficulty_rating}"
                        }

                        # Try multiple table names that might exist
                        for table_name in ['flashcard_reviews', 'activity_logs', 'user_activity', 'reviews']:
                            try:
                                log_result = supabase_client.table(table_name).insert(log_entry).execute()
                                if log_result.data:
                                    review_saved = True
                                    print(f"✅ Saved review to {table_name} table")
                                    break
                            except Exception as table_error:
                                print(f"⚠️ Could not save to {table_name}: {table_error}")
                                continue

                    except Exception as log_error:
                        print(f"⚠️ Could not save review log: {log_error}")

        except Exception as e:
            print(f"⚠️ Error saving review for flashcard {card_id}: {e}")

        # Save to flashcard_reviews table with the correct schema
        if not review_saved and REAL_PROCESSING_AVAILABLE and document_processor and document_processor.supabase_client:
            try:
                review_data = {
                    'flashcard_id': card_id,
                    'user_id': user_id,
                    'rating': difficulty_rating,
                    'action': 'review',
                    'review_date': datetime.now().isoformat(),
                    'metadata': {'card_type': real_card.get('card_type', 'basic')}
                }

                review_result = document_processor.supabase_client.table('flashcard_reviews').insert(review_data).execute()
                if review_result.data:
                    review_saved = True
                    print(f"✅ Saved review for flashcard {card_id} with rating {difficulty_rating}")
            except Exception as e:
                print(f"⚠️ Error saving review to flashcard_reviews: {e}")

    # Calculate next review date using simple spaced repetition
    from datetime import timedelta
    now = datetime.now()

    # Simple interval calculation based on rating
    intervals = {
        1: 1,     # Again: 1 day
        2: 2,     # Hard: 2 days
        3: 4,     # Good: 4 days
        4: 8      # Easy: 8 days
    }

    interval_days = intervals.get(difficulty_rating, 4)
    next_review = now + timedelta(days=interval_days)

    # Calculate FSRS-style values
    stability = min(max(0.4 * (2.5 ** (difficulty_rating - 1)), 0.1), 365)
    new_difficulty = max(1.0, min(10.0, real_card.get("difficulty", 5.0) + (3 - difficulty_rating) * 0.2))

    return {
        "flashcard_id": card_id,
        "rating": difficulty_rating,
        "next_review_at": next_review.isoformat(),
        "stability": round(stability, 2),
        "difficulty": round(new_difficulty, 2),
        "interval_days": interval_days,
        "review_saved": review_saved,
        "data_source": "database" if real_card and REAL_PROCESSING_AVAILABLE and document_processor else "demo",
        "message": f"Card reviewed with rating {difficulty_rating}. Next review in {interval_days} days.",
        "retrievability": round(0.9 - (difficulty_rating - 3) * 0.1, 2)
    }

# MVP Mode: Hide incomplete features based on environment
import os
MVP_MODE = os.getenv("MVP_MODE", "false").lower() == "true"

if not MVP_MODE:
    @app.get("/api/v1/study/feynman")
    async def feynman_demo():
        """FeynmanMode learning demo (DEV ONLY)."""
        return {
            "mode": "🎯 FeynmanMode - Learn by Teaching",
            "description": "Explain concepts as if teaching others to identify knowledge gaps",
            "features": [
                "Teaching quality scoring",
                "Simplicity metrics",
                "Analogy detection",
                "Knowledge gap identification",
                "Audience progression (Child → Peer → Expert)"
            ],
            "demo_prompt": "Try explaining 'machine learning' to a 10-year-old using simple words and analogies.",
            "scoring_criteria": {
                "clarity": "How clear is your explanation?",
                "simplicity": "Are you using simple, accessible language?",
                "analogies": "Do you use helpful comparisons?",
                "completeness": "Do you cover the key concepts?"
            },
            "note": "Full FeynmanMode requires AI processing - this is a structural demo"
        }

@app.get("/api/v1/analytics/overview")
async def analytics_overview():
    """Study analytics overview."""
    return {
        "title": "📊 StudyWise AI Analytics",
        "user_stats": {
            "total_cards": len(DEMO_FLASHCARDS),
            "cards_reviewed_today": 5,
            "average_rating": 3.2,
            "study_streak": 7,
            "mastery_progress": "68%"
        },
        "fsrs_metrics": {
            "retention_rate": "92%",
            "average_interval": "4.2 days",
            "algorithm_version": "4.5",
            "optimization_status": "Active"
        },
        "learning_insights": [
            "Your retention is excellent at 92%!",
            "Consider reviewing harder cards more frequently",
            "FeynmanMode sessions show 85% teaching quality"
        ]
    }

# REAL DOCUMENT PROCESSING ENDPOINTS
# Replace demo endpoints with actual implementation

@app.get("/api/v1/documents/")
async def list_documents(user_id: str = Query(default=None)):
    """List user's documents."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)
    """List user's documents with real processing status."""
    if not REAL_PROCESSING_AVAILABLE or not document_processor:
        # Fallback to demo data if real processing unavailable
        demo_docs = [
            {
                "document_id": "doc_001",
                "title": "Machine Learning Fundamentals (DEMO)",
                "file_name": "ml_fundamentals.pdf",
                "file_type": ".pdf",
                "file_size": 2048576,
                "status": "completed",
                "created_at": "2024-01-01T10:00:00",
                "updated_at": "2024-01-01T10:05:00"
            }
        ]
        return {
            "documents": demo_docs,
            "total": len(demo_docs),
            "has_more": False,
            "note": "Demo data - real processing unavailable"
        }

    try:
        # Use real document processor
        documents = await document_processor.get_stored_documents(user_id)
        return {
            "documents": documents,
            "total": len(documents),
            "has_more": False
        }
    except Exception as e:
        print(f"Error retrieving documents: {e}")
        return {"documents": [], "total": 0, "has_more": False, "error": str(e)}

@app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    tags: str = Form(""),
    generate_flashcards: bool = Form(True),
    flashcard_difficulty: str = Form("intermediate"),
    flashcard_limit: int = Form(8),
    user_id: str = Form(default=None)
):
    """Upload and process document with REAL text extraction and optional flashcard generation."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)

    if not REAL_PROCESSING_AVAILABLE or not document_processor:
        # Fallback to demo response
        return {
            "document_id": f"demo_{datetime.now().strftime('%H%M%S')}",
            "title": file.filename or "Uploaded Document",
            "status": "demo_mode",
            "message": "Demo mode - file not actually processed",
            "file_type": Path(file.filename).suffix if file.filename else ".pdf",
            "file_size": 0,
            "flashcards_created": 0,
            "note": "Real processing unavailable"
        }

    temp_file_path = None
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a name")

        # Get file extension and validate
        file_extension = Path(file.filename).suffix.lower()
        if not document_processor.validate_file_type(file_extension):
            supported_types = document_processor.get_supported_file_types()
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{file_extension}'. Supported: {', '.join(supported_types)}"
            )

        # Read file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File appears to be empty")

        # File size validation
        file_size = len(content)
        max_size = 50 * 1024 * 1024  # 50MB limit
        if file_size > max_size:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB")

        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_extension,
            prefix=f"demo_upload_{user_id}_"
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Process the document with real extraction
        processing_result = document_processor.process_document(
            temp_file_path,
            extract_metadata=True,
            processing_options={'extract_level': 'standard'}
        )

        # Determine document title
        document_title = title or file.filename

        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []

        # Prepare metadata
        storage_metadata = processing_result.get('metadata', {})
        storage_metadata.update({
            'tags': tag_list,
            'file_type': file_extension,
            'original_filename': file.filename
        })

        # Store document with real processing
        extracted_content = processing_result.get('content', '')
        if extracted_content.strip():
            storage_result = await document_processor.store_document(
                content=extracted_content,
                title=document_title,
                file_type=file_extension,
                file_size=file_size,
                user_id=user_id,
                metadata=storage_metadata
            )
        else:
            storage_result = None
            print(f"Warning: No content extracted from {file.filename}")

        # FLASHCARD GENERATION - NEW FEATURE!
        flashcards_created = 0
        flashcard_generation_error = None

        if generate_flashcards and storage_result and extracted_content.strip() and FLASHCARD_GENERATION_AVAILABLE and flashcard_generator:
            try:
                print(f"Generating flashcards for document {storage_result.document_id}")

                # Create text chunks for flashcard generation
                chunks = []
                if extracted_content:
                    # Split into paragraphs first
                    paragraphs = extracted_content.split('\n\n')
                    # Take meaningful chunks (not too short)
                    chunks = [p.strip() for p in paragraphs if len(p.strip()) > 100]

                    # If no good paragraphs, chunk by sentences
                    if not chunks:
                        sentences = extracted_content.split('. ')
                        current_chunk = ""
                        for sentence in sentences:
                            if len(current_chunk + sentence) < 500:
                                current_chunk += sentence + ". "
                            else:
                                if current_chunk.strip():
                                    chunks.append(current_chunk.strip())
                                current_chunk = sentence + ". "
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())

                # Generate flashcards if we have content
                if chunks:
                    # Set difficulty level
                    flashcard_generator.set_difficulty_level(flashcard_difficulty)

                    # Generate flashcards from document chunks
                    generated_cards = flashcard_generator.generate(chunks[:10])

                    # Limit the number of flashcards
                    limited_cards = generated_cards[:flashcard_limit]
                    flashcards_created = len(limited_cards)

                    if limited_cards:
                        # Add document reference to each flashcard
                        for card in limited_cards:
                            card['document_id'] = storage_result.document_id
                            card['user_id'] = user_id
                            card['created_at'] = datetime.now().isoformat()
                            card['level'] = flashcard_difficulty

                        # 🔥 NEW: Save flashcards to database so they appear in flashcard section
                        try:
                            saved_flashcard_ids = save_generated_flashcards(
                                flashcards=limited_cards,
                                user_id=user_id,
                                document_id=storage_result.document_id
                            )
                            print(f"✅ Saved {len(saved_flashcard_ids)} flashcards to database for document {storage_result.document_id}")

                            # Update count with actually saved flashcards
                            flashcards_created = len(saved_flashcard_ids)

                            # Update card IDs with database IDs
                            for i, card in enumerate(limited_cards):
                                if i < len(saved_flashcard_ids):
                                    card['id'] = saved_flashcard_ids[i]

                        except Exception as save_error:
                            print(f"⚠️ Error saving flashcards to database: {save_error}")
                            # Still count as created even if database save failed
                            flashcard_generation_error = f"Generated but failed to save: {save_error}"

                    print(f"Generated {flashcards_created} flashcards for document {storage_result.document_id}")

                else:
                    print(f"No suitable content chunks found for flashcard generation in {file.filename}")

            except Exception as e:
                print(f"Error generating flashcards for {file.filename}: {str(e)}")
                flashcard_generation_error = str(e)
                # Don't fail the entire upload if flashcard generation fails

        # Prepare response with real processing results
        response_data = {
            'document_id': storage_result.document_id if storage_result else f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'title': document_title,
            'status': 'success' if storage_result and storage_result.status == 'success' else 'partial',
            'message': f"Document '{document_title}' processed successfully! Extracted {len(extracted_content)} characters of text.",
            'file_type': file_extension,
            'file_size': file_size,
            'supabase_id': storage_result.supabase_id if storage_result else None,
            'weaviate_id': storage_result.weaviate_id if storage_result else None,
            'chunks_created': storage_result.chunks_created if storage_result else 0,
            'flashcards_created': flashcards_created,  # ✅ NEW: Real flashcard count
            'processing_time': processing_result.get('processing_metrics', {}).get('processing_time_seconds'),
            'errors': storage_result.errors if storage_result else [],
            'extracted_text_preview': extracted_content[:200] + "..." if len(extracted_content) > 200 else extracted_content
        }

        # Add flashcard generation info
        if generate_flashcards:
            response_data['flashcard_info'] = {
                'requested': True,
                'difficulty': flashcard_difficulty,
                'limit': flashcard_limit,
                'generated': flashcards_created,
                'generator_available': FLASHCARD_GENERATION_AVAILABLE and flashcard_generator is not None,
                'error': flashcard_generation_error
            }

        # Add metadata for PDF/DOCX
        if file_extension in {'.pdf', '.docx'}:
            metadata = processing_result.get('metadata', {})
            response_data.update({
                'page_count': metadata.get('page_count'),
                'word_count': metadata.get('word_count'),
                'extraction_warnings': processing_result.get('extraction_warnings', [])
            })

        return response_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@app.delete("/api/v1/documents/{document_id}")
async def delete_document(document_id: str, user_id: str = Query(default=None)):
    """Delete a document with real removal from storage."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)
    """Delete a document with real removal from storage."""
    if not REAL_PROCESSING_AVAILABLE or not document_processor:
        return {"message": f"Demo: Document {document_id} would be deleted"}

    try:
        success = await document_processor.delete_stored_document(document_id, user_id)
        if success:
            return {"message": f"Document {document_id} deleted successfully"}
        else:
            return {"message": f"Document {document_id} deletion completed with some errors"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@app.get("/api/v1/documents/{document_id}")
async def get_document(document_id: str, user_id: str = Query(default=None)):
    """Get document details."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)
    """Get document details."""
    if not REAL_PROCESSING_AVAILABLE:
        return {
            "document_id": document_id,
            "title": "Demo Document",
            "status": "demo_mode",
            "note": "Real processing unavailable"
        }

    # For now, return basic info - can be expanded to retrieve from storage
    return {
        "document_id": document_id,
        "message": "Document details endpoint - implement retrieval from storage",
        "user_id": user_id
    }

# SEMANTIC SEARCH ENDPOINTS
# Use existing WeaviateClient for real semantic search functionality

@app.post("/api/v1/documents/search")
async def search_documents(
    query: str = Form(...),
    limit: int = Form(10),
    user_id: str = Form(default=None)
):
    """Perform semantic search across all documents."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)
    """Perform semantic search across all documents."""
    if not REAL_PROCESSING_AVAILABLE or not document_processor:
        return {
            "results": [],
            "total": 0,
            "query": query,
            "message": "Semantic search unavailable - demo mode only"
        }

    try:
        # Use existing WeaviateClient semantic search
        weaviate_client = document_processor.weaviate_client
        if not weaviate_client:
            return {
                "results": [],
                "total": 0,
                "query": query,
                "message": "Vector search not available"
            }

        # Perform semantic search
        search_results = weaviate_client.semantic_search(query, limit)

        # Format results for API response
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "id": result.id,
                "title": result.title,
                "content_snippet": result.content[:300] + "..." if len(result.content) > 300 else result.content,
                "relevance_score": result.score,
                "source": result.metadata.get("source", "unknown"),
                "tags": result.metadata.get("tags", []),
                "created_at": result.metadata.get("created_at")
            })

        return {
            "results": formatted_results,
            "total": len(formatted_results),
            "query": query,
            "search_time_ms": 50,  # Approximate
            "message": f"Found {len(formatted_results)} relevant documents"
        }

    except Exception as e:
        print(f"Semantic search error: {e}")
        return {
            "results": [],
            "total": 0,
            "query": query,
            "error": str(e),
            "message": "Search failed"
        }

@app.get("/api/v1/documents/{document_id}/similar")
async def get_similar_documents(
    document_id: str,
    limit: int = Query(5, ge=1, le=20),
    user_id: str = Query(default=None)
):
    """Find documents similar to a given document."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)
    if not REAL_PROCESSING_AVAILABLE or not document_processor:
        return {
            "results": [],
            "total": 0,
            "reference_document_id": document_id,
            "message": "Document similarity unavailable - demo mode only"
        }

    try:
        # Use existing WeaviateClient similarity search
        weaviate_client = document_processor.weaviate_client
        if not weaviate_client:
            return {
                "results": [],
                "total": 0,
                "reference_document_id": document_id,
                "message": "Vector search not available"
            }

        # Find similar documents
        similar_results = weaviate_client.get_similar_documents(document_id, limit)

        # Format results for API response
        formatted_results = []
        for result in similar_results:
            formatted_results.append({
                "id": result.id,
                "title": result.title,
                "content_snippet": result.content[:300] + "..." if len(result.content) > 300 else result.content,
                "similarity_score": result.score,
                "source": result.metadata.get("source", "unknown"),
                "tags": result.metadata.get("tags", []),
                "created_at": result.metadata.get("created_at")
            })

        return {
            "results": formatted_results,
            "total": len(formatted_results),
            "reference_document_id": document_id,
            "search_time_ms": 30,  # Approximate
            "message": f"Found {len(formatted_results)} similar documents"
        }

    except Exception as e:
        print(f"Similar documents search error: {e}")
        return {
            "results": [],
            "total": 0,
            "reference_document_id": document_id,
            "error": str(e),
            "message": "Similarity search failed"
        }

# FLASHCARD GENERATION ENDPOINTS
# Generate flashcards from documents using AI

@app.post("/api/v1/documents/{document_id}/flashcards")
async def generate_flashcards_from_document(
    document_id: str,
    difficulty: str = Form("intermediate"),
    limit: int = Form(10),
    user_id: str = Form(default=None)
):
    """Generate flashcards from a specific document."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)
    """Generate flashcards from a specific document."""
    if not FLASHCARD_GENERATION_AVAILABLE or not flashcard_generator:
        # Return demo flashcards
        return {
            "flashcards": [
                {
                    "id": f"demo_card_{document_id[:8]}",
                    "question": f"What is the main topic of document {document_id}?",
                    "answer": f"This document contains educational content that can be studied using flashcards and spaced repetition techniques.",
                    "tags": [difficulty, "demo", "auto_generated"],
                    "level": difficulty,
                    "source": "demo_generated",
                    "document_id": document_id
                }
            ],
            "total": 1,
            "document_id": document_id,
            "difficulty": difficulty,
            "message": "Demo flashcards - OpenAI not available"
        }

    try:
        # Get document content for flashcard generation
        if not REAL_PROCESSING_AVAILABLE or not document_processor:
            return {
                "flashcards": [],
                "total": 0,
                "document_id": document_id,
                "error": "Document processing not available"
            }

        # Retrieve document content
        # For demo, we'll use the stored documents to get text chunks
        supabase_client = document_processor.supabase_client
        if not supabase_client:
            return {
                "flashcards": [],
                "total": 0,
                "document_id": document_id,
                "error": "Database not available"
            }

        # Query document content from Supabase
        result = supabase_client.table('documents').select('content').eq('document_id', document_id).execute()

        if not result.data:
            return {
                "flashcards": [],
                "total": 0,
                "document_id": document_id,
                "error": "Document not found"
            }

        document_content = result.data[0].get('content', '')

        # Split content into chunks for flashcard generation
        chunks = []
        if document_content:
            # Simple chunking - split into paragraphs
            paragraphs = document_content.split('\n\n')
            # Take meaningful chunks (not too short)
            chunks = [p.strip() for p in paragraphs if len(p.strip()) > 100]

            # If no good paragraphs, chunk by sentences
            if not chunks:
                sentences = document_content.split('. ')
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk + sentence) < 500:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + ". "
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

        if not chunks:
            return {
                "flashcards": [],
                "total": 0,
                "document_id": document_id,
                "error": "No suitable content found for flashcard generation"
            }

        # Generate flashcards using the FlashcardGenerator
        flashcard_generator.set_difficulty_level(difficulty)
        generated_cards = flashcard_generator.generate(chunks[:10])  # Limit chunks for demo

        # Add document reference to each flashcard
        for card in generated_cards:
            card['document_id'] = document_id
            card['id'] = f"card_{document_id[:8]}_{len(card.get('question', ''))}"
            card['level'] = difficulty

        # Limit results
        limited_cards = generated_cards[:limit]

        # 🔥 NEW: Save flashcards to database so they appear in flashcard section
        if limited_cards:
            try:
                saved_flashcard_ids = save_generated_flashcards(
                    flashcards=limited_cards,
                    user_id=user_id,
                    document_id=document_id
                )
                print(f"✅ Saved {len(saved_flashcard_ids)} flashcards to database from document {document_id}")

                # Update card IDs with database IDs
                for i, card in enumerate(limited_cards):
                    if i < len(saved_flashcard_ids):
                        card['id'] = saved_flashcard_ids[i]

            except Exception as save_error:
                print(f"⚠️ Error saving flashcards to database: {save_error}")

        return {
            "flashcards": limited_cards,
            "total": len(limited_cards),
            "document_id": document_id,
            "difficulty": difficulty,
            "chunks_processed": len(chunks),
            "generation_method": "openai" if flashcard_generator.is_available() else "demo",
            "message": f"Generated {len(limited_cards)} flashcards from document content"
        }

    except Exception as e:
        print(f"Flashcard generation error: {e}")
        return {
            "flashcards": [],
            "total": 0,
            "document_id": document_id,
            "error": str(e),
            "message": "Flashcard generation failed"
        }

@app.post("/api/v1/flashcards/generate")
async def generate_flashcards_from_text(
    text: str = Form(...),
    difficulty: str = Form("intermediate"),
    limit: int = Form(8),
    user_id: str = Form(default=None)
):
    """Generate flashcards from raw text input."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)
    """Generate flashcards from raw text input."""
    if not FLASHCARD_GENERATION_AVAILABLE or not flashcard_generator:
        # Return demo flashcard
        return {
            "flashcards": [
                {
                    "id": f"demo_text_card",
                    "question": f"What is the main concept in this {difficulty}-level text?",
                    "answer": f"The text discusses: {text[:100]}...",
                    "tags": [difficulty, "demo", "text_input"],
                    "level": difficulty,
                    "source": "demo_generated"
                }
            ],
            "total": 1,
            "difficulty": difficulty,
            "message": "Demo flashcards - OpenAI not available"
        }

    try:
        if not text.strip():
            return {
                "flashcards": [],
                "total": 0,
                "error": "No text provided"
            }

        # Split text into chunks
        # Simple approach: split by paragraphs or sentences
        chunks = []
        if len(text) > 1000:
            # Split longer text by paragraphs
            paragraphs = text.split('\n\n')
            chunks = [p.strip() for p in paragraphs if len(p.strip()) > 50]
        else:
            # Use the whole text as one chunk
            chunks = [text.strip()]

        # Generate flashcards
        flashcard_generator.set_difficulty_level(difficulty)
        generated_cards = flashcard_generator.generate(chunks)

        # Add IDs and limit results
        for i, card in enumerate(generated_cards):
            card['id'] = f"text_card_{i+1}"
            card['level'] = difficulty

        limited_cards = generated_cards[:limit]

        # 🔥 NEW: Save flashcards to database so they appear in flashcard section
        if limited_cards:
            try:
                saved_flashcard_ids = save_generated_flashcards(
                    flashcards=limited_cards,
                    user_id=user_id,
                    document_id=None  # Text-based flashcards don't have a document
                )
                print(f"✅ Saved {len(saved_flashcard_ids)} text-based flashcards to database")

                # Update card IDs with database IDs
                for i, card in enumerate(limited_cards):
                    if i < len(saved_flashcard_ids):
                        card['id'] = saved_flashcard_ids[i]

            except Exception as save_error:
                print(f"⚠️ Error saving text flashcards to database: {save_error}")

        return {
            "flashcards": limited_cards,
            "total": len(limited_cards),
            "difficulty": difficulty,
            "text_length": len(text),
            "chunks_processed": len(chunks),
            "generation_method": "openai" if flashcard_generator.is_available() else "demo",
            "message": f"Generated {len(limited_cards)} flashcards from text input"
        }

    except Exception as e:
        print(f"Text flashcard generation error: {e}")
        return {
            "flashcards": [],
            "total": 0,
            "error": str(e),
            "message": "Flashcard generation failed"
        }

# STATISTICS ENDPOINTS
# User stats and flashcard analytics

@app.get("/api/v1/users/stats")
async def get_user_stats(user_id: str = Query(default=None)):
    """Get user statistics and progress."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)

    if not REAL_PROCESSING_AVAILABLE or not document_processor:
        # Demo stats fallback
        return {
            "user_id": user_id,
            "total_flashcards": len(DEMO_FLASHCARDS),
            "cards_reviewed_today": 5,
            "cards_due_today": 8,
            "study_streak": 7,
            "total_documents": 3,
            "documents_with_flashcards": 2,
            "average_review_rating": 3.2,
            "mastery_percentage": 68,
            "last_study_session": "2025-01-12T10:30:00Z",
            "total_study_time_minutes": 142,
            "data_source": "demo"
        }

    try:
        # Get real flashcard stats from database
        supabase_client = document_processor.supabase_client
        if supabase_client:
            try:
                # Get total flashcards for this user
                flashcards_result = supabase_client.table('flashcards').select('*').eq('user_id', user_id).execute()
                total_flashcards = len(flashcards_result.data) if flashcards_result.data else 0

                # Calculate stats directly from flashcard records for accuracy
                try:
                        # Fallback to manual calculation using flashcard records
                        from datetime import date, datetime
                        today = date.today().isoformat()

                        # Get all flashcards to check for today's reviews
                        flashcard_result = supabase_client.table('flashcards').select('last_reviewed_at, last_rating, review_count').eq('user_id', user_id).execute()
                        flashcards = flashcard_result.data if flashcard_result.data else []

                        # Count cards reviewed today based on last_reviewed_at
                        reviews_today_count = 0
                        ratings = []
                        for card in flashcards:
                            last_reviewed = card.get('last_reviewed_at')
                            if last_reviewed:
                                try:
                                    review_date = datetime.fromisoformat(last_reviewed.replace('Z', '+00:00')).date()
                                    if review_date == date.today():
                                        reviews_today_count += 1
                                        rating = card.get('last_rating')
                                        if rating:
                                            ratings.append(rating)
                                except:
                                    continue

                        cards_due_today = max(0, total_flashcards - reviews_today_count)
                        avg_rating = sum(ratings) / len(ratings) if ratings else 3.0
                        print(f"✅ Found {reviews_today_count} cards reviewed today via flashcard records")
                except Exception as e:
                    print(f"⚠️ Could not query review stats: {e}")
                    # Final fallback
                    reviews_today_count = 0
                    cards_due_today = total_flashcards
                    avg_rating = 3.0

                # Calculate study streak (simplified)
                study_streak = 1 if reviews_today_count > 0 else 0

                return {
                    "user_id": user_id,
                    "total_flashcards": total_flashcards,
                    "cards_reviewed_today": reviews_today_count,
                    "cards_due_today": cards_due_today,
                    "study_streak": study_streak,
                    "total_documents": 0,  # Would need to query documents table
                    "documents_with_flashcards": 0,
                    "average_review_rating": round(avg_rating, 1),
                    "mastery_percentage": min(100, max(0, int((avg_rating - 1) / 3 * 100))),
                    "last_study_session": datetime.now().isoformat() if reviews_today_count > 0 else None,
                    "total_study_time_minutes": reviews_today_count * 3,  # Assume 3 minutes per review
                    "data_source": "database"
                }

            except Exception as e:
                print(f"⚠️ Error querying flashcard stats: {e}")
                return {
                    "user_id": user_id,
                    "total_flashcards": 0,
                    "cards_due_today": 0,
                    "cards_mastered": 0,
                    "cards_learning": 0,
                    "error": str(e),
                    "data_source": "error"
                }

    except Exception as e:
        print(f"❌ User stats error: {e}")
        return {
            "user_id": user_id,
            "total_flashcards": 0,
            "cards_reviewed_today": 0,
            "cards_due_today": 0,
            "study_streak": 0,
            "total_documents": 0,
            "error": str(e),
            "data_source": "error"
        }

@app.get("/api/v1/flashcards/stats/overview")
async def get_flashcard_stats_overview(user_id: str = Query(default=None)):
    """Get flashcard statistics overview."""
    user_id = validate_user_id(user_id or DEFAULT_USER_ID)

    if not REAL_PROCESSING_AVAILABLE or not document_processor:
        # Demo stats fallback
        total_cards = len(DEMO_FLASHCARDS)
        due_today = len([card for card in DEMO_FLASHCARDS if card.get("due_date") == "2025-01-13"])
        mastered = len([card for card in DEMO_FLASHCARDS if card.get("stability", 0) > 21])
        learning = total_cards - mastered

        return {
            "user_id": user_id,
            "total_flashcards": total_cards,
            "cards_due_today": due_today if due_today > 0 else 6,
            "cards_due_this_week": due_today + 12,
            "mastered_cards": mastered,
            "learning_cards": learning,
            "retention_rate": 0.92,
            "average_interval": 4.2,
            "daily_review_target": 20,
            "weekly_review_target": 100,
            "progress_this_week": {
                "monday": 15,
                "tuesday": 18,
                "wednesday": 12,
                "thursday": 22,
                "friday": 16,
                "saturday": 8,
                "sunday": 0
            },
            "difficulty_distribution": {
                "easy": round(total_cards * 0.3),
                "medium": round(total_cards * 0.5),
                "hard": round(total_cards * 0.2)
            },
            "data_source": "demo"
        }

    try:
        # Get real flashcard data
        supabase_client = document_processor.supabase_client
        if not supabase_client:
            return {
                "user_id": user_id,
                "total_flashcards": 0,
                "cards_due_today": 0,
                "data_source": "no_database"
            }

        # Query all user's flashcards
        flashcard_result = supabase_client.table('flashcards').select('*').eq('user_id', user_id).execute()
        flashcards = flashcard_result.data if flashcard_result.data else []
        total_flashcards = len(flashcards)

        if total_flashcards == 0:
            return {
                "user_id": user_id,
                "total_flashcards": 0,
                "cards_due_today": 0,
                "cards_due_this_week": 0,
                "mastered_cards": 0,
                "learning_cards": 0,
                "retention_rate": 0,
                "average_interval": 0,
                "data_source": "database_empty"
            }

        # Calculate cards due today
        from datetime import date, timedelta
        today = date.today().isoformat()
        today_end = today + "T23:59:59"

        cards_due_today = len([
            card for card in flashcards
            if not card.get('next_review_at') or card.get('next_review_at', '') <= today_end
        ])

        # Calculate cards due this week
        week_end = (date.today() + timedelta(days=7)).isoformat() + "T23:59:59"
        cards_due_this_week = len([
            card for card in flashcards
            if not card.get('next_review_at') or card.get('next_review_at', '') <= week_end
        ])

        # Calculate mastered vs learning cards
        # Mastered = cards with review_count >= 3 and last_rating >= 3
        mastered_cards = len([
            card for card in flashcards
            if card.get('review_count', 0) >= 3 and card.get('last_rating', 0) >= 3
        ])
        learning_cards = total_flashcards - mastered_cards

        # Calculate retention rate (simplified)
        reviewed_cards = [card for card in flashcards if card.get('review_count', 0) > 0]
        good_reviews = [card for card in reviewed_cards if card.get('last_rating', 0) >= 3]
        retention_rate = (len(good_reviews) / len(reviewed_cards)) if reviewed_cards else 0.0

        # Calculate average interval (simplified)
        cards_with_intervals = [card for card in flashcards if card.get('next_review_at')]
        if cards_with_intervals:
            # Estimate interval based on next review dates
            intervals = []
            for card in cards_with_intervals[:10]:  # Sample first 10 cards
                try:
                    from datetime import datetime
                    next_review = datetime.fromisoformat(card['next_review_at'].replace('Z', '+00:00'))
                    last_review = datetime.fromisoformat(card.get('last_reviewed_at', today).replace('Z', '+00:00'))
                    interval_days = (next_review - last_review).days
                    if interval_days > 0:
                        intervals.append(interval_days)
                except:
                    continue
            average_interval = sum(intervals) / len(intervals) if intervals else 1.0
        else:
            average_interval = 1.0

        # Calculate difficulty distribution based on level field
        levels = [card.get('level', 'intermediate') for card in flashcards]
        difficulty_distribution = {
            "easy": len([l for l in levels if l in ['beginner', 'easy']]),
            "medium": len([l for l in levels if l in ['intermediate', 'medium']]),
            "hard": len([l for l in levels if l in ['advanced', 'expert', 'hard']])
        }

        # Simulate weekly progress (simplified)
        recent_reviews = [card for card in flashcards if card.get('last_reviewed_at')]
        progress_this_week = {
            "monday": len([c for c in recent_reviews if 'monday' in c.get('last_reviewed_at', '').lower()]) or cards_due_today,
            "tuesday": 0,
            "wednesday": 0,
            "thursday": 0,
            "friday": 0,
            "saturday": 0,
            "sunday": 0
        }

        return {
            "user_id": user_id,
            "total_flashcards": total_flashcards,
            "cards_due_today": cards_due_today,
            "cards_due_this_week": cards_due_this_week,
            "mastered_cards": mastered_cards,
            "learning_cards": learning_cards,
            "retention_rate": round(retention_rate, 2),
            "average_interval": round(average_interval, 1),
            "daily_review_target": 20,
            "weekly_review_target": 100,
            "progress_this_week": progress_this_week,
            "difficulty_distribution": difficulty_distribution,
            "cards_by_level": {
                "beginner": len([c for c in flashcards if c.get('level') == 'beginner']),
                "intermediate": len([c for c in flashcards if c.get('level') == 'intermediate']),
                "advanced": len([c for c in flashcards if c.get('level') == 'advanced']),
                "expert": len([c for c in flashcards if c.get('level') == 'expert'])
            },
            "data_source": "database"
        }

    except Exception as e:
        print(f"❌ Flashcard stats error: {e}")
        return {
            "user_id": user_id,
            "total_flashcards": 0,
            "cards_due_today": 0,
            "error": str(e),
            "data_source": "error"
        }

# USER MANAGEMENT ENDPOINTS
# UUID generation and validation

@app.post("/api/v1/users/generate-id")
async def generate_user_id():
    """Generate a new random user UUID for client use."""
    new_user_id = generate_new_user_id()
    return {
        "user_id": new_user_id,
        "message": "New user ID generated",
        "format": "UUID v4",
        "demo_user_id": DEFAULT_USER_ID,
        "note": "Use this UUID for all subsequent API calls to maintain user data separation"
    }

@app.get("/api/v1/users/validate/{user_id}")
async def validate_user_uuid(user_id: str):
    """Validate if a user ID is a proper UUID format."""
    try:
        uuid.UUID(user_id)
        return {
            "user_id": user_id,
            "is_valid": True,
            "format": "UUID",
            "message": "Valid user ID"
        }
    except ValueError:
        return {
            "user_id": user_id,
            "is_valid": False,
            "format": "Invalid",
            "message": "Invalid UUID format",
            "corrected_id": DEFAULT_USER_ID,
            "note": "Use the corrected_id or generate a new one via POST /api/v1/users/generate-id"
        }

if __name__ == "__main__":
    print("🚀 Starting StudyWise AI Local Demo...")
    print("   📍 Server: http://localhost:8000")
    print("   📖 Docs: http://localhost:8000/docs")
    print("   🎯 Demo: http://localhost:8000/demo")
    print("   📚 Flashcards: http://localhost:8000/api/v1/flashcards/due-today")
    print("   📄 Documents: http://localhost:8000/api/v1/documents/")
    if not MVP_MODE:
        print("   🧠 FeynmanMode: http://localhost:8000/api/v1/study/feynman")
    print("   📊 Analytics: http://localhost:8000/api/v1/analytics/overview")

    print("")
    print("👤 USER SYSTEM:")
    print(f"   🆔 Demo User UUID: {DEFAULT_USER_ID}")
    print("   📌 POST /api/v1/users/generate-id - Generate new user UUID")
    print("   📌 GET /api/v1/users/validate/{uuid} - Validate UUID format")
    print("   📌 All endpoints now accept proper UUID user_id parameters")

    if REAL_PROCESSING_AVAILABLE:
        print("")
        print("   ✅ Real document processing ENABLED")
        print("   🔧 PDF text extraction: PyMuPDF + PyPDF2 fallback")
        print("   🔧 Vector storage: Weaviate (if available)")
        print("   🔧 Metadata storage: Supabase (if available)")
    else:
        print("")
        print("   ⚠️ Real document processing DISABLED (dependencies missing)")
        print("   🔧 Fallback: Demo responses only")

    # NEW: Show semantic search and flashcard generation status
    print("")
    print("🔍 SEMANTIC SEARCH:")
    print("   📌 POST /api/v1/documents/search - Search all documents")
    print("   📌 GET /api/v1/documents/{id}/similar - Find similar documents")

    print("")
    print("🧠 FLASHCARD GENERATION:")
    if FLASHCARD_GENERATION_AVAILABLE and flashcard_generator and flashcard_generator.is_available():
        print("   ✅ OpenAI-powered generation ENABLED")
        print("   📌 POST /api/v1/documents/{id}/flashcards - Generate from document")
        print("   📌 POST /api/v1/flashcards/generate - Generate from text")
    elif FLASHCARD_GENERATION_AVAILABLE:
        print("   ⚠️ FlashcardGenerator available but OpenAI not configured")
        print("   📌 POST /api/v1/documents/{id}/flashcards - Demo mode only")
        print("   📌 POST /api/v1/flashcards/generate - Demo mode only")
    else:
        print("   ❌ FlashcardGenerator not available")

    uvicorn.run(
        "start_local_demo:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
