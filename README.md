# Study-Wise AI 🧠

A multimodal personal knowledge management system that transforms study materials into searchable vector embeddings and interactive flashcards using advanced AI technologies.

## 🏗️ Architecture Overview

Study-Wise AI implements a **hybrid database architecture** combining the strengths of both vector and relational databases:

- **🔍 Weaviate (Vector Database)**: Semantic search across documents using OpenAI embeddings
- **📊 Supabase (PostgreSQL)**: Structured data storage for flashcards and user management
- **🤖 OpenAI Integration**: Text embeddings and flashcard generation
- **⚡ FastAPI**: RESTful API endpoints for semantic search
- **🖥️ CLI Tools**: Command-line interface for data management

### Why This Architecture?

We chose this hybrid approach over pgvector for several key reasons:

1. **Native Multimodal Support**: Weaviate provides built-in CLIP and Whisper integration for future video/image processing
2. **Cross-Modal Search**: Search text and find related images/videos seamlessly
3. **Specialized Performance**: Each database optimized for its specific use case
4. **Scalability**: Independent scaling of vector operations and structured data

## 🚀 Current Implementation Status

### ✅ Completed (Steps 1-3.1)

#### **Step 1: Design** ✅
- [x] Module architecture and responsibilities defined
- [x] Public interfaces and data models designed
- [x] Vector database strategy documented

#### **Step 2: Scaffold** ✅
- [x] Complete file structure with type hints and docstrings
- [x] Test file scaffolds created
- [x] Dependencies and configuration setup
- [x] Pytest configuration optimized

#### **Step 3.1: WeaviateClient Implementation** ✅
- [x] **WeaviateClient**: Complete vector operations with OpenAI embeddings
- [x] **Schema Management**: Automatic Document schema creation
- [x] **Semantic Search**: Hybrid search with proper similarity scoring
- [x] **Context Manager**: Robust connection handling
- [x] **Error Handling**: Comprehensive exception management
- [x] **Demo Data**: 12+ test documents for development

### 🚧 In Progress (Step 3.2)
- [ ] **DocumentProcessor**: Integration between Supabase and Weaviate
- [ ] **SemanticSearchAPI**: FastAPI endpoints implementation
- [ ] **CLI Interface**: Management commands for production use

### ⏳ Planned (Steps 3.3-4)
- [ ] Integration tests and documentation
- [ ] Multimodal extensions (images, videos)
- [ ] Production deployment configuration

## 🛠️ Technologies Used

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Vector Database** | Weaviate Cloud | 1.30.4 | Semantic search & embeddings |
| **Relational Database** | Supabase PostgreSQL | Latest | Structured data & user management |
| **Embeddings** | OpenAI text-embedding-3-small | Latest | Text vectorization |
| **API Framework** | FastAPI | ≥0.104.0 | RESTful API endpoints |
| **HTTP Client** | httpx | Latest | Async HTTP operations |
| **Testing** | pytest | Latest | Unit and integration tests |
| **Environment** | python-dotenv | Latest | Configuration management |

## 📁 Project Structure

```
study-wise-ai/
├── 📂 src/                          # Main implementation
│   ├── 🔹 weaviate_client.py        # ✅ Vector database operations
│   ├── 🔸 document_processor.py     # 🚧 Document pipeline integration
│   ├── 🔸 semantic_search_api.py    # 🚧 FastAPI endpoints
│   ├── 🔸 cli.py                    # 🚧 Command-line interface
│   └── 🔹 supabase_client.py        # ✅ Database connection utility
│
├── 📂 tests/                        # Test suite (25/25 passing)
│   ├── 🔹 test_weaviate_client.py   # ✅ Vector operations tests
│   ├── 🔸 test_document_processor.py # 🚧 Integration tests
│   ├── 🔸 test_semantic_search_api.py # 🚧 API endpoint tests
│   └── 🔸 test_cli.py               # 🚧 CLI functionality tests
│
├── 📂 archive_legacy/               # Archived flashcard system
│   ├── 📂 src/                     # Original implementation
│   └── 📂 tests/                   # Legacy test files
│
├── 📂 notebooks/                    # Jupyter analysis notebooks
├── 📂 raw_data/                     # Source materials storage
│
├── 🔧 requirements.txt              # Python dependencies
├── 🔧 pytest.ini                   # Test configuration
├── 🔧 .env.example                  # Environment template
├── 🔧 .gitignore                    # Git exclusions
├── 🔧 .python-version               # Python version lock
│
├── 🛠️ manage_test_data.py           # Demo data management utility
├── 📋 VECTOR_DATABASE_STRATEGY.md   # Architecture decision record
└── 📖 README.md                     # This documentation
```

### Legend
- 🔹 **Completed**: Fully implemented and tested
- 🔸 **Scaffold**: Interface defined, implementation pending
- 🚧 **In Progress**: Currently being developed

## ⚙️ Setup Instructions

### 1. Prerequisites

