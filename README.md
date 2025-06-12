# StudyWise AI 🧠✨

> **Advanced AI-Powered Learning Platform with FSRS Spaced Repetition**

StudyWise AI is a revolutionary multimodal personal knowledge management system that transforms study materials into intelligent, interactive learning experiences. Featuring cutting-edge study modes including the **FeynmanMode** for teaching-based learning, **FSRS-powered flashcard system** for optimal memory retention, real-time analytics, and voice AI compatibility.

## 🌟 Key Features

### 🧠 **Advanced Study Modes**
- **FeynmanMode**: Learn by teaching with real-time quality analysis
- **TraditionalMode**: Classic Q&A with adaptive difficulty
- **FSRS Flashcards**: Scientific spaced repetition for maximum retention
- **SocraticMode**: Guided questioning and critical thinking *(coming soon)*
- **DebateMode**: Argumentative learning and perspective analysis *(coming soon)*

### 🎯 **FeynmanMode Highlights**
- **Teaching Quality Scoring**: Real-time analysis of explanation clarity
- **Analogy Detection**: Automatic identification and counting of analogies
- **Simplicity Metrics**: Live simplicity scoring to encourage clear explanations
- **Knowledge Gap Identification**: AI detects uncertainty and vague terminology
- **Audience Progression**: Dynamic teaching for Child → Peer → Expert audiences
- **Session Analytics**: Comprehensive learning insights and personalized recommendations

### 🧮 **FSRS Spaced Repetition System**
- **Modern Algorithm**: FSRS (Free Spaced Repetition Scheduler) with 17 optimized parameters
- **Intelligent Scheduling**: Scientific intervals based on memory research
- **4-Point Rating System**: Again (10min) → Hard (1 day) → Good (4 days) → Easy (6 days)
- **Adaptive Difficulty**: Dynamic difficulty adjustment based on performance
- **Production Ready**: UUID-based authentication with robust error handling
- **API Integration**: RESTful endpoints for seamless frontend integration

### 🔍 **Intelligent Search & Processing**
- **Hybrid Database Architecture**: Weaviate (vector) + Supabase (relational)
- **Semantic Document Search**: OpenAI embeddings with similarity scoring
- **PDF/DOCX Support**: Advanced document processing and chunking
- **Conversational AI**: Interactive Q&A with document context

### 🎮 **Modern Learning Experience**
- **React + TypeScript Frontend**: Beautiful, responsive study interface
- **Real-time Feedback**: Live teaching analysis and improvement suggestions
- **Voice AI Ready**: Prepared for 11Labs TTS/STT integration
- **Mobile Responsive**: Seamless learning across all devices

## 🏗️ Architecture Overview

StudyWise AI implements a **sophisticated multi-tier architecture** optimized for advanced learning experiences:

```
🌐 Frontend (React + TypeScript)
├── Study Modes Hub (Mode Selection)
├── FeynmanMode Interface (Teaching Analytics)
├── FSRS Flashcard System (Spaced Repetition)
├── Traditional Study Sessions
└── Document Management

⚡ FastAPI Backend
├── Study Modes Framework
├── FeynmanMode Engine (895 lines)
├── FSRS Scheduler (957 lines)
├── Session Management
└── Analytics Engine

🔍 Vector Database (Weaviate)
├── Document Embeddings (OpenAI)
├── Semantic Search
└── Context Retrieval

📊 Relational Database (Supabase)
├── User Sessions
├── FSRS Card States
├── Review History
└── Study Analytics
```

## 🚀 Implementation Status

### ✅ **Completed Features**

#### **🧠 Study Modes Framework**
- [x] **BaseStudyMode**: Abstract foundation for all learning modes
- [x] **FeynmanMode**: Complete implementation with 30/30 tests passing
- [x] **TraditionalMode**: Classic Q&A learning with spaced repetition
- [x] **Session Management**: Robust session lifecycle handling
- [x] **Analytics Engine**: Comprehensive learning insights

#### **🧮 FSRS Spaced Repetition System** *(NEW)*
- [x] **FSRS Algorithm**: Complete implementation with 17 parameters
- [x] **Card Scheduling**: Intelligent review intervals based on performance
- [x] **Review Processing**: 4-point rating system (Again/Hard/Good/Easy)
- [x] **Database Integration**: FSRS states and review history tracking
- [x] **API Endpoints**: Production-ready flashcard management
- [x] **UUID Authentication**: Secure user session management
- [x] **Error Handling**: Robust fallback logic and debugging
- [x] **Migration Tools**: Scripts for card migration and testing
- [x] **Timezone Support**: Proper datetime handling across systems

