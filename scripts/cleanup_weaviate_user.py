#!/usr/bin/env python3
"""
Simple Weaviate user data cleanup using the same pattern as document_processor.py
"""

import sys
sys.path.append('.')

from src.weaviate_client import create_weaviate_client
import weaviate.classes as wvc

def cleanup_weaviate_user(user_id: str):
    """Clean up all Weaviate data for a user."""
    try:
        weaviate_client = create_weaviate_client()
        print(f"🧹 Cleaning Weaviate data for user: {user_id}")
        
        collection = weaviate_client.client.collections.get("Document")
        
        # Delete all chunks for this user (using correct Weaviate v4 API)
        collection.data.delete_many(
            where=wvc.query.Filter.by_property("user_id").equal(user_id)
        )
        
        print(f"✅ Successfully deleted all Weaviate data for user: {user_id}")
        
    except Exception as e:
        print(f"❌ Error cleaning Weaviate data: {e}")
    finally:
        if 'weaviate_client' in locals():
            weaviate_client.close()

if __name__ == "__main__":
    demo_user_id = "550e8400-e29b-41d4-a716-446655440000"
    cleanup_weaviate_user(demo_user_id)