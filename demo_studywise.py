#!/usr/bin/env python3
"""
Interactive demo for StudyWise AI Conversational RAG System
Shows the system working with different types of questions.
"""

import sys
import asyncio
from datetime import datetime

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Make sure to set environment variables manually.")

# Add src to path
sys.path.insert(0, 'src')

from conversation.rag import StudyAssistant

# Sample questions organized by type
SAMPLE_QUESTIONS = {
    "Factual Questions (Basic Knowledge)": [
        "What is machine learning?",
        "What is artificial intelligence?",
        "What is deep learning?",
        "What is a neural network?",
        "What is supervised learning?"
    ],

    "Conceptual Questions (How Things Work)": [
        "How does a neural network learn?",
        "How do machine learning algorithms work?",
        "How does gradient descent work?",
        "How do computers recognize images?",
        "How does natural language processing work?"
    ],

    "Application Questions (Practical Use)": [
        "How can I start learning machine learning?",
        "How do I choose the right algorithm?",
        "How can I improve model accuracy?",
        "How do I prepare data for machine learning?",
        "How can I deploy a machine learning model?"
    ],

    "Comparison Questions": [
        "What's the difference between AI and machine learning?",
        "Supervised vs unsupervised learning - what's the difference?",
        "Compare linear regression and logistic regression",
        "What's better: decision trees or neural networks?",
        "Compare Python and R for machine learning"
    ],

    "Explanation Questions (Why/Because)": [
        "Why is data preprocessing important?",
        "Why do neural networks need activation functions?",
        "Why does overfitting happen?",
        "Why is cross-validation important?",
        "Why do we need regularization?"
    ]
}

async def demo_conversation():
    """Run an interactive demo conversation."""
    print("🤖 StudyWise AI - Interactive Demo")
    print("=" * 50)

    try:
        # Initialize the assistant
        print("🚀 Initializing StudyWise AI...")
        assistant = StudyAssistant()
        await assistant.initialize()
        print("✅ Assistant ready!")

        # Start a conversation
        print("\n💬 Starting new conversation...")
        user_id = "demo-user-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        conversation_id = await assistant.start_conversation(user_id)
        print(f"✅ Conversation started: {conversation_id}")

        return assistant, conversation_id

    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return None, None

async def ask_question(assistant, conversation_id, question):
    """Ask a question and show the response."""
    print(f"\n❓ Question: '{question}'")
    print("-" * 60)

    try:
        start_time = datetime.now()
        response = await assistant.ask_question(
            conversation_id=conversation_id,
            question=question
        )
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        print(f"🤖 Answer: {response.answer[:200]}...")
        print(f"📊 Confidence: {response.confidence_score:.2f}")
        print(f"⚡ Processing time: {processing_time:.1f}s")
        print(f"📚 Sources: {len(response.sources)} documents")

        if response.follow_up_suggestions:
            print(f"💡 Suggested follow-ups:")
            for i, suggestion in enumerate(response.follow_up_suggestions[:3], 1):
                print(f"   {i}. {suggestion}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def run_sample_questions():
    """Run through sample questions to demonstrate capabilities."""
    assistant, conversation_id = await demo_conversation()

    if not assistant:
        return

    print("\n🎯 Let's test different types of questions...")
    print("=" * 50)

    # Test one question from each category
    test_questions = [
        ("Factual", "What is machine learning?"),
        ("Conceptual", "How does a neural network learn?"),
        ("Application", "How can I start learning machine learning?"),
        ("Comparison", "What's the difference between AI and machine learning?"),
        ("Explanation", "Why is data preprocessing important?")
    ]

    for category, question in test_questions:
        print(f"\n📋 Testing {category} Question:")
        success = await ask_question(assistant, conversation_id, question)
        if not success:
            break

        # Small delay between questions
        await asyncio.sleep(1)

    print(f"\n📚 Conversation History:")
    try:
        history = await assistant.get_conversation_history(conversation_id, limit=10)
        for i, msg in enumerate(history[-6:], 1):  # Show last 6 messages
            role_icon = "👤" if msg.role.value == "user" else "🤖"
            preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
            print(f"   {i}. {role_icon} {preview}")
    except Exception as e:
        print(f"   ❌ Could not retrieve history: {e}")

async def interactive_mode():
    """Run interactive mode where user can ask custom questions."""
    assistant, conversation_id = await demo_conversation()

    if not assistant:
        return

    print("\n🎮 Interactive Mode - Ask your own questions!")
    print("Type 'quit' to exit, 'samples' to see sample questions")
    print("=" * 50)

    while True:
        try:
            question = input("\n❓ Your question: ").strip()

            if question.lower() in ['quit', 'exit', 'q']:
                break
            elif question.lower() == 'samples':
                show_sample_questions()
                continue
            elif not question:
                continue

            await ask_question(assistant, conversation_id, question)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def show_sample_questions():
    """Display sample questions organized by category."""
    print("\n📋 Sample Questions You Can Try:")
    print("=" * 50)

    for category, questions in SAMPLE_QUESTIONS.items():
        print(f"\n🎯 {category}:")
        for i, question in enumerate(questions[:3], 1):  # Show top 3 per category
            print(f"   {i}. {question}")

async def main():
    """Main demo function."""
    print("🎓 Welcome to StudyWise AI Demo!")
    print("Choose a demo mode:")
    print("1. Automated sample questions")
    print("2. Interactive mode (ask your own questions)")
    print("3. Show all sample questions")

    try:
        choice = input("\nEnter choice (1-3): ").strip()

        if choice == "1":
            await run_sample_questions()
        elif choice == "2":
            await interactive_mode()
        elif choice == "3":
            show_sample_questions()
        else:
            print("Invalid choice. Running automated demo...")
            await run_sample_questions()

    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
