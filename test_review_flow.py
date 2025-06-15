#!/usr/bin/env python3
"""
Test script to trace the complete flashcard review flow.
This will help identify exactly where the persistence issue is occurring.
"""

import sys
sys.path.append('.')

import json
from datetime import datetime, timezone
from src.flashcards.scheduler import get_due_cards, review_card, get_scheduling_metrics
from src.flashcards.models import CardRating
from src.supabase_client import get_supabase_client

DEMO_USER_UUID = '550e8400-e29b-41d4-a716-446655440000'

def test_complete_review_flow():
    """Test the complete review flow from due cards to persistence."""
    
    print("="*60)
    print("FLASHCARD REVIEW FLOW TEST")
    print("="*60)
    
    # Step 1: Get initial state
    print("\n1. INITIAL STATE")
    print("-" * 30)
    
    due_cards_before = get_due_cards(DEMO_USER_UUID, limit=20)
    metrics_before = get_scheduling_metrics(DEMO_USER_UUID)
    
    print(f"Due cards before: {len(due_cards_before)}")
    print(f"Total cards: {metrics_before.total_cards}")
    print(f"Cards due today: {metrics_before.cards_due_today}")
    
    if not due_cards_before:
        print("❌ No due cards found - cannot test review flow")
        return
    
    # Select first card for testing
    test_card = due_cards_before[0]
    flashcard_id = test_card['flashcard_id']
    
    print(f"\nTesting with card: {flashcard_id}")
    print(f"Question: {test_card['question'][:50]}...")
    print(f"Current state: {test_card['state']}")
    print(f"Total reviews: {test_card['total_reviews']}")
    print(f"Due date: {test_card['due_date']}")
    print(f"Last reviewed: {test_card.get('last_reviewed', 'Never')}")
    
    # Step 2: Check database state before review
    print("\n2. DATABASE STATE BEFORE REVIEW")
    print("-" * 40)
    
    supabase = get_supabase_client()
    
    # Check FSRS state
    fsrs_state_before = supabase.table('fsrs_card_states').select('*').eq(
        'flashcard_id', flashcard_id
    ).eq('user_id', DEMO_USER_UUID).execute()
    
    if fsrs_state_before.data:
        state = fsrs_state_before.data[0]
        print(f"FSRS State exists:")
        print(f"  Stability: {state['stability']}")
        print(f"  Difficulty: {state['difficulty']}")
        print(f"  Due date: {state['due_date']}")
        print(f"  Last reviewed: {state['last_reviewed']}")
        print(f"  Total reviews: {state['total_reviews']}")
        print(f"  State: {state['state']}")
    else:
        print("❌ No FSRS state found!")
    
    # Check review history count
    history_before = supabase.table('fsrs_review_history').select('id').eq(
        'flashcard_id', flashcard_id
    ).eq('user_id', DEMO_USER_UUID).execute()
    
    print(f"Review history records: {len(history_before.data)}")
    
    # Step 3: Perform review
    print("\n3. PERFORMING REVIEW")
    print("-" * 30)
    
    print("Submitting GOOD rating...")
    
    try:
        # Fix the timezone issue first
        review_result = review_card(flashcard_id, DEMO_USER_UUID, CardRating.GOOD)
        print("✅ Review submitted successfully!")
        print(f"Next due date: {review_result.next_due_date}")
        print(f"Interval days: {review_result.interval_days}")
        print(f"New stability: {review_result.new_state.stability:.2f}")
        print(f"New difficulty: {review_result.new_state.difficulty:.2f}")
        print(f"Total reviews after: {review_result.new_state.total_reviews}")
        
    except Exception as e:
        print(f"❌ Review failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 4: Check database state after review
    print("\n4. DATABASE STATE AFTER REVIEW")
    print("-" * 40)
    
    # Check FSRS state
    fsrs_state_after = supabase.table('fsrs_card_states').select('*').eq(
        'flashcard_id', flashcard_id
    ).eq('user_id', DEMO_USER_UUID).execute()
    
    if fsrs_state_after.data:
        state = fsrs_state_after.data[0]
        print(f"FSRS State after review:")
        print(f"  Stability: {state['stability']} (was {fsrs_state_before.data[0]['stability']})")
        print(f"  Difficulty: {state['difficulty']} (was {fsrs_state_before.data[0]['difficulty']})")
        print(f"  Due date: {state['due_date']} (was {fsrs_state_before.data[0]['due_date']})")
        print(f"  Last reviewed: {state['last_reviewed']} (was {fsrs_state_before.data[0]['last_reviewed']})")
        print(f"  Total reviews: {state['total_reviews']} (was {fsrs_state_before.data[0]['total_reviews']})")
        print(f"  State: {state['state']} (was {fsrs_state_before.data[0]['state']})")
        
        if state['total_reviews'] > fsrs_state_before.data[0]['total_reviews']:
            print("✅ Total reviews incremented correctly!")
        else:
            print("❌ Total reviews NOT incremented!")
            
    else:
        print("❌ FSRS state disappeared after review!")
    
    # Check review history
    history_after = supabase.table('fsrs_review_history').select('*').eq(
        'flashcard_id', flashcard_id
    ).eq('user_id', DEMO_USER_UUID).execute()
    
    print(f"Review history records: {len(history_after.data)} (was {len(history_before.data)})")
    
    if len(history_after.data) > len(history_before.data):
        print("✅ New review history record created!")
        latest_review = history_after.data[-1]  # Get the latest one
        print(f"  Rating: {latest_review['rating']}")
        print(f"  Review time: {latest_review['review_time']}")
        print(f"  Elapsed days: {latest_review['elapsed_days']}")
    else:
        print("❌ No new review history record created!")
    
    # Step 5: Check if card is still in due list
    print("\n5. DUE LIST AFTER REVIEW")
    print("-" * 35)
    
    due_cards_after = get_due_cards(DEMO_USER_UUID, limit=20)
    metrics_after = get_scheduling_metrics(DEMO_USER_UUID)
    
    print(f"Due cards after: {len(due_cards_after)} (was {len(due_cards_before)})")
    print(f"Cards due today: {metrics_after.cards_due_today} (was {metrics_before.cards_due_today})")
    
    # Check if our test card is still in the due list
    still_due = any(c['flashcard_id'] == flashcard_id for c in due_cards_after)
    print(f"Test card still in due list: {still_due}")
    
    if not still_due:
        print("✅ Card correctly removed from due list!")
    else:
        print("❌ Card still appears in due list!")
        # Find the card and show its current state
        for card in due_cards_after:
            if card['flashcard_id'] == flashcard_id:
                print(f"  Current due date: {card['due_date']}")
                print(f"  Current state: {card['state']}")
                print(f"  Days overdue: {card.get('days_overdue', 'N/A')}")
                break
    
    # Step 6: Summary
    print("\n6. SUMMARY")
    print("-" * 20)
    
    success_indicators = [
        ("Review submission", "✅" if 'review_result' in locals() else "❌"),
        ("FSRS state updated", "✅" if fsrs_state_after.data and 
         fsrs_state_after.data[0]['total_reviews'] > fsrs_state_before.data[0]['total_reviews'] else "❌"),
        ("Review history created", "✅" if len(history_after.data) > len(history_before.data) else "❌"),
        ("Card removed from due list", "✅" if not still_due else "❌"),
        ("Due count decreased", "✅" if metrics_after.cards_due_today < metrics_before.cards_due_today else "❌")
    ]
    
    for indicator, status in success_indicators:
        print(f"{status} {indicator}")
    
    failures = [s for s in success_indicators if s[1] == "❌"]
    if failures:
        print(f"\n❌ FOUND {len(failures)} ISSUES IN REVIEW PERSISTENCE!")
        print("These need to be fixed for proper review tracking.")
    else:
        print("\n✅ ALL REVIEW PERSISTENCE CHECKS PASSED!")

if __name__ == "__main__":
    test_complete_review_flow()