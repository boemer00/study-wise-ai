"""
Traditional Mode implementation: Standard conversational learning.
"""

import random
from typing import List, Dict, Any
from .base_mode import BaseStudyMode
from ..models.study_session import StudyPrompt, SessionResponse, PromptType, SessionStage


class TraditionalMode(BaseStudyMode):
    """
    Traditional Mode: Standard conversational learning approach.

    Session Flow:
    1. Answer user questions directly
    2. Provide explanations and examples
    3. Offer additional context when helpful
    4. Guide learning through natural conversation

    This mode provides the familiar chat-based learning experience
    while still tracking progress and understanding.
    """

    def __init__(self, documents: List[str], user_id: str, difficulty_level: int = 1):
        """
        Initialize Traditional mode with conversational approach.

        Args:
            documents: Document IDs to use for context
            user_id: User identifier for personalization
            difficulty_level: Starting difficulty (1-5)
        """
        super().__init__(documents, user_id, difficulty_level)
        self.conversation_topics = []
        self.explained_concepts = []
        self.user_questions = []

        # Track mode-specific state
        self.session_context.update({
            "conversation_style": "friendly",
            "topics_explored": set(),
            "explanation_depth_preference": "medium",
            "follow_up_questions_asked": 0,
            "user_initiated_topics": 0
        })

    async def generate_initial_prompt(self) -> StudyPrompt:
        """
        Generate welcoming prompt to start conversation.

        Creates a friendly opening that invites the user to ask questions
        or explore topics from their uploaded documents.

        Returns:
            StudyPrompt with welcoming conversation starter

        Raises:
            ValueError: If documents are invalid or inaccessible
        """
        if not self.documents:
            raise ValueError("No documents provided for study session")

        # Get document context to understand available topics
        try:
            doc_context = await self.get_document_context(self.documents)
            key_concepts = doc_context.get("key_concepts", ["the uploaded material"])

            # Create welcoming prompt based on available content
            if len(key_concepts) > 3:
                concept_preview = ", ".join(key_concepts[:3]) + f", and {len(key_concepts) - 3} other topics"
            else:
                concept_preview = ", ".join(key_concepts)

            # Adjust tone based on difficulty level
            if self.difficulty_level <= 2:
                tone = "I'm here to help you learn in a relaxed, step-by-step way."
                invitation = "Feel free to ask me anything, no matter how basic it might seem!"
            elif self.difficulty_level >= 4:
                tone = "I'm ready to dive deep into complex topics with you."
                invitation = "What challenging aspects would you like to explore?"
            else:
                tone = "I'm here to guide you through your learning journey."
                invitation = "What would you like to understand better?"

            prompt_text = f"""Hello! {tone}

I've reviewed your documents and I can help you with topics like: {concept_preview}.

{invitation}

You can:
• Ask questions about specific concepts
• Request explanations or examples
• Explore connections between topics
• Or simply tell me what interests you most!

What would you like to start with?"""

            return StudyPrompt(
                prompt_text=prompt_text,
                prompt_type=PromptType.QUESTION,
                difficulty_level=self.difficulty_level,
                related_documents=self.documents,
                expected_concepts=key_concepts[:5],  # Focus on top concepts
                context={
                    "mode": "traditional",
                    "stage": "greeting",
                    "available_topics": key_concepts
                }
            )

        except Exception as e:
            # Fallback prompt if document analysis fails
            return StudyPrompt(
                prompt_text=f"""Hello! I'm here to help you learn from your uploaded documents.

I'm ready to answer your questions, provide explanations, and guide you through the material in whatever way works best for you.

What would you like to start with? You can ask me about:
• Specific concepts you'd like to understand
• Questions about the material
• Requests for examples or explanations
• Or anything else you're curious about!

How can I help you today?""",
                prompt_type=PromptType.QUESTION,
                difficulty_level=self.difficulty_level,
                related_documents=self.documents,
                expected_concepts=["general topics"],
                context={"mode": "traditional", "stage": "greeting_fallback"}
            )

    async def process_user_response(self, response: str, current_prompt: StudyPrompt) -> SessionResponse:
        """
        Provide helpful response to user's question or comment.

        This method implements traditional conversational learning:
        - Answers user questions directly and clearly
        - Provides relevant examples and context
        - Suggests related topics to explore
        - Maintains natural conversation flow

        Args:
            response: User's question or comment
            current_prompt: The prompt they were responding to

        Returns:
            SessionResponse with helpful answer and follow-up suggestions
        """
        # Validate response
        if not self.validate_user_response(response):
            return SessionResponse(
                ai_message="I'd love to help! Could you please provide a bit more detail in your question or comment?",
                session_stage=SessionStage.ACTIVE,
                feedback="Please provide a more detailed response",
                suggestions=["Try asking a specific question", "Share what you're curious about", "Tell me what confused you"]
            )

        # Increment interaction count
        self.increment_interactions()

        # Analyze user's input to determine response strategy
        response_analysis = await self._analyze_user_input(response)

        # Generate appropriate response based on analysis
        ai_response = await self._generate_helpful_response(response, response_analysis)

        # Calculate quality score for this interaction
        quality_score = self.calculate_response_quality_score(
            response,
            current_prompt.expected_concepts
        )

        # Suggest related topics for continued exploration
        related_suggestions = await self._suggest_related_topics(response_analysis.get("main_topic", "general"))

        # Generate next prompt if appropriate
        next_prompt = await self._generate_follow_up_prompt(response_analysis)

        # Track concepts covered
        for concept in response_analysis.get("mentioned_concepts", []):
            self.add_covered_concept(concept)

        # Update session progress
        progress_increment = min(10.0, quality_score * 15.0)  # Max 15% per good interaction
        new_progress = min(100.0, self.session_context.get("current_progress", 0) + progress_increment)
        self.session_context["current_progress"] = new_progress

        return SessionResponse(
            ai_message=ai_response,
            next_prompt=next_prompt,
            session_stage=SessionStage.ACTIVE,
            progress_percentage=new_progress,
            feedback=f"Great {'question' if response_analysis.get('is_question') else 'response'}! " +
                    f"Quality score: {quality_score:.1f}/1.0",
            suggestions=related_suggestions,
            metadata={
                "response_analysis": response_analysis,
                "quality_score": quality_score,
                "concepts_mentioned": response_analysis.get("mentioned_concepts", [])
            }
        )

    async def evaluate_understanding(self, responses: List[str]) -> Dict[str, float]:
        """
        Evaluate understanding based on questions asked and engagement.

        Analyzes conversation to assess:
        - Types of questions being asked
        - Depth of follow-up questions
        - Understanding demonstrated in responses
        - Topics covered and explored

        Args:
            responses: All user responses in the conversation

        Returns:
            Dict mapping concepts to understanding scores (0.0-1.0)
        """
        if not responses:
            return {}

        understanding_scores = {}
        covered_concepts = self.get_covered_concepts()

        for concept in covered_concepts:
            concept_mentions = 0
            concept_depth_indicators = 0
            follow_up_questions = 0

            for response in responses:
                response_lower = response.lower()
                concept_lower = concept.lower()

                # Count mentions of this concept
                if concept_lower in response_lower:
                    concept_mentions += 1

                    # Look for depth indicators
                    depth_words = ['why', 'how', 'what if', 'explain', 'example', 'because', 'therefore']
                    concept_depth_indicators += sum(1 for word in depth_words if word in response_lower)

                    # Count follow-up questions
                    if '?' in response:
                        follow_up_questions += 1

            # Calculate understanding score based on engagement patterns
            base_score = min(1.0, concept_mentions * 0.2)  # Basic engagement
            depth_score = min(0.4, concept_depth_indicators * 0.1)  # Depth of inquiry
            follow_up_score = min(0.4, follow_up_questions * 0.2)  # Continued interest

            total_score = base_score + depth_score + follow_up_score
            understanding_scores[concept] = min(1.0, total_score)

        # Add scores for general engagement patterns
        total_responses = len(responses)
        avg_response_length = sum(len(r) for r in responses) / total_responses if responses else 0

        # General conversation quality score
        if avg_response_length > 50:  # Substantial responses
            understanding_scores["conversational_engagement"] = min(1.0, avg_response_length / 200.0)

        # Question complexity progression
        question_count = sum(1 for r in responses if '?' in r)
        if question_count > 0:
            understanding_scores["inquiry_skills"] = min(1.0, question_count / len(responses))

        return understanding_scores

    async def _analyze_user_input(self, response: str) -> Dict[str, Any]:
        """
        Analyze user input to determine response strategy.

        Args:
            response: User's input text

        Returns:
            Analysis results with response strategy
        """
        response_lower = response.lower()

        analysis = {
            "is_question": '?' in response,
            "is_request_for_explanation": any(word in response_lower for word in
                ['explain', 'what is', 'how does', 'why', 'tell me about']),
            "is_request_for_example": any(word in response_lower for word in
                ['example', 'instance', 'show me', 'demonstrate']),
            "mentions_confusion": any(word in response_lower for word in
                ['confused', 'unclear', "don't understand", 'lost', 'difficult']),
            "expresses_interest": any(word in response_lower for word in
                ['interesting', 'fascinating', 'cool', 'want to know more', 'tell me more']),
            "response_length": len(response),
            "mentioned_concepts": [],
            "complexity_level": self._assess_question_complexity(response),
            "main_topic": "general"
        }

        # Extract mentioned concepts
        covered_concepts = self.get_covered_concepts()
        for concept in covered_concepts:
            if concept.lower() in response_lower:
                analysis["mentioned_concepts"].append(concept)

        # Determine main topic (simple heuristic)
        if analysis["mentioned_concepts"]:
            analysis["main_topic"] = analysis["mentioned_concepts"][0]

        return analysis

    def _assess_question_complexity(self, question: str) -> int:
        """
        Assess complexity level of user's question.

        Args:
            question: User's question text

        Returns:
            Complexity level (1-5)
        """
        question_lower = question.lower()

        # Simple indicators of complexity
        basic_words = ['what', 'who', 'when', 'where']
        intermediate_words = ['how', 'why', 'explain']
        advanced_words = ['analyze', 'compare', 'evaluate', 'synthesize', 'implications', 'nuances']

        complexity_score = 1

        # Check for complexity indicators
        if any(word in question_lower for word in advanced_words):
            complexity_score = 5
        elif any(word in question_lower for word in intermediate_words):
            complexity_score = 3
        elif any(word in question_lower for word in basic_words):
            complexity_score = 2

        # Adjust based on length and structure
        if len(question) > 100:
            complexity_score += 1

        # Count of complex sentence structures
        complex_indicators = ['because', 'therefore', 'however', 'although', 'furthermore', 'moreover']
        if sum(1 for indicator in complex_indicators if indicator in question_lower) > 0:
            complexity_score += 1

        return min(5, max(1, complexity_score))

    async def _generate_helpful_response(self, user_input: str, analysis: Dict[str, Any]) -> str:
        """
        Generate helpful response to user's question or comment.

        Args:
            user_input: User's original input
            analysis: Analysis of the user input

        Returns:
            Helpful response text
        """
        # Determine response strategy based on analysis
        if analysis["mentions_confusion"]:
            response_start = "I understand that can be confusing! Let me break it down for you.\n\n"
        elif analysis["is_request_for_explanation"]:
            response_start = "Great question! Here's how I'd explain that:\n\n"
        elif analysis["is_request_for_example"]:
            response_start = "Perfect! Let me give you a concrete example:\n\n"
        elif analysis["expresses_interest"]:
            response_start = "I'm glad you find this interesting! Let me share more:\n\n"
        else:
            response_start = "Thanks for sharing that. Here's what I think:\n\n"

        # Generate main content based on complexity level and topic
        if analysis["main_topic"] != "general" and analysis["mentioned_concepts"]:
            main_content = await self._generate_topic_specific_content(
                analysis["main_topic"],
                analysis["complexity_level"]
            )
        else:
            # General encouragement and guidance
            main_content = """I'm here to help you understand the material better. Here are some ways we can approach your learning:

• **Ask specific questions** about concepts that interest or confuse you
• **Request examples** to see how abstract ideas work in practice
• **Explore connections** between different topics in your documents
• **Dive deeper** into areas you find particularly engaging

The beauty of learning is that we can take it at your pace and focus on what matters most to you."""

        # Add appropriate closing
        if analysis["complexity_level"] >= 4:
            closing = "\n\nWhat aspects would you like to explore further?"
        elif analysis["complexity_level"] <= 2:
            closing = "\n\nDoes this help clarify things? What else would you like to know?"
        else:
            closing = "\n\nWhat other questions do you have about this?"

        return response_start + main_content + closing

    async def _generate_topic_specific_content(self, topic: str, complexity: int) -> str:
        """
        Generate content specific to a topic and complexity level.

        Args:
            topic: The main topic to address
            complexity: Complexity level (1-5)

        Returns:
            Topic-specific content
        """
        # This would integrate with your document retrieval system
        # For now, we'll generate appropriate responses based on complexity

        if complexity <= 2:
            return f"""Let me explain **{topic}** in simple terms:

{topic} is an important concept from your materials. Think of it as [simple analogy or explanation].

The key points to remember are:
• [Main point 1]
• [Main point 2]
• [Main point 3]

This connects to other ideas in your documents, helping you build a complete understanding."""

        elif complexity >= 4:
            return f"""**{topic}** is a sophisticated concept with several important dimensions:

**Core Definition**: [Advanced explanation]

**Key Components**:
1. [Component 1] - [detailed explanation]
2. [Component 2] - [detailed explanation]
3. [Component 3] - [detailed explanation]

**Connections & Implications**: This concept relates to [other concepts] and has implications for [broader context].

**Advanced Considerations**: [Complex aspects, edge cases, or nuanced perspectives]"""

        else:
            return f"""**{topic}** is a key concept worth understanding well:

**What it is**: [Clear definition]

**Why it matters**: [Importance and relevance]

**How it works**: [Process or mechanism]

**Real-world application**: [Practical examples or use cases]

**Common misconceptions**: [Things students often get wrong]"""

    async def _suggest_related_topics(self, current_topic: str) -> List[str]:
        """
        Suggest related topics the user might want to explore.

        Args:
            current_topic: Topic currently being discussed

        Returns:
            List of related topic suggestions
        """
        # Get covered concepts to suggest connections
        covered_concepts = self.get_covered_concepts()

        suggestions = []

        # Add general learning suggestions
        suggestions.extend([
            "Ask for specific examples or use cases",
            "Explore how this connects to other concepts",
            "Request a different explanation approach",
            "Discuss practical applications"
        ])

        # Add concept-specific suggestions if we have covered concepts
        if covered_concepts and len(covered_concepts) > 1:
            other_concepts = [c for c in covered_concepts if c != current_topic][:3]
            suggestions.extend([
                f"Explore how this relates to {concept}" for concept in other_concepts
            ])

        # Limit to 5 suggestions maximum
        return suggestions[:5]

    async def _generate_follow_up_prompt(self, analysis: Dict[str, Any]) -> StudyPrompt:
        """
        Generate an optional follow-up prompt to continue the conversation.

        Args:
            analysis: Analysis of user's previous response

        Returns:
            Follow-up prompt to guide continued learning
        """
        # Sometimes provide gentle guidance, not always
        if self.get_interaction_count() % 3 == 0:  # Every third interaction

            if analysis["complexity_level"] <= 2:
                prompt_text = "Would you like me to explain anything else, or shall we explore a new topic?"
            elif analysis["complexity_level"] >= 4:
                prompt_text = "What other advanced aspects of this topic interest you?"
            else:
                prompt_text = "What other questions come to mind about this?"

            return StudyPrompt(
                prompt_text=prompt_text,
                prompt_type=PromptType.QUESTION,
                difficulty_level=self.difficulty_level,
                related_documents=self.documents,
                expected_concepts=analysis.get("mentioned_concepts", []),
                context={"follow_up": True, "interaction_count": self.get_interaction_count()}
            )

        return None

    async def _provide_examples(self, concept: str) -> List[str]:
        """
        Provide relevant examples for a concept.

        Args:
            concept: Concept to provide examples for

        Returns:
            List of relevant examples
        """
        # This would integrate with document content in real implementation
        examples = [
            f"Example 1: [Concrete instance of {concept}]",
            f"Example 2: [Another way {concept} appears]",
            f"Example 3: [Real-world application of {concept}]"
        ]

        # Adjust complexity based on difficulty level
        if self.difficulty_level <= 2:
            return [f"Simple example: {concept} is like [everyday analogy]"]
        elif self.difficulty_level >= 4:
            return [f"Advanced example: In [complex scenario], {concept} manifests as [detailed instance]"]

        return examples[:2]  # Return 2 examples for medium difficulty