- **Python 3.12+** (managed via pyenv)
- **Weaviate Cloud** account and cluster
- **Supabase** project with PostgreSQL database
- **OpenAI API** key for embeddings

### 2. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd study-wise-ai

# Create virtual environment
python -m venv study-env
source study-env/bin/activate  # macOS/Linux
# or: study-env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create `.env` file with your credentials:

```env
# Weaviate Configuration
WEAVIATE_URL=https://your-cluster-id.weaviate.network
WEAVIATE_API_KEY=your-weaviate-api-key

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
```

### 4. Database Setup

```bash
# Test connections
python -c "from src.weaviate_client import create_weaviate_client; print('Weaviate: OK')"
python -c "from src.supabase_client import get_supabase_client; print('Supabase: OK')"

# Initialize Weaviate schema
python -c "
from src.weaviate_client import create_weaviate_client
with create_weaviate_client() as client:
    client.create_schema()
    print('Schema created successfully')
"
```

## 🎯 Current Features

### ✅ **Vector Search & Embeddings**

```python
from src.weaviate_client import create_weaviate_client

# Add documents to vector database
with create_weaviate_client() as client:
    doc_id = client.add_document(
        content="Machine learning is a subset of AI...",
        metadata={
            "title": "ML Introduction",
            "source": "textbook.pdf",
            "tags": ["ai", "machine-learning"]
        }
    )

# Semantic search
results = client.semantic_search("neural networks", limit=5)
for result in results:
    print(f"{result.title}: {result.score:.3f}")
```

### ✅ **Flashcard System Integration**

```python
from src.supabase_client import get_supabase_client

# Query flashcards
supabase = get_supabase_client()
flashcards = supabase.table('flashcards').select('*').limit(10).execute()
```

### ✅ **Demo Data Management**

```bash
# Add demo study materials
python manage_test_data.py add

# Check database status
python manage_test_data.py status

# Test semantic search
python manage_test_data.py test

# Remove demo data
python manage_test_data.py remove
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# All tests
pytest

# Specific test files
pytest tests/test_weaviate_client.py -v

# With coverage
pytest --cov=src tests/
```

**Current Status**: 25/25 tests passing ✅

## 📊 Performance Metrics

### Vector Search Performance
- **Embedding Model**: OpenAI text-embedding-3-small (1536 dimensions)
- **Search Latency**: ~200-500ms per query
- **Similarity Scores**: 0.6-0.8+ for relevant matches
- **Index Size**: 16 documents (demo), scales to millions

### Database Statistics
- **Weaviate**: 16 documents indexed
- **Supabase**: 65+ flashcards stored
- **Search Accuracy**: High semantic relevance without keyword dependency

## 🔍 Usage Examples

### Semantic Search Demo

```python
# Search finds conceptually related content without exact keywords
queries = [
    "programming languages",           # → Python content (0.677)
    "artificial intelligence",        # → ML content (0.716)
    "data structures and algorithms", # → Programming content (0.698)
    "machine learning applications"   # → AI applications (0.785)
]
```

### Cross-System Integration

```python
# Find documents in Weaviate
vector_results = client.semantic_search("supervised learning")

# Find related flashcards in Supabase
flashcards = supabase.table('flashcards').select('*').ilike(
    'question', '%supervised%'
).execute()
```

## 🚨 Known Issues & Limitations

### Minor Issues
- **SSL Warnings**: Harmless connection warnings in logs
- **Timezone Warnings**: Datetime objects default to UTC
- **Empty Search**: Weaviate API v4 change affects empty query handling

### Current Limitations
- **Text Only**: Multimodal support (images/videos) not yet implemented
- **Single User**: User management system pending
- **Basic CLI**: Advanced management features in development

## 🛣️ Roadmap

### **Next: Step 3.2 - DocumentProcessor** 🎯
- Bridge Supabase structured data with Weaviate vectors
- Automated document pipeline from upload to searchable embeddings
- Synchronization between both database systems

### **Upcoming: Step 3.3 - API & CLI**
- FastAPI endpoints for semantic search
- Production-ready CLI management tools
- Comprehensive integration testing

### **Future: Multimodal Extensions**
- Image and video content processing
- CLIP embeddings for visual search
- Whisper integration for audio transcription

## 🤝 Contributing

This project follows a **strict 4-step iterative workflow**:

1. **Design**: Define interfaces and responsibilities
2. **Scaffold**: Create typed function signatures and tests
3. **Implement**: Build working functionality
4. **Test**: Comprehensive testing and validation

Each step requires completion and approval before proceeding to the next.

## 📄 License

[Your chosen license]

## 🔗 Additional Resources

- **[Vector Database Strategy](VECTOR_DATABASE_STRATEGY.md)**: Detailed comparison of Weaviate vs pgvector
- **[Supabase Setup](README_SUPABASE.md)**: Database schema and configuration
- **[Weaviate Documentation](https://weaviate.io/developers/weaviate)**: Official API reference
- **[OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)**: Embedding model details

---

**Built with ❤️ for intelligent learning and knowledge management**
