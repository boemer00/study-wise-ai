#!/usr/bin/env python3
"""
FSRS Demo Script

This script demonstrates how to use the new FSRS (Free Spaced Repetition Scheduler)
implementation for flashcard scheduling.

Run this after setting up the database schema to see FSRS in action.
"""

from datetime import datetime, timedelta
from src.flashcards.models import CardRating
from src.flashcards.fsrs import (
    get_fsrs_parameters,
    process_card_review,
    simulate_forgetting_curve,
    calculate_retrievability
)
from src.flashcards.models import CardState

def main():
    print("🧠 FSRS (Free Spaced Repetition Scheduler) Demo")
    print("=" * 50)

    # 1. Get FSRS parameters
    print("\n1. FSRS Parameters:")
    params = get_fsrs_parameters()
    print(f"   Target retention: {params.request_retention:.1%}")
    print(f"   Maximum interval: {params.maximum_interval} days")
    print(f"   Algorithm version: {params.version}")

    # 2. Simulate a new card's learning journey
    print("\n2. Card Learning Journey:")
    print("   Simulating reviews for a new Python flashcard...")

    # Start with a new card
    card_state = CardState(
        flashcard_id="python_variables_001",
        user_id="demo_student",
        stability=0.4,  # Initial stability for new cards
        difficulty=5.0,  # Initial difficulty
        due_date=datetime.now(),
        last_reviewed=None,
        total_reviews=0,
        lapses=0,
        state="new",
        reps=0,
        elapsed_days=None,
        scheduled_days=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    # Simulate a sequence of reviews
    review_sequence = [
        (CardRating.GOOD, 0, "First review - student got it right"),
        (CardRating.GOOD, 1, "Second review after 1 day - still good"),
        (CardRating.HARD, 3, "Third review after 3 days - found it harder"),
        (CardRating.AGAIN, 5, "Fourth review after 5 days - forgot it"),
        (CardRating.GOOD, 1, "Fifth review after 1 day - back on track"),
        (CardRating.EASY, 4, "Sixth review after 4 days - now easy!")
    ]

    print(f"\n   Starting state:")
    print(f"   • Stability: {card_state.stability:.2f} days")
    print(f"   • Difficulty: {card_state.difficulty:.1f}/10")

    for i, (rating, elapsed_days, description) in enumerate(review_sequence, 1):
        # Process the review
        new_stability, new_difficulty, next_interval = process_card_review(
            card_state, rating, elapsed_days, params
        )

        # Calculate retrievability at review time
        if elapsed_days > 0:
            retrievability = calculate_retrievability(elapsed_days, card_state.stability)
        else:
            retrievability = 1.0

        print(f"\n   Review #{i}: {description}")
        print(f"   • Rating: {rating.name} ({rating.value}/4)")
        print(f"   • Retrievability at review: {retrievability:.1%}")
        print(f"   • New stability: {new_stability:.2f} days (was {card_state.stability:.2f})")
        print(f"   • New difficulty: {new_difficulty:.1f}/10 (was {card_state.difficulty:.1f})")
        print(f"   • Next interval: {next_interval} days")

        # Update card state for next iteration
        review_time = card_state.due_date + timedelta(days=elapsed_days)
        card_state = CardState(
            flashcard_id=card_state.flashcard_id,
            user_id=card_state.user_id,
            stability=new_stability,
            difficulty=new_difficulty,
            due_date=review_time + timedelta(days=next_interval),
            last_reviewed=review_time,
            total_reviews=card_state.total_reviews + 1,
            lapses=card_state.lapses + (1 if rating == CardRating.AGAIN else 0),
            state="review" if rating != CardRating.AGAIN else "relearning",
            reps=card_state.reps + (1 if rating != CardRating.AGAIN else 0),
            elapsed_days=elapsed_days,
            scheduled_days=next_interval,
            created_at=card_state.created_at,
            updated_at=review_time
        )

    # 3. Show forgetting curve
    print(f"\n3. Forgetting Curve (current stability: {card_state.stability:.1f} days):")
    curve = simulate_forgetting_curve(card_state.stability, days_range=30)

    print("   Days | Retrievability")
    print("   -----|-------------")
    for day, retrievability in curve[::5]:  # Show every 5th day
        bar = "█" * int(retrievability * 20)
        print(f"   {day:3d}  | {retrievability:.1%} {bar}")

    # 4. Summary statistics
    print(f"\n4. Final Statistics:")
    print(f"   • Total reviews: {card_state.total_reviews}")
    print(f"   • Successful reviews: {card_state.reps}")
    print(f"   • Lapses (forgotten): {card_state.lapses}")
    print(f"   • Success rate: {card_state.reps/card_state.total_reviews:.1%}")
    print(f"   • Final stability: {card_state.stability:.1f} days")
    print(f"   • Final difficulty: {card_state.difficulty:.1f}/10")
    print(f"   • Next review in: {next_interval} days")

    print(f"\n✅ Demo completed! The card has evolved from a new, unstable memory")
    print(f"   to a mature memory with {card_state.stability:.1f}-day stability.")

    # 5. Integration instructions
    print(f"\n5. Integration with StudyWise AI:")
    print(f"   To use this in your app:")
    print(f"   1. Run the database schema: src/flashcards/database_schema.sql")
    print(f"   2. Import: from src.flashcards import review_card, get_due_cards")
    print(f"   3. Use review_card() when users study flashcards")
    print(f"   4. Use get_due_cards() to get cards ready for review")

    print(f"\n   Example API usage:")
    print(f"   result = review_card('card_123', 'user_456', CardRating.GOOD)")
    print(f"   due_cards = get_due_cards('user_456', limit=20)")

if __name__ == "__main__":
    main()
