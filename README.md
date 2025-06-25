# StudyWise AI 🧠✨

> **AI-Powered Learning Platform with FSRS Spaced Repetition & Advanced Study Modes**

StudyWise AI transforms study materials into intelligent, interactive learning experiences by combining proven educational psychology with state-of-the-art AI.

---

## 🚀 Quick Start (Local Development)

```bash
# 1. Clone and set up a virtual environment
git clone <repository-url>
cd study-wise-ai
python -m venv study-env && source study-env/bin/activate
pip install -r requirements.txt

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# 3. Generate a secure secret key (production only)
python scripts/generate_secret_key.py

# 4. Run the development server
python start_local_demo.py  # http://localhost:8000
```

---

## 🌐 Production Deployment — Google Cloud Run

StudyWise AI ships with first-class support for Google Cloud Run. Two options are provided.

### 1. One-Command Deployment using `deploy.sh`

```bash
./deploy.sh                      # backend only, Cloud Build + Cloud Run
```

The script will:
1. Enable required GCP APIs (Cloud Build, Cloud Run, Container Registry).
2. Build the container image and push it to Container Registry.
3. Deploy the image to Cloud Run with recommended CPU, memory, and scaling parameters.
4. Output the live service URL so that it can be added to the frontend or CORS configuration.

### 2. Cloud Build Trigger (`cloudbuild.yaml`)

Add a build trigger in the Cloud Console that points to the repository and references the included `cloudbuild.yaml`. Every push to `main` will then:

1. Build the Docker image `gcr.io/$PROJECT_ID/studywise-api:$COMMIT_SHA`.
2. Push it to Container Registry.
3. Deploy the image to Cloud Run (region `us-central1`, service name `studywise-api`).

A minimal manual invocation looks like this:

```bash
# From the project root
gcloud builds submit --config cloudbuild.yaml
```

Once deployment finishes, retrieve the service URL:

```bash
SERVICE_URL=$(gcloud run services describe studywise-api \
             --region us-central1 \
             --format="value(status.url)")
echo "Backend available at $SERVICE_URL"
```

> **Tip :** To deploy the companion React frontend as well, see `deploy-both.sh`, which builds and deploys both images and automatically wires the frontend's `VITE_API_URL` to the new backend URL.

---

## 🌟 Core Features

### 🧠 **Flashcards**
- **FSRS Algorithm**: Scientific spaced repetition with 17-parameter algorithm for your flashcards
- **Document Processing**: PDF/DOCX upload with semantic search

### 🔍 **Intelligent Processing**
- **Hybrid Architecture**: Weaviate (vector) + Supabase (relational)
- **Semantic Search**: OpenAI embeddings with similarity scoring --> Talk to you database.
- **Real-time Analytics**: Comprehensive learning insights and progress tracking

### 🎯 **Production Ready**
- **FastAPI Backend**: High-performance API with 36+ endpoints
- **React Frontend**: Modern TypeScript interface
- **UUID Authentication**: Secure user session management
- **Comprehensive Testing**: 30+ tests with automated validation

## 🏗️ Architecture

```
🌐 React Frontend ←→ ⚡ FastAPI Backend ←→ 🔍 Weaviate (Vector) + 📊 Supabase (Data)
                                        ↕
                                    🤖 OpenAI (GPT-4 + Embeddings)
```

**Key Components:**
- **Study Framework**: FSRS Flashcards
- **Document Processing**: PDF/DOCX handlers with intelligent chunking
- **Vector Search**: Semantic document retrieval and similarity
- **Analytics Engine**: Learning progress and personalized recommendations

## 🧪 Quality Assurance

### **Multi-Layer Validation System**
```bash
# Quick sanity check (≈ 1 second)
python scripts/pre_merge_validation.py --quick

# Full test suite (≈ 45 seconds)
python scripts/pre_merge_validation.py
```

### **Automated Protection**
- **Pre-commit hooks**: Validate every commit automatically
- **GitHub Actions**: CI/CD pipeline with PR validation
- **Zero disruption guarantee**: All changes tested against existing functionality

### **Test Coverage**
- ✅ **442 tests collected** across all modules
- ✅ **FSRS Algorithm**: Integration tests with real scheduling
- ✅ **API Endpoints**: All 36 routes validated

## 🔐 Security & Configuration

### **Environment-Based Configuration**
```bash
# Development: Auto-generates secure keys
ENVIRONMENT=development

# Production: Requires explicit SECRET_KEY
ENVIRONMENT=production
SECRET_KEY=your_secure_key_here  # Generate with scripts/generate_secret_key.py
```

