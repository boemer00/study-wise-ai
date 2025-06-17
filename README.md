# StudyWise AI 🧠✨

> **AI-Powered Learning Platform with FSRS Spaced Repetition & Advanced Study Modes**

StudyWise AI transforms study materials into intelligent, interactive learning experiences using cutting-edge AI and educational psychology principles.

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd study-wise-ai
python -m venv study-env && source study-env/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Generate secure production key
python scripts/generate_secret_key.py

# 4. Install validation system
python scripts/install_pre_commit_hook.py

# 5. Start demo server
python start_local_demo.py  # http://localhost:8000
```

## 🌟 Core Features

### 🧠 **Advanced Study Modes**
- **FeynmanMode**: Learn by teaching with real-time quality analysis and feedback
- **FSRS Flashcards**: Scientific spaced repetition with 17-parameter algorithm
- **TraditionalMode**: Classic Q&A with adaptive difficulty
- **Document Processing**: PDF/DOCX upload with semantic search

### 🔍 **Intelligent Processing**
- **Hybrid Architecture**: Weaviate (vector) + Supabase (relational)
- **Semantic Search**: OpenAI embeddings with similarity scoring
- **Real-time Analytics**: Comprehensive learning insights and progress tracking
- **Voice AI Ready**: Prepared for TTS/STT integration

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
- **Study Modes Framework**: FeynmanMode, Traditional, FSRS Flashcards
- **Document Processing**: PDF/DOCX handlers with intelligent chunking
- **Vector Search**: Semantic document retrieval and similarity
- **Analytics Engine**: Learning progress and personalized recommendations

## 🧪 Quality Assurance

### **Multi-Layer Validation System**
```bash
# Quick validation (5 tests, ~1 second)
python scripts/pre_merge_validation.py --quick

# Full validation (9 tests, ~45 seconds)  
python scripts/pre_merge_validation.py

# Production environment testing
python scripts/pre_merge_validation.py --environment prod
```

### **Automated Protection**
- **Pre-commit hooks**: Validate every commit automatically
- **GitHub Actions**: CI/CD pipeline with PR validation
- **Zero disruption guarantee**: All changes tested against existing functionality

### **Test Coverage**
- ✅ **442 tests collected** across all modules
- ✅ **Study Modes**: 30/30 comprehensive tests passing
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

## 🔮 Roadmap

### **Phase 1: Production Deployment**
- [x] **Security**: Environment-based secret management
- [x] **Validation**: Multi-layer testing system  
- [ ] **Infrastructure**: Docker containerization
- [ ] **Monitoring**: Structured logging and health checks

### **Phase 2: Advanced Features**
- [ ] **SocraticMode**: Guided questioning and discovery
- [ ] **DebateMode**: Argumentative learning
- [ ] **Voice Integration**: 11Labs TTS/STT
- [ ] **Multimodal**: Image and video processing

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