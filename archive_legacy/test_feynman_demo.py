#!/usr/bin/env python3
"""
FeynmanMode Demonstration Script

Shows the Feynman Technique study mode in action with realistic teaching scenarios.
"""

import asyncio
from src.study_modes.modes.feynman_mode import FeynmanMode


async def demonstrate_feynman_mode():
    """Demonstrate FeynmanMode with realistic teaching scenarios."""

    print("🧠 FeynmanMode Demonstration")
    print("=" * 50)
    print()

    # Create FeynmanMode instance
    feynman_mode = FeynmanMode(
        documents=['neural_collaborative_filtering.pdf'],
        user_id='demo-user',
        difficulty_level=2
    )

    print("✅ FeynmanMode initialized successfully")
    print(f"📚 Documents: {feynman_mode.documents}")
    print(f"👤 User: {feynman_mode.user_id}")
    print(f"📊 Difficulty Level: {feynman_mode.difficulty_level}")
    print(f"🎯 Target Audience: {feynman_mode.session_context['current_audience']}")
    print()

    # 1. Generate initial teaching prompt
    print("🚀 Step 1: Generate Initial Teaching Prompt")
    print("-" * 40)

    initial_prompt = await feynman_mode.generate_initial_prompt()
    print(f"📝 Prompt Type: {initial_prompt.prompt_type.value}")
    print(f"📋 Expected Concepts: {initial_prompt.expected_concepts}")
    print(f"🎯 Teaching Concept: {initial_prompt.context.get('teaching_concept')}")
    print()
    print(f"💬 Prompt Text:")
    print(f"   {initial_prompt.prompt_text[:200]}...")
    print()

    # 2. Process a teaching attempt with good explanations
    print("🎭 Step 2: Process Teaching Attempt (Good Explanation)")
    print("-" * 50)

    good_teaching_attempt = """
    Machine learning is like teaching a computer to recognize patterns, just like how you might teach a child to recognize different animals.

    First, you show the computer lots of examples - thousands of pictures of cats, dogs, and birds. The computer looks for patterns: cats have pointy ears and whiskers, dogs have floppy ears and bark, birds have feathers and beaks.

    Then, when you show the computer a new picture it's never seen before, it can say "This looks like a cat because it has pointy ears and whiskers, just like the other cat pictures I've seen."

    It's basically pattern recognition on a massive scale. The computer gets better the more examples you give it, just like how kids get better at recognizing animals after seeing many different ones.
    """

    response1 = await feynman_mode.process_user_response(good_teaching_attempt, initial_prompt)

    print(f"📊 Teaching Quality Score: {response1.metadata.get('teaching_quality_score', 0):.2f}")
    print(f"📈 Progress: {response1.progress_percentage:.1f}%")
    print(f"🔍 Analogies Detected: {response1.metadata.get('analogies_detected', [])}")
    print(f"🎯 Feynman Stage: {response1.metadata.get('feynman_stage')}")
    print()
    print(f"🤖 AI Feedback:")
    print(f"   {response1.ai_message[:300]}...")
    print()
    print(f"💡 Suggestions:")
    for i, suggestion in enumerate(response1.suggestions[:3], 1):
        print(f"   {i}. {suggestion}")
    print()

    # 3. Process a teaching attempt with knowledge gaps
    print("🔍 Step 3: Process Teaching Attempt (With Knowledge Gaps)")
    print("-" * 50)

    uncertain_teaching_attempt = """
    I think machine learning is maybe when computers learn from data, but I'm not really sure how it actually works.

    I guess algorithms are involved somehow, and they do something with the data to make predictions?

    I don't really understand what neural networks are exactly, but I think they're kind of like brains or something.
    """

    next_prompt = response1.next_prompt if response1.next_prompt else initial_prompt
    response2 = await feynman_mode.process_user_response(uncertain_teaching_attempt, next_prompt)

    print(f"📊 Teaching Quality Score: {response2.metadata.get('teaching_quality_score', 0):.2f}")
    print(f"📈 Progress: {response2.progress_percentage:.1f}%")
    print(f"⚠️ Knowledge Gaps: {response2.metadata.get('knowledge_gaps', [])}")
    print(f"🎯 Feynman Stage: {response2.metadata.get('feynman_stage')}")
    print()
    print(f"🤖 AI Feedback:")
    print(f"   {response2.ai_message[:300]}...")
    print()

    # 4. Show teaching progression analysis
    print("📊 Step 4: Teaching Progression Analysis")
    print("-" * 40)

    progression = feynman_mode._analyze_teaching_progression()
    print(f"🎯 Progression Type: {progression.get('progression', 'unknown')}")
    print(f"📈 Improvement: {progression.get('improvement', 0):.2f}")
    print(f"⭐ Initial Score: {progression.get('initial_score', 0):.2f}")
    print(f"🏆 Current Score: {progression.get('current_score', 0):.2f}")
    print(f"🎪 Consistency: {progression.get('consistency', 0):.2f}")
    print()

    # 5. Show concept extraction capabilities
    print("🔬 Step 5: Concept Extraction Demonstration")
    print("-" * 45)

    test_text = "Neural networks use backpropagation and gradient descent for optimization during training."
    extracted_concepts = feynman_mode.extract_concepts_from_response(test_text)
    print(f"📝 Input Text: {test_text}")
    print(f"🎯 Extracted Concepts: {extracted_concepts}")
    print()

    # 6. Show simplicity scoring
    print("📐 Step 6: Simplicity Scoring Demonstration")
    print("-" * 40)

    simple_text = "Machine learning helps computers learn from data to make predictions."
    complex_text = "Machine learning utilizes sophisticated algorithmic methodologies to optimize computational parameters."

    simple_score = feynman_mode._calculate_simplicity_score(simple_text)
    complex_score = feynman_mode._calculate_simplicity_score(complex_text)

    print(f"📝 Simple Text: '{simple_text}'")
    print(f"📊 Simplicity Score: {simple_score:.2f}")
    print()
    print(f"📝 Complex Text: '{complex_text}'")
    print(f"📊 Simplicity Score: {complex_score:.2f}")
    print()

    # 7. Generate session summary
    print("📋 Step 7: Session Summary")
    print("-" * 25)

    all_responses = [good_teaching_attempt, uncertain_teaching_attempt]
    summary = await feynman_mode.generate_session_summary(all_responses)

    print(f"🔢 Total Interactions: {summary['total_interactions']}")
    print(f"🎭 Teaching Attempts: {summary['teaching_attempts']}")
    print(f"📚 Concepts Covered: {len(summary['concepts_covered'])}")
    print(f"🎯 Average Teaching Quality: {summary['average_teaching_quality']:.2f}")
    print(f"🧠 Feynman Mastery Level: {summary['feynman_mastery_level']:.2f}")
    print(f"🔍 Knowledge Gaps Identified: {summary['knowledge_gaps_identified']}")
    print(f"🎨 Analogies Used: {summary['analogies_used']}")
    print()
    print(f"💡 Recommendations:")
    for i, rec in enumerate(summary['recommendations'][:3], 1):
        print(f"   {i}. {rec}")
    print()

    # 8. Audience progression demonstration
    print("🎭 Step 8: Audience Progression")
    print("-" * 30)

    audiences = ['child', 'peer', 'expert']
    print("🔄 Audience Progression Cycle:")
    for audience in audiences:
        next_aud = feynman_mode._get_next_audience(audience)
        print(f"   {audience} → {next_aud}")
    print()

    # 9. Show teaching tips for different audiences
    print("💡 Step 9: Teaching Tips by Audience")
    print("-" * 35)

    concept = "machine learning"
    for audience in audiences:
        tips = feynman_mode._get_teaching_tips(audience, concept)
        print(f"🎯 {audience.upper()} audience:")
        print(f"   {tips}")
        print()

    print("✅ FeynmanMode Demonstration Complete!")
    print("🎓 The Feynman Technique helps learners master concepts through teaching,")
    print("   simplification, analogies, and identifying knowledge gaps.")


if __name__ == "__main__":
    asyncio.run(demonstrate_feynman_mode())