### **Production Security**
- **Secret Management**: Environment-based with validation
- **No Hardcoded Keys**: Production deployment blocked without proper secrets
- **Security Scanning**: Automated detection of security issues

## 📊 FSRS Spaced Repetition

### **How It Works**
1. **Smart Scheduling**: 17-parameter algorithm optimizes review intervals
2. **4-Point Rating**: Again (1 day) → Hard (2 days) → Good (4 days) → Easy (8 days)
3. **Adaptive Learning**: Algorithm learns from your performance patterns

### **API Endpoints**
```bash
GET /api/v1/flashcards/due-today        # Cards due for review
POST /api/v1/flashcards/{id}/review     # Record review with rating
GET /api/v1/flashcards/stats/overview   # Learning statistics
```

## 💡 Usage Examples

### **Start Learning Session**
```bash
# Get cards due today
curl http://localhost:8000/api/v1/flashcards/due-today

# Review with FSRS rating (1=Again, 2=Hard, 3=Good, 4=Easy)
curl -X POST "http://localhost:8000/api/v1/flashcards/card_001/review?difficulty_rating=3"
```

### **Upload & Process Documents**
```bash
# Upload PDF with automatic flashcard generation
curl -X POST -F "file=@document.pdf" -F "generate_flashcards=true" \
  http://localhost:8000/api/v1/documents/upload
```

### **Semantic Search**
```bash
# Search across all documents
curl -X POST -F "query=machine learning concepts" \
  http://localhost:8000/api/v1/documents/search
```

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | FastAPI + Python 3.12 | High-performance API |
| **Frontend** | React + TypeScript + Vite | Modern UI |
| **Vector DB** | Weaviate Cloud | Semantic search |
| **Database** | Supabase PostgreSQL | Structured data |
| **AI/ML** | OpenAI GPT-4 + Embeddings | Natural language processing |
| **Algorithm** | FSRS | Scientific spaced repetition |

## 📁 Project Structure

```
study-wise-ai/
├── 🔧 api/                    # FastAPI backend
├── 🧠 src/study_modes/        # Learning modes (FeynmanMode, Traditional)
├── 🧮 src/flashcards/         # FSRS spaced repetition system
├── 📄 src/file_handlers/      # Document processing (PDF, DOCX)
├── 🧪 tests/                  # Comprehensive test suite (442 tests)
├── 📊 scripts/                # Validation & deployment tools
└── 📖 docs/                   # Documentation & guides
```

## 🚦 Development Workflow

### **Making Changes**
```bash
# 1. Validate starting point
python scripts/pre_merge_validation.py --quick

# 2. Make your changes...

# 3. Auto-validation on commit
git commit -m "Your changes"  # Pre-commit hook runs

# 4. Full validation before PR
python scripts/pre_merge_validation.py
```

### **Contributing Guidelines**
1. **Install validation**: `python scripts/install_pre_commit_hook.py`
2. **Follow workflow**: Design → Scaffold → Implement → Test
3. **Ensure tests pass**: All validation must pass before merge
4. **Document changes**: Update relevant documentation

## 📖 Documentation

- **[Production Security Guide](docs/PRODUCTION_SECURITY.md)**: Secret management & deployment
- **[Testing Strategy](docs/TESTING_STRATEGY.md)**: Validation system & best practices
- **[MVP Deployment Guide](MVP_DEPLOYMENT_GUIDE.md)**: Feature-separated deployment
- **[API Documentation](http://localhost:8000/docs)**: Interactive Swagger docs

## 🎯 Key Endpoints

```bash
# Core Application
GET  /                              # Welcome & feature overview
GET  /health                        # System health check
GET  /docs                          # API documentation

# Flashcards (FSRS)
GET  /api/v1/flashcards/due-today   # Cards due for review
POST /api/v1/flashcards/{id}/review # Record review & get next interval

# Documents
POST /api/v1/documents/upload       # Upload PDF/DOCX with processing
POST /api/v1/documents/search       # Semantic search across documents

# Analytics
GET  /api/v1/flashcards/stats/overview  # Learning progress & insights
GET  /api/v1/users/stats             # User statistics & performance
```

## 🎉 Demo & Testing

```bash
# Live demos
python demo_spaced_repetition.py    # FSRS algorithm demonstration
python test_feynman_demo.py         # FeynmanMode teaching analysis

# Validation
python scripts/pre_merge_validation.py --quick  # Fast validation
python scripts/pre_merge_validation.py          # Full system validation

# Server
python start_local_demo.py          # Demo server with all features
```

---

**StudyWise AI - Transforming Learning Through Teaching** 🧠✨

*Built with modern AI, educational psychology, and comprehensive validation*

© 2025 Renato Boemer. All rights reserved.