#### **🎯 FeynmanMode Implementation**
- [x] **Teaching Analysis**: Real-time quality scoring and feedback
- [x] **Simplicity Scoring**: Algorithmic assessment of explanation clarity
- [x] **Analogy Detection**: Pattern recognition for teaching metaphors
- [x] **Knowledge Gap Identification**: AI-powered uncertainty detection
- [x] **Audience Progression**: Dynamic difficulty adjustment
- [x] **Session Analytics**: Detailed progress and recommendation system

#### **🔍 Vector Search & Processing**
- [x] **WeaviateClient**: Complete vector operations with OpenAI embeddings
- [x] **Document Processing**: PDF/DOCX upload and chunking
- [x] **Semantic Search**: Hybrid search with similarity scoring
- [x] **Context Retrieval**: Intelligent document context extraction

#### **🌐 Frontend Integration**
- [x] **Study Modes Hub**: Modern mode selection interface
- [x] **FeynmanMode UI**: Advanced teaching interface with real-time analytics
- [x] **Document Management**: Upload and organize study materials
- [x] **Chat Interface**: Conversational AI with document context

#### **🧪 Testing & Quality**
- [x] **Comprehensive Test Suite**: 30+ tests covering all functionality
- [x] **Integration Tests**: End-to-end workflow validation
- [x] **Demo Scripts**: Live demonstration of FeynmanMode and FSRS capabilities
- [x] **Production Ready**: Error handling and edge case management

### 🔮 **Future Enhancements**
- [ ] **SocraticMode**: Guided questioning and critical thinking
- [ ] **DebateMode**: Argumentative learning and perspective analysis
- [ ] **Voice Integration**: 11Labs TTS/STT for hands-free learning
- [ ] **Multimodal Support**: Image and video content processing
- [ ] **Advanced Analytics**: ML-powered learning optimization
- [ ] **FSRS Parameter Optimization**: Personalized algorithm tuning

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | React + TypeScript + Vite | Modern learning interface |
| **UI Library** | TailwindCSS + shadcn/ui | Beautiful, accessible components |
| **Backend** | FastAPI + Python 3.12 | High-performance API server |
| **Vector DB** | Weaviate Cloud | Semantic search & embeddings |
| **Database** | Supabase PostgreSQL | Structured data & analytics |
| **AI/ML** | OpenAI GPT-4 + Embeddings | Natural language processing |
| **Spaced Repetition** | FSRS Algorithm | Scientific memory optimization |
| **Testing** | pytest + React Testing Library | Comprehensive test coverage |

## 📁 Project Structure

```
study-wise-ai/
├── 📂 src/
│   ├── 🧠 study_modes/              # Advanced learning modes
│   │   ├── 📁 modes/                # Study mode implementations
│   │   │   ├── ✅ base_mode.py      # Abstract base class
│   │   │   ├── 🎯 feynman_mode.py   # Teaching-based learning (895 lines)
│   │   │   ├── 📚 traditional_mode.py # Classic Q&A learning
│   │   │   ├── ❓ socratic_mode.py   # Guided questioning (scaffold)
│   │   │   └── 💬 debate_mode.py     # Argumentative learning (scaffold)
│   │   ├── 📁 models/               # Data models and schemas
│   │   │   ├── 📊 study_session.py  # Session management models
│   │   │   └── 📈 analytics.py      # Learning analytics models
│   │   ├── 📁 session/              # Session management
│   │   │   └── 🔄 session_manager.py # Session lifecycle handling
│   │   └── 🎮 study_mode_manager.py # Mode coordination
│   ├── 🧮 flashcards/               # FSRS spaced repetition system
│   │   ├── ⚡ scheduler.py          # FSRS scheduler (957 lines)
│   │   ├── 🧠 fsrs.py               # Core FSRS algorithm
│   │   ├── 📊 models.py             # FSRS data models
│   │   └── 🔧 flashcards_db.py      # Database operations
│   ├── 💬 conversation/             # Chat and dialogue systems
│   ├── 📄 file_handlers/            # Document processing
│   └── 🔍 (vector search components) # Weaviate integration
│
├── 📂 tests/
│   ├── 🧠 study_modes/              # Study modes test suite
│   │   ├── ✅ test_feynman_comprehensive.py # 20 comprehensive tests
│   │   ├── 🎯 test_feynman_mode.py         # 10 core functionality tests
│   │   ├── 📊 test_session_manager.py      # Session management tests
│   │   └── 🔧 (additional test modules)    # Foundation and integration tests
│   ├── 🧮 flashcards/               # FSRS test suite
│   │   └── ✅ test_fsrs_integration.py     # FSRS algorithm tests
│   └── 📁 (other test modules)/    # Additional test coverage
│
├── 📂 api/                          # FastAPI backend
│   ├── 🔧 core/                     # Core API configuration
│   ├── 📊 models/                   # API data models
│   └── 🛣️ routers/                  # API route handlers
│       └── 🧮 flashcards.py        # FSRS API endpoints
│
├── 🎮 test_feynman_demo.py          # Live FeynmanMode demonstration
├── 🧮 demo_spaced_repetition.py     # Live FSRS demonstration
├── 🔄 test_migration.py             # FSRS card migration script
├── 🚀 start_api.py                  # API server launcher
├── 📋 requirements.txt              # Python dependencies
└── 📖 README.md                     # This documentation
```

