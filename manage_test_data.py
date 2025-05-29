#!/usr/bin/env python3
"""
Test data management utility for Weaviate database.
Easily add, check, or remove demo data for development.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, 'src')

from weaviate_client import create_weaviate_client

# Standard demo data for consistent testing
DEMO_STUDY_MATERIALS = [
    {
        "content": "Python is a high-level, interpreted programming language with dynamic semantics. Its high-level built-in data structures, combined with dynamic typing and dynamic binding, make it very attractive for Rapid Application Development, as well as for use as a scripting or glue language to connect existing components together.",
        "metadata": {
            "title": "Python Programming Basics",
            "source": "demo_python_tutorial.pdf",
            "tags": ["python", "programming", "basics", "tutorial", "demo"],
            "supabase_id": "demo_1"
        }
    },
    {
        "content": "Machine learning is a method of data analysis that automates analytical model building. It is a branch of artificial intelligence based on the idea that systems can learn from data, identify patterns and make decisions with minimal human intervention.",
        "metadata": {
            "title": "Introduction to Machine Learning",
            "source": "demo_ml_fundamentals.pdf",
            "tags": ["machine-learning", "ai", "data-science", "patterns", "demo"],
            "supabase_id": "demo_2"
        }
    },
    {
        "content": "Vector databases are specialized databases designed to store, index, and query high-dimensional vector data efficiently. They use advanced indexing techniques like HNSW (Hierarchical Navigable Small World) or IVF (Inverted File) to enable fast similarity searches across millions or billions of vectors.",
        "metadata": {
            "title": "Vector Databases Explained",
            "source": "demo_vector_db_guide.pdf",
            "tags": ["vector-database", "indexing", "similarity-search", "hnsw", "demo"],
            "supabase_id": "demo_3"
        }
    },
    {
        "content": "Natural Language Processing (NLP) is a subfield of linguistics, computer science, and artificial intelligence concerned with the interactions between computers and human language, in particular how to program computers to process and analyze large amounts of natural language data.",
        "metadata": {
            "title": "Natural Language Processing Overview",
            "source": "demo_nlp_intro.pdf",
            "tags": ["nlp", "linguistics", "ai", "language-processing", "demo"],
            "supabase_id": "demo_4"
        }
    },
    {
        "content": "Deep learning is part of a broader family of machine learning methods based on artificial neural networks with representation learning. Learning can be supervised, semi-supervised or unsupervised. Deep neural networks, deep belief networks, recurrent neural networks and convolutional neural networks have been applied to fields such as computer vision, speech recognition, natural language processing.",
        "metadata": {
            "title": "Deep Learning Fundamentals",
            "source": "demo_deep_learning.pdf",
            "tags": ["deep-learning", "neural-networks", "ai", "computer-vision", "demo"],
            "supabase_id": "demo_5"
        }
    },
    {
        "content": "Flashcards are a study tool that helps with memorization through spaced repetition. The front of the card contains a question or prompt, while the back contains the answer or explanation. They are particularly effective for learning vocabulary, formulas, historical dates, and other factual information.",
        "metadata": {
            "title": "Effective Flashcard Study Methods",
            "source": "demo_study_techniques.pdf",
            "tags": ["flashcards", "spaced-repetition", "memorization", "study-methods", "demo"],
            "supabase_id": "demo_6"
        }
    }
]

def add_demo_data():
    """Add standard demo data to the database."""
    print("📚 Adding Demo Study Materials")
    print("=" * 40)

    with create_weaviate_client() as client:
        client.create_schema()

        # Check if demo data already exists
        existing_demo = client.hybrid_search("", filters={"tags": ["demo"]}, limit=1)
        if existing_demo:
            print("⚠️  Demo data already exists!")
            overwrite = input("   Overwrite existing demo data? (y/N): ").strip().lower()
            if overwrite != 'y':
                print("   Cancelled.")
                return

            # Remove existing demo data
            print("   🧹 Removing existing demo data...")
            remove_demo_data(client)

        print(f"\n📝 Adding {len(DEMO_STUDY_MATERIALS)} demo documents...")

        for i, material in enumerate(DEMO_STUDY_MATERIALS):
            doc_id = client.add_document(material["content"], material["metadata"])
            print(f"✅ {i+1}. {material['metadata']['title']}")

        total_count = client.get_document_count()
        print(f"\n📊 Total documents in database: {total_count}")
        print("🎉 Demo data added successfully!")

def check_database_status():
    """Check what's currently in the database."""
    print("📊 Database Status")
    print("=" * 40)

    with create_weaviate_client() as client:
        if not client.client.collections.exists("Document"):
            print("❌ Document collection doesn't exist yet")
            print("💡 Run: python manage_test_data.py add")
            return

        total_count = client.get_document_count()
        print(f"📈 Total documents: {total_count}")

        if total_count == 0:
            print("📭 Database is empty")
            print("💡 Run: python manage_test_data.py add")
            return

        # Check for demo data
        demo_results = client.hybrid_search("", filters={"tags": ["demo"]}, limit=20)
        demo_count = len(demo_results)
        real_count = total_count - demo_count

        print(f"🧪 Demo documents: {demo_count}")
        print(f"📚 Real documents: {real_count}")

        if demo_results:
            print("\n🧪 Demo Documents:")
            for i, doc in enumerate(demo_results, 1):
                print(f"   {i}. {doc.title}")

        # Show recent non-demo documents
        if real_count > 0:
            print("\n📚 Sample Real Documents:")
            # This would need refinement for excluding demo data
            all_results = client.semantic_search("", limit=10)
            non_demo = [doc for doc in all_results if "demo" not in doc.metadata.get("tags", [])][:5]
            for i, doc in enumerate(non_demo, 1):
                print(f"   {i}. {doc.title}")

