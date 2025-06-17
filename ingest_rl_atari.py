#!/usr/bin/env python3
"""
Simple script to ingest rl_atari.pdf into the RAG system.
This script will process the PDF and upload it to both Supabase and Weaviate.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.document_processor import DocumentProcessor
from src.file_handlers.pdf_handler import PDFHandler


async def main():
    """Ingest rl_atari.pdf into the RAG system."""
    
    # Check if file exists
    pdf_path = Path("raw_data/rl_atari.pdf")
    if not pdf_path.exists():
        print(f"❌ Error: {pdf_path} not found")
        return 1
    
    print(f"🔄 Processing {pdf_path}...")
    
    try:
        # Initialize document processor
        processor = DocumentProcessor()
        
        # Process document directly from file
        print("🔄 Processing document for RAG system...")
        result = processor.process_document(
            file_path=pdf_path,
            extract_metadata=True,
            processing_options={
                "chunk_size": 800,
                "overlap_size": 100
            }
        )
        
        print(f"✅ Document processed successfully!")
        print(f"   - File: {result.get('file_name', 'N/A')}")
        print(f"   - Size: {result.get('file_size', 'N/A')} bytes")
        print(f"   - Content length: {len(result.get('content', ''))} characters")
        print(f"   - Metadata: {result.get('metadata', {})}")
        
        # Store document in vector database
        print("🔄 Storing in vector database...")
        store_result = await processor.store_document(
            content=result.get('content', ''),
            title=result['metadata'].get('file_name', 'RL Atari Paper'),
            file_type=result['metadata'].get('file_extension', '.pdf'),
            file_size=result['metadata'].get('file_size', 0),
            user_id="test-user",
            metadata=result['metadata'],
            chunk_size=800,
            overlap=100
        )
        
        print(f"✅ Document stored successfully!")
        print(f"   - Document ID: {store_result.document_id}")
        print(f"   - Supabase ID: {store_result.supabase_id}")
        print(f"   - Chunks created: {store_result.chunks_created}")
        print(f"   - Status: {store_result.status}")
        print(f"   - Processing time: {store_result.processing_time:.2f}s" if store_result.processing_time else "")
        
        # Test a simple search
        print("\n🔍 Testing vector search...")
        # This will test if the document was properly embedded in Weaviate
        if processor.weaviate_client:
            search_results = await processor.weaviate_client.search_similar_chunks(
                query_text="reinforcement learning atari",
                limit=3
            )
            
            print(f"✅ Search test successful! Found {len(search_results)} results:")
            for i, result in enumerate(search_results[:2], 1):
                score = result.get('score', 0)
                if isinstance(score, (int, float)):
                    print(f"   {i}. Score: {score:.3f}")
                else:
                    print(f"   {i}. Score: {score}")
                print(f"      Content: {result.get('content', '')[:100]}...")
        else:
            print("⚠️  Weaviate client not available for search test")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)