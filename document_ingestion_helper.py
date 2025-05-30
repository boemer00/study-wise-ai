#!/usr/bin/env python3
"""
Document Ingestion Helper for StudyWise AI Conversational RAG

This script helps you ingest and chunk your study documents into Weaviate
for use with the conversational RAG system.
"""

import asyncio
import os
import sys
import uuid
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Make sure to set environment variables manually.")

# Add src to path
sys.path.insert(0, 'src')

from weaviate_client import create_weaviate_client

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DocumentChunker:
    """Helper class for chunking documents."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings near the chunk boundary
                for boundary in ['. ', '.\n', '? ', '! ']:
                    boundary_pos = text.rfind(boundary, start, end)
                    if boundary_pos > start + self.chunk_size // 2:
                        end = boundary_pos + len(boundary)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = end - self.overlap
            if start >= len(text):
                break

        return chunks


class DocumentIngester:
    """Document ingestion manager for Weaviate."""

    def __init__(self):
        self.client = None
        self.chunker = DocumentChunker()

    async def connect(self):
        """Connect to Weaviate."""
        try:
            self.client = create_weaviate_client()
            logger.info("Connected to Weaviate successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise

    async def ingest_text_document(
        self,
        content: str,
        title: str,
        source: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest a text document by chunking and storing in Weaviate.

        Args:
            content: Document text content
            title: Document title
            source: Document source (file path, URL, etc.)
            document_id: Optional document ID (will generate if not provided)
            metadata: Optional metadata dictionary

        Returns:
            Ingestion result summary
        """
        try:
            if not self.client:
                await self.connect()

            document_id = document_id or str(uuid.uuid4())
            metadata = metadata or {}

            # Chunk the document
            chunks = self.chunker.chunk_text(content)
            logger.info(f"Created {len(chunks)} chunks for document: {title}")

            # Store chunks in Weaviate
            collection = self.client.client.collections.get("Document")
            chunk_ids = []

            for i, chunk_content in enumerate(chunks):
                chunk_id = f"{document_id}-chunk-{i+1}"

                chunk_data = {
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "title": title,
                    "content": chunk_content,
                    "page_number": i + 1,  # Using chunk number as page for text docs
                    "source": source,
                    "metadata": json.dumps({
                        **metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "chunk_length": len(chunk_content)
                    }),
                    "created_at": datetime.now(timezone.utc)
                }

                result = collection.data.insert(chunk_data)
                chunk_ids.append(str(result))
                logger.debug(f"Stored chunk {i+1}/{len(chunks)}: {chunk_id}")

            ingestion_result = {
                "document_id": document_id,
                "title": title,
                "source": source,
                "total_chunks": len(chunks),
                "chunk_ids": chunk_ids,
                "total_characters": len(content),
                "status": "success"
            }

            logger.info(f"Successfully ingested document: {title} ({len(chunks)} chunks)")
            return ingestion_result

        except Exception as e:
            logger.error(f"Failed to ingest document {title}: {e}")
            return {
                "document_id": document_id,
                "title": title,
                "source": source,
                "status": "error",
                "error": str(e)
            }

    async def ingest_file(
        self,
        file_path: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest a text file.

        Args:
            file_path: Path to the text file
            title: Optional title (will use filename if not provided)
            metadata: Optional metadata

        Returns:
            Ingestion result
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Read file content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            title = title or path.stem
            source = str(path.absolute())

            return await self.ingest_text_document(
                content=content,
                title=title,
                source=source,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to ingest file {file_path}: {e}")
            return {
                "title": title or file_path,
                "source": file_path,
                "status": "error",
                "error": str(e)
            }

    async def ingest_directory(
        self,
        directory_path: str,
        file_extensions: List[str] = ['.txt', '.md'],
        recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Ingest all text files in a directory.

        Args:
            directory_path: Path to directory
            file_extensions: List of file extensions to process
            recursive: Whether to process subdirectories

        Returns:
            List of ingestion results
        """
        try:
            directory = Path(directory_path)
            if not directory.exists():
                raise FileNotFoundError(f"Directory not found: {directory_path}")

            # Find all matching files
            pattern = "**/*" if recursive else "*"
            files = []
            for ext in file_extensions:
                files.extend(directory.glob(f"{pattern}{ext}"))

            logger.info(f"Found {len(files)} files to ingest in {directory_path}")

            # Ingest each file
            results = []
            for file_path in files:
                try:
                    result = await self.ingest_file(str(file_path))
                    results.append(result)

                    if result['status'] == 'success':
                        print(f"✅ {file_path.name}: {result['total_chunks']} chunks")
                    else:
                        print(f"❌ {file_path.name}: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    results.append({
                        "title": file_path.name,
                        "source": str(file_path),
                        "status": "error",
                        "error": str(e)
                    })

            return results

        except Exception as e:
            logger.error(f"Failed to ingest directory {directory_path}: {e}")
            return []

    def close(self):
        """Close the Weaviate connection."""
        if self.client:
            self.client.close()


async def main():
    """Main function for interactive document ingestion."""
    print("📚 StudyWise AI - Document Ingestion Helper")
    print("=" * 50)

    ingester = DocumentIngester()

    try:
        await ingester.connect()

        print("\nSelect ingestion mode:")
        print("1. Ingest single file")
        print("2. Ingest directory")
        print("3. Ingest sample text")
        print("4. Check current document count")

        choice = input("\nEnter choice (1-4): ").strip()

        if choice == "1":
            await ingest_single_file(ingester)
        elif choice == "2":
            await ingest_directory(ingester)
        elif choice == "3":
            await ingest_sample_text(ingester)
        elif choice == "4":
            await check_document_count(ingester)
        else:
            print("Invalid choice")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        ingester.close()


async def ingest_single_file(ingester: DocumentIngester):
    """Interactive single file ingestion."""
    file_path = input("Enter file path: ").strip()
    title = input("Enter title (optional, press Enter to use filename): ").strip()

    title = title if title else None

    print(f"\n📄 Ingesting file: {file_path}")
    result = await ingester.ingest_file(file_path, title=title)

    if result['status'] == 'success':
        print(f"✅ Success! Created {result['total_chunks']} chunks")
        print(f"   Document ID: {result['document_id']}")
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")


async def ingest_directory(ingester: DocumentIngester):
    """Interactive directory ingestion."""
    dir_path = input("Enter directory path: ").strip()
    extensions = input("Enter file extensions (default: .txt,.md): ").strip()
    recursive = input("Recursive? (y/n, default: y): ").strip().lower()

    if not extensions:
        extensions = ".txt,.md"
    ext_list = [ext.strip() for ext in extensions.split(',')]

    is_recursive = recursive != 'n'

    print(f"\n📁 Ingesting directory: {dir_path}")
    print(f"   Extensions: {ext_list}")
    print(f"   Recursive: {is_recursive}")

    results = await ingester.ingest_directory(dir_path, ext_list, is_recursive)

    success_count = sum(1 for r in results if r['status'] == 'success')
    total_chunks = sum(r.get('total_chunks', 0) for r in results if r['status'] == 'success')

    print(f"\n📊 Summary:")
    print(f"   Files processed: {len(results)}")
    print(f"   Successful: {success_count}")
    print(f"   Total chunks created: {total_chunks}")


async def ingest_sample_text(ingester: DocumentIngester):
    """Ingest sample text for testing."""
    sample_text = """
Machine Learning Fundamentals

Machine learning is a method of data analysis that automates analytical model building. It is a branch of artificial intelligence based on the idea that systems can learn from data, identify patterns and make decisions with minimal human intervention.

Types of Machine Learning:

1. Supervised Learning
Supervised learning uses labeled training data to learn a mapping function from input variables to output variables. Common algorithms include linear regression, decision trees, and neural networks.

2. Unsupervised Learning
Unsupervised learning finds hidden patterns in data without labeled examples. This includes clustering algorithms like k-means and dimensionality reduction techniques like PCA.

3. Reinforcement Learning
Reinforcement learning involves an agent learning to make decisions by taking actions in an environment to maximize cumulative reward. This is used in applications like game playing and robotics.

Key Concepts:

Training Data: The dataset used to teach the machine learning algorithm.
Features: Individual measurable properties of observed phenomena.
Model: The mathematical representation of a real-world process.
Algorithm: The method used to build the machine learning model.
Prediction: The output of a model when given new input data.

Applications of machine learning include recommendation systems, image recognition, natural language processing, autonomous vehicles, and medical diagnosis.
    """.strip()

    print("\n📝 Ingesting sample machine learning text...")
    result = await ingester.ingest_text_document(
        content=sample_text,
        title="Machine Learning Fundamentals",
        source="sample_text",
        metadata={"type": "sample", "subject": "machine_learning"}
    )

    if result['status'] == 'success':
        print(f"✅ Success! Created {result['total_chunks']} chunks")
        print(f"   Document ID: {result['document_id']}")
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")


async def check_document_count(ingester: DocumentIngester):
    """Check current document count in Weaviate."""
    try:
        collection = ingester.client.client.collections.get("Document")

        # Get total count
        response = collection.aggregate.over_all(total_count=True)
        total_count = response.total_count

        print(f"\n📊 Current Document Chunks in Weaviate: {total_count}")

        if total_count > 0:
            # Get sample of recent documents
            recent = collection.query.fetch_objects(limit=5)
            print(f"\n📄 Recent Documents:")
            for obj in recent.objects:
                title = obj.properties.get('title', 'Unknown')
                chunk_id = obj.properties.get('chunk_id', 'Unknown')
                content_preview = obj.properties.get('content', '')[:100] + '...'
                print(f"   - {title} ({chunk_id})")
                print(f"     {content_preview}")

    except Exception as e:
        print(f"❌ Error checking document count: {e}")


if __name__ == "__main__":
    asyncio.run(main())