def remove_demo_data(client=None):
    """Remove all demo data from the database."""
    should_close = False
    if client is None:
        client = create_weaviate_client()
        should_close = True

    try:
        # Find all demo documents
        demo_docs = client.hybrid_search("", filters={"tags": ["demo"]}, limit=100)

        if not demo_docs:
            print("ℹ️  No demo data found")
            return

        print(f"🧹 Removing {len(demo_docs)} demo documents...")

        removed_count = 0
        for doc in demo_docs:
            if client.delete_document(doc.id):
                removed_count += 1

        print(f"✅ Removed {removed_count} demo documents")
        print(f"📊 Remaining documents: {client.get_document_count()}")

    finally:
        if should_close:
            client.close()

def clean_all_data():
    """Remove ALL data from the database (use with caution!)."""
    print("⚠️  WARNING: This will delete ALL documents!")
    confirm = input("   Type 'DELETE ALL' to confirm: ").strip()

    if confirm != "DELETE ALL":
        print("   Cancelled.")
        return

    print("🧹 Deleting all documents...")

    with create_weaviate_client() as client:
        if client.client.collections.exists("Document"):
            # Delete the entire collection
            client.client.collections.delete("Document")
            print("✅ Document collection deleted")

            # Recreate schema
            client.create_schema()
            print("✅ Fresh schema created")

        print(f"📊 Final document count: {client.get_document_count()}")

def quick_test():
    """Run a quick test search on current data."""
    print("🔍 Quick Search Test")
    print("=" * 40)

    with create_weaviate_client() as client:
        count = client.get_document_count()
        if count == 0:
            print("📭 No data to search")
            return

        print(f"📊 Searching {count} documents...\n")

        test_queries = [
            "programming languages",
            "artificial intelligence",
            "study methods"
        ]

        for query in test_queries:
            print(f"🔎 '{query}':")
            results = client.semantic_search(query, limit=2)
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.title} (score: {result.score:.3f})")
            print()

def main():
    if len(sys.argv) < 2:
        print("🛠️  Test Data Management Utility")
        print("=" * 40)
        print("Usage:")
        print("  python manage_test_data.py <command>")
        print()
        print("Commands:")
        print("  add      - Add demo study materials")
        print("  status   - Check database status")
        print("  remove   - Remove demo data only")
        print("  clean    - Remove ALL data (careful!)")
        print("  test     - Quick search test")
        print()
        return

    command = sys.argv[1].lower()

    try:
        if command == "add":
            add_demo_data()
        elif command == "status":
            check_database_status()
        elif command == "remove":
            print("🧹 Removing Demo Data")
            print("=" * 40)
            remove_demo_data()
        elif command == "clean":
            clean_all_data()
        elif command == "test":
            quick_test()
        else:
            print(f"❌ Unknown command: {command}")
            print("💡 Run without arguments to see usage")

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
