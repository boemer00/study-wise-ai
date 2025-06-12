#!/usr/bin/env python3
"""
Test script to migrate demo cards to FSRS system and test the due cards functionality.
"""

import uuid
from src.flashcards.scheduler import migrate_demo_cards_to_fsrs, get_due_cards

def main():
    # Use a proper UUID for demo testing
    demo_user_uuid = "550e8400-e29b-41d4-a716-446655440000"  # Fixed UUID for consistent testing
    print(f"🔧 Using demo user UUID: {demo_user_uuid}")

    print("\n🔄 Starting migration of demo cards to FSRS...")
    migrated = migrate_demo_cards_to_fsrs(demo_user_uuid, limit=10)
    print(f"✅ Migrated {migrated} cards to FSRS system")

    print("\n📋 Getting due cards after migration...")
    due_cards = get_due_cards(demo_user_uuid, limit=10)
    print(f"📊 Found {len(due_cards)} cards due for review")

    if due_cards:
        print("\n🃏 First 3 due cards:")
        for i, card in enumerate(due_cards[:3]):
            print(f"  {i+1}. {card.get('flashcard_id', card.get('id', 'Unknown'))}: {card.get('question', 'No question')[:50]}...")

    print(f"\n🎯 For API testing, use: user_id={demo_user_uuid}")

if __name__ == "__main__":
    main()
