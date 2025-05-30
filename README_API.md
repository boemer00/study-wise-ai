# StudyWise AI FastAPI Backend

A simple FastAPI backend wrapper for the StudyWise AI conversational RAG system.

## Quick Start

1. **Start the server:**
   ```bash
   python start_api.py
   ```

2. **Access the API:**
   - Server: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## API Endpoints

### Core Endpoints
- `GET /` - Root endpoint with API info
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

### Chat/Conversation (`/api/v1/chat/`)
- `POST /conversations` - Create new conversation
- `POST /conversations/{id}/messages` - Send message to AI
- `GET /conversations/{id}/history` - Get conversation history
- `PUT /conversations/{id}` - Update conversation
- `DELETE /conversations/{id}` - End conversation
- `GET /conversations` - List user conversations

### Flashcards (`/api/v1/flashcards/`)
- `POST /` - Create flashcard
- `GET /` - List flashcards with filtering
- `GET /{id}` - Get specific flashcard
- `PUT /{id}` - Update flashcard
- `DELETE /{id}` - Delete flashcard
- `POST /{id}/review` - Record review session
- `GET /{id}/stats` - Get flashcard statistics
- `POST /study-session` - Start study session
- `GET /stats/overview` - User flashcard overview
- `GET /due-today` - Cards due for review

### Documents (`/api/v1/documents/`)
- `POST /upload` - Upload document for RAG
- `GET /` - List user documents
- `DELETE /{id}` - Delete document

### Users (`/api/v1/users/`)
- `GET /profile` - User profile
- `GET /stats` - Learning statistics
- `GET /conversations` - User conversations

### System (`/api/v1/system/`)
- `GET /health` - System health check
- `GET /status` - System status
- `GET /version` - API version

## Authentication

Currently using demo authentication with a default user. All requests are authenticated as `demo-user-123`.

## Integration with Lovable

This API is designed to work with a Lovable frontend. Key features:

- **CORS enabled** for frontend integration
- **Simple authentication** for easy development
- **RESTful endpoints** for all StudyWise AI features
- **Interactive docs** for easy frontend development
- **Error handling** with proper HTTP status codes

## Development

The API is built on top of the existing StudyWise AI system:
- Uses `StudyAssistant` for conversational RAG
- Integrates with existing Supabase/Weaviate infrastructure
- Maintains conversation memory and flashcard spaced repetition

## Configuration

The API uses environment variables from your existing `.env` file:
- `OPENAI_API_KEY`
- `SUPABASE_URL` and `SUPABASE_KEY`
- `WEAVIATE_URL` and `WEAVIATE_API_KEY`

## Next Steps

1. **Implement endpoint functionality** - Connect API routes to StudyAssistant
2. **Build Lovable frontend** - Create interactive UI with chat and flashcards
3. **Add authentication** - Implement proper user management
4. **Deploy** - Set up production deployment

The scaffolding is complete and ready for implementation!
