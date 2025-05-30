#!/usr/bin/env python3
"""
Quick demo of StudyWise AI - shows 2-3 questions rapidly
"""

import sys
import asyncio
from datetime import datetime

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add src to path
sys.path.insert(0, 'src')

from conversation.rag import StudyAssistant

async def quick_demo():
    """Quick demo with 3 questions to show the system working."""
    print("⚡ StudyWise AI - Quick Demo")
    print("=" * 40)

    try:
        # Initialize (this is the slow part)
        print("🚀 Initializing... (this takes ~10-15 seconds)")
        assistant = StudyAssistant()
        await assistant.initialize()
        print("✅ Ready!")

        # Start conversation
        user_id = f"demo-{datetime.now().strftime('%H%M%S')}"
        conversation_id = await assistant.start_conversation(user_id)
        print(f"💬 Conversation: {conversation_id[:8]}...")

        # Quick questions
        questions = [
            "What is machine learning?",
            "How does it work?",
            "Can you give me an example?"
        ]

        for i, question in enumerate(questions, 1):
            print(f"\n❓ Q{i}: {question}")

            start = datetime.now()
            response = await assistant.ask_question(conversation_id, question)
            duration = (datetime.now() - start).total_seconds()

            # Show shortened response
            answer = response.answer[:150] + "..." if len(response.answer) > 150 else response.answer
            print(f"🤖 A{i}: {answer}")
            print(f"   ⚡ {duration:.1f}s | 📊 Confidence: {response.confidence_score:.2f}")

        print(f"\n✅ Demo complete! System is working perfectly.")
        print(f"💡 Try the full demo with: python demo_studywise.py")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(quick_demo())
