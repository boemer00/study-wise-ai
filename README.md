# StudyWise AI 🧠✨

> **Advanced AI-Powered Learning Platform with Feynman Technique Integration**

StudyWise AI is a revolutionary multimodal personal knowledge management system that transforms study materials into intelligent, interactive learning experiences. Featuring cutting-edge study modes including the **FeynmanMode** for teaching-based learning, real-time analytics, and voice AI compatibility.

## 🌟 Key Features

### 🧠 **Advanced Study Modes**
- **FeynmanMode**: Learn by teaching with real-time quality analysis
- **TraditionalMode**: Classic Q&A with adaptive difficulty
- **SocraticMode**: Guided questioning and critical thinking *(coming soon)*
- **DebateMode**: Argumentative learning and perspective analysis *(coming soon)*

### 🎯 **FeynmanMode Highlights**
- **Teaching Quality Scoring**: Real-time analysis of explanation clarity
- **Analogy Detection**: Automatic identification and counting of analogies
- **Simplicity Metrics**: Live simplicity scoring to encourage clear explanations
- **Knowledge Gap Identification**: AI detects uncertainty and vague terminology
- **Audience Progression**: Dynamic teaching for Child → Peer → Expert audiences
- **Session Analytics**: Comprehensive learning insights and personalized recommendations

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
├── Traditional Study Sessions
└── Document Management

⚡ FastAPI Backend
├── Study Modes Framework
├── FeynmanMode Engine (895 lines)
├── Session Management
└── Analytics Engine

🔍 Vector Database (Weaviate)
├── Document Embeddings (OpenAI)
├── Semantic Search
└── Context Retrieval

📊 Relational Database (Supabase)
├── User Sessions
├── Study Analytics
└── Progress Tracking
```

## 🚀 Implementation Status

### ✅ **Completed Features**

#### **🧠 Study Modes Framework**
- [x] **BaseStudyMode**: Abstract foundation for all learning modes
- [x] **FeynmanMode**: Complete implementation with 30/30 tests passing
- [x] **TraditionalMode**: Classic Q&A learning with spaced repetition
- [x] **Session Management**: Robust session lifecycle handling
- [x] **Analytics Engine**: Comprehensive learning insights

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
- [x] **Demo Scripts**: Live demonstration of FeynmanMode capabilities
- [x] **Production Ready**: Error handling and edge case management

### 🔮 **Future Enhancements**
- [ ] **SocraticMode**: Guided questioning and critical thinking
- [ ] **DebateMode**: Argumentative learning and perspective analysis
- [ ] **Voice Integration**: 11Labs TTS/STT for hands-free learning
- [ ] **Multimodal Support**: Image and video content processing
- [ ] **Advanced Analytics**: ML-powered learning optimization

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | React + TypeScript + Vite | Modern learning interface |
| **UI Library** | TailwindCSS + shadcn/ui | Beautiful, accessible components |
| **Backend** | FastAPI + Python 3.12 | High-performance API server |
| **Vector DB** | Weaviate Cloud | Semantic search & embeddings |
| **Database** | Supabase PostgreSQL | Structured data & analytics |
| **AI/ML** | OpenAI GPT-4 + Embeddings | Natural language processing |
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
│   └── 📁 (other test modules)/    # Additional test coverage
│
├── 📂 api/                          # FastAPI backend
│   ├── 🔧 core/                     # Core API configuration
│   ├── 📊 models/                   # API data models
│   └── 🛣️ routers/                  # API route handlers
│
├── 🎮 test_feynman_demo.py          # Live FeynmanMode demonstration
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
│   ├── 💬 ChatInterface.tsx         # AI conversation
│   ├── 📄 DocumentManager.tsx       # File upload and management
│   └── 📊 Dashboard.tsx             # Learning progress overview
├── 🔗 services/
│   └── 📡 api.ts                    # Study modes API integration
└── 🎨 (UI components and routing)   # Modern React architecture
```

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

# Live demonstration
python test_feynman_demo.py
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
