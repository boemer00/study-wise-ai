#!/usr/bin/env python3
"""
User data cleanup utility for StudyWise AI.
Removes all user data from both Supabase and Weaviate.
"""

import os
import sys
sys.path.append('.')

from src.supabase_client import get_supabase_client
from src.weaviate_client import create_weaviate_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_user_data(user_id: str, confirm: bool = False):
    """
    Remove all data for a specific user from both databases.
    
    Args:
        user_id: The user ID to clean up
        confirm: If True, actually perform the deletion
    """
    if not confirm:
        print("⚠️  DRY RUN MODE - No data will be deleted")
        print("Use --confirm to actually delete data")
    
    print(f"🧹 Cleaning up data for user: {user_id}")
    
    # Initialize clients
    try:
        supabase_client = get_supabase_client()
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return False
    
    try:
        weaviate_client = create_weaviate_client()
        print("✅ Connected to Weaviate")
    except Exception as e:
        print(f"❌ Failed to connect to Weaviate: {e}")
        weaviate_client = None
    
    # 1. Clean up Supabase data
    try:
        # Count documents
        docs_result = supabase_client.table('documents').select('document_id').eq('user_id', user_id).execute()
        doc_count = len(docs_result.data) if docs_result.data else 0
        print(f"📄 Found {doc_count} documents in Supabase")
        
        if confirm and doc_count > 0:
            # Delete documents
            delete_result = supabase_client.table('documents').delete().eq('user_id', user_id).execute()
            print(f"✅ Deleted {doc_count} documents from Supabase")
        
        # Count flashcards (if table exists)
        try:
            cards_result = supabase_client.table('flashcards').select('id').eq('user_id', user_id).execute()
            card_count = len(cards_result.data) if cards_result.data else 0
            print(f"🃏 Found {card_count} flashcards in Supabase")
            
            if confirm and card_count > 0:
                delete_result = supabase_client.table('flashcards').delete().eq('user_id', user_id).execute()
                print(f"✅ Deleted {card_count} flashcards from Supabase")
        except Exception as e:
            print(f"ℹ️  No flashcards table or no flashcards found: {e}")
        
    except Exception as e:
        print(f"❌ Error cleaning Supabase data: {e}")
        return False
    
    # 2. Clean up Weaviate data
    if weaviate_client:
        try:
            collection = weaviate_client.client.collections.get("Document")
            
            # Count chunks by querying first
            import weaviate.classes as wvc
            try:
                response = collection.query.fetch_objects(
                    where=wvc.query.filter.by_property("user_id").equal(user_id),
                    limit=1000  # Get up to 1000 to count
                )
                chunk_count = len(response.objects)
                print(f"🔍 Found {chunk_count} chunks in Weaviate")
                
                if confirm and chunk_count > 0:
                    # Delete all chunks for this user
                    collection.data.delete_many(
                        where=wvc.query.filter.by_property("user_id").equal(user_id)
                    )
            except Exception as count_error:
                print(f"⚠️  Could not count chunks: {count_error}")
                if confirm:
                    # Try deletion anyway
                    collection.data.delete_many(
                        where=wvc.query.filter.by_property("user_id").equal(user_id)
                    )
                chunk_count = "unknown"
                print(f"✅ Deleted {chunk_count} chunks from Weaviate")
            
        except Exception as e:
            print(f"❌ Error cleaning Weaviate data: {e}")
            return False
        finally:
            weaviate_client.close()
    
    if confirm:
        print(f"🎉 Successfully cleaned up all data for user: {user_id}")
    else:
        print(f"📋 Cleanup summary for user {user_id}:")
        print(f"   - Documents in Supabase: {doc_count}")
        print(f"   - Chunks in Weaviate: {chunk_count}")
        print("   Run with --confirm to delete this data")
    
    return True

def cleanup_demo_user():
    """Clean up the demo user specifically."""
    demo_user_id = "550e8400-e29b-41d4-a716-446655440000"
    return cleanup_user_data(demo_user_id, confirm=True)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up user data from StudyWise AI")
    parser.add_argument("--user-id", help="User ID to clean up")
    parser.add_argument("--demo", action="store_true", help="Clean up demo user")
    parser.add_argument("--confirm", action="store_true", help="Actually perform the deletion")
    
    args = parser.parse_args()
    
    if args.demo:
        cleanup_demo_user()
    elif args.user_id:
        cleanup_user_data(args.user_id, args.confirm)
    else:
        print("Usage:")
        print("  python scripts/cleanup_user_data.py --demo")
        print("  python scripts/cleanup_user_data.py --user-id USER_ID [--confirm]")