### Frontend Structure (study-wise-frontend/)
```
src/
├── 📱 components/
│   ├── 🧠 StudyModesHub.tsx         # Mode selection interface
│   ├── 🎯 FeynmanSession.tsx        # Teaching interface with analytics
│   ├── 🧮 FlashcardReview.tsx       # FSRS flashcard interface
│   ├── 💬 ChatInterface.tsx         # AI conversation
│   ├── 📄 DocumentManager.tsx       # File upload and management
│   └── 📊 Dashboard.tsx             # Learning progress overview
├── 🔗 services/
│   └── 📡 api.ts                    # Study modes and FSRS API integration
└── 🎨 (UI components and routing)   # Modern React architecture
```

## 🧮 FSRS Spaced Repetition System

### **How It Works**

The FSRS (Free Spaced Repetition Scheduler) system uses cutting-edge research in memory science to optimize learning retention:

1. **Initial Review**: New cards are shown immediately
2. **Performance Rating**: User rates difficulty (Again/Hard/Good/Easy)
3. **Intelligent Scheduling**: Algorithm calculates optimal next review interval
4. **Adaptive Difficulty**: System learns from user performance patterns

### **Rating System**
- **🔴 Again (1)**: Review in 10 minutes
- **🟡 Hard (2)**: Review in 1 day
- **🟢 Good (3)**: Review in 4 days
- **🔵 Easy (4)**: Review in 6+ days

### **Key Benefits**
- **Scientific Accuracy**: Based on latest memory research
- **Personalized Learning**: Adapts to individual performance
- **Optimal Efficiency**: Minimal reviews for maximum retention
- **Production Ready**: Robust error handling and UUID authentication

### **API Endpoints**
```
GET /api/v1/flashcards/due-today        # Get cards due for review
POST /api/v1/flashcards/{id}/review     # Record review with rating
GET /api/v1/flashcards/stats/overview   # Get learning statistics
```

### **Demo Scripts**
- `demo_spaced_repetition.py`: Live FSRS demonstration
- `test_migration.py`: Card migration to FSRS system

## ⚙️ Setup Instructions

### 1. Prerequisites

- **Python 3.12+** with pyenv
- **Node.js 18+** for frontend
- **Weaviate Cloud** account
- **Supabase** project
- **OpenAI API** key

### 2. Backend Setup

```bash
# Clone and setup
git clone <repository-url>
cd study-wise-ai

# Python environment
python -m venv study-env
source study-env/bin/activate
pip install -r requirements.txt

# Environment configuration
cp .env.example .env
# Edit .env with your API keys
```

### 3. Frontend Setup

```bash
# Setup frontend
cd ../study-wise-frontend
npm install
npm run dev  # Starts on http://localhost:8080
```

### 4. Launch Application

```bash
# Terminal 1: Backend API
cd study-wise-ai
python start_api.py  # Starts on http://localhost:8000

# Terminal 2: Frontend
cd study-wise-frontend
npm run dev  # Starts on http://localhost:8080
```

## 🎯 Usage Examples

### 🧠 **FeynmanMode Session**

```python
# Start a FeynmanMode session
from src.study_modes.modes.feynman_mode import FeynmanMode

feynman = FeynmanMode(
    documents=['neural_networks.pdf'],
    user_id='student-123',
    difficulty_level=2
)

# Generate teaching prompt
prompt = await feynman.generate_initial_prompt()
print(prompt.prompt_text)
# "Explain neural networks to a classmate who's hearing about it for the first time..."

# Process teaching attempt
response = await feynman.process_user_response(
    "Neural networks are like the human brain, with layers that process information...",
    prompt
)

print(f"Teaching Quality: {response.metadata['teaching_quality_score']:.2f}")
print(f"Analogies Detected: {response.metadata['analogies_detected']}")
print(f"Progress: {response.progress_percentage:.1f}%")
```

### 🧮 **FSRS Spaced Repetition**

```python
# Demonstration of FSRS scheduling system
from src.flashcards.scheduler import get_due_cards, review_card
from src.flashcards.models import CardRating

# Get cards due for review today
user_id = "550e8400-e29b-41d4-a716-446655440000"  # UUID format
due_cards = get_due_cards(user_id, limit=10)
print(f"Cards due today: {len(due_cards)}")

# Review cards with FSRS ratings
for card in due_cards[:3]:
    card_id = card['flashcard_id']

    # User rates difficulty: 1=Again, 2=Hard, 3=Good, 4=Easy
    rating = CardRating.GOOD  # 3 - Good performance

    # Process review and get next scheduled date
    result = review_card(card_id, user_id, rating)
    print(f"Card {card_id}: Next review {result.next_due_date}")
    print(f"Interval: {result.interval_days} days")

# Cards are automatically excluded from future "due today" lists
remaining_cards = get_due_cards(user_id, limit=10)
print(f"Cards still due: {len(remaining_cards)}")
```

### 🎮 **Frontend Interface**

Access the modern learning interface:

1. **📊 Dashboard**: http://localhost:8080/dashboard
2. **🧠 Study Modes**: http://localhost:8080/study
3. **💬 AI Chat**: http://localhost:8080/chat
4. **📄 Documents**: http://localhost:8080/documents

## 📊 FeynmanMode Analytics

### **Real-time Teaching Metrics**
- **Simplicity Score**: 0.0-1.0 (higher = clearer explanation)
- **Teaching Quality**: Composite score based on clarity, analogies, structure
- **Analogy Count**: Number of teaching metaphors detected
- **Knowledge Gaps**: Areas of uncertainty identified
- **Audience Appropriateness**: How well explanation matches target audience

### **Session Analytics**
```python
# Get comprehensive session summary
summary = await feynman.generate_session_summary(user_responses)

{
    'teaching_attempts': 5,
    'average_teaching_quality': 0.78,
    'concepts_covered': ['neural networks', 'backpropagation'],
    'analogies_used': 8,
    'feynman_mastery_level': 0.83,
    'recommendations': [
        'Try explaining to different audiences',
        'Focus on simpler analogies for complex concepts'
    ]
}
```

## 🧪 Testing

### **Run Test Suite**
```bash
# All tests
pytest

# FeynmanMode specific
pytest tests/study_modes/test_feynman_comprehensive.py -v

# FSRS spaced repetition
pytest tests/flashcards/ -v

# Live demonstrations
python test_feynman_demo.py
python demo_spaced_repetition.py
```

### **Test Coverage**
- **30/30 tests passing** ✅
- **FeynmanMode**: 20 comprehensive functionality tests
- **Session Management**: 5 integration tests
- **Base Framework**: 5 foundation tests

## 🔮 Future Roadmap

### **Phase 1: Voice Integration** 🎤
- 11Labs TTS/STT integration
- Hands-free learning experience
- Voice-optimized prompts and feedback

### **Phase 2: Advanced Modes** 🧩
- **SocraticMode**: Guided questioning and discovery
- **DebateMode**: Argumentative learning and critical analysis
- **CollaborativeMode**: Peer-to-peer learning sessions

### **Phase 3: Multimodal Learning** 🎨
- Image and video content processing
- Visual concept mapping
- Interactive diagrams and animations

### **Phase 4: AI Optimization** 🤖
- Personalized learning path generation
- Adaptive difficulty algorithms
- Predictive analytics for learning outcomes

## 🤝 Contributing

StudyWise AI follows a **strict four-step development workflow**:

1. **Design**: Define module responsibilities and interfaces
2. **Scaffold**: Create file structures with type hints and docstrings
3. **Implement**: Fill scaffolds with working code
4. **Test**: Comprehensive pytest coverage

See our [contributing guidelines](CONTRIBUTING.md) for detailed development processes.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎓 Acknowledgments

- **Richard Feynman** for the teaching-based learning methodology
- **OpenAI** for advanced language models and embeddings
- **Weaviate** for vector database technology
- **Supabase** for backend-as-a-service platform

---

**StudyWise AI - Transforming Learning Through Teaching** 🧠✨

*Built with ❤️ using modern AI and educational psychology principles*
