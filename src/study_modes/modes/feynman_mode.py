"""
Feynman Study Mode - Learn through teaching and simplification.

The Feynman Technique is based on the idea that if you can't explain something simply,
you don't understand it well enough. This mode challenges users to:
1. Explain concepts in simple terms
2. Use analogies and examples
3. Identify knowledge gaps
4. Teach to different audiences
5. Progressively build complexity
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
import random

from .base_mode import BaseStudyMode
from ..models.study_session import StudyPrompt, SessionResponse, PromptType, SessionStage
from ..models.analytics import ConceptUnderstanding, LearningInsights


class FeynmanMode(BaseStudyMode):
    """
    Feynman Technique study mode implementation.

    Focuses on learning through teaching, simplification, and analogies.
    Users explain concepts as if teaching others, helping identify knowledge gaps.
    """

    def __init__(self, documents: List[str], user_id: str, difficulty_level: int = 2):
        """
        Initialize Feynman mode.

        Args:
            documents: List of document IDs to study
            user_id: Unique identifier for the user
            difficulty_level: Starting difficulty (1-5), default 2 for teaching focus
        """
        super().__init__(documents, user_id, difficulty_level)

        # Feynman-specific session context
        self.session_context.update({
            'teaching_attempts': [],
            'explanation_quality_scores': [],
            'analogies_used': [],
            'knowledge_gaps_identified': [],
            'audience_levels': ['child', 'peer', 'expert'],
            'current_audience': 'peer',
            'simplification_challenges': 0,
            'analogy_challenges': 0,
            'complexity_progression': [],
            'teaching_concepts': set(),
            'mastery_indicators': {},
            'current_progress': 0.0  # Add progress tracking
        })

    def calculate_session_progress(self) -> float:
        """
        Calculate current session progress as a percentage.

        Returns:
            Progress percentage (0.0-100.0)
        """
        return self.session_context.get('current_progress', 0.0)

    def extract_concepts_from_response(self, response: str) -> List[str]:
        """
        Extract concepts mentioned in user response.

        Args:
            response: User's response text

        Returns:
            List of extracted concepts
        """
        concepts = []
        response_lower = response.lower()

        # Common ML/AI concepts to look for
        concept_keywords = [
            'machine learning', 'neural networks', 'deep learning', 'algorithms',
            'artificial intelligence', 'data science', 'statistics', 'probability',
            'regression', 'classification', 'clustering', 'supervised learning',
            'unsupervised learning', 'reinforcement learning', 'feature engineering',
            'model training', 'optimization', 'gradient descent', 'backpropagation',
            'overfitting', 'underfitting', 'cross validation', 'bias', 'variance'
        ]

        # Extract concepts that appear in the response
        for concept in concept_keywords:
            if concept in response_lower:
                concepts.append(concept)

        # Extract concepts from covered concepts
        covered_concepts = self.get_covered_concepts()
        for concept in covered_concepts:
            if concept.lower() in response_lower and concept not in concepts:
                concepts.append(concept)

        # Simple word-based concept extraction
        words = response_lower.split()
        potential_concepts = []

        # Look for technical terms (words > 6 characters ending in certain suffixes)
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word)
            if (len(word_clean) > 6 and
                any(word_clean.endswith(suffix) for suffix in ['tion', 'sion', 'ment', 'ness', 'ing']) and
                word_clean not in concepts):
                potential_concepts.append(word_clean)

        # Add unique potential concepts (limit to avoid noise)
        concepts.extend(potential_concepts[:3])

        return list(set(concepts))  # Remove duplicates

    def calculate_duration(self) -> int:
        """
        Calculate session duration in seconds.

        Returns:
            Duration in seconds
        """
        if hasattr(self, 'start_time'):
            if hasattr(self, 'end_time') and self.end_time:
                return int((self.end_time - self.start_time).total_seconds())
            else:
                return int((datetime.now() - self.start_time).total_seconds())
        else:
            # Estimate based on interactions (rough estimate: 2 minutes per interaction)
            return self.get_interaction_count() * 120

    async def generate_initial_prompt(self, **kwargs) -> StudyPrompt:
        """
        Generate initial Feynman technique prompt focused on teaching.

        Returns:
            StudyPrompt: Initial teaching challenge prompt
        """
        try:
            # Get document context for content selection
            context = await self.get_document_context(self.documents)
            key_concepts = context.get('key_concepts', ['basic concepts'])
            document_summaries = context.get('document_summaries', {})

            # Select primary concept for teaching
            primary_concept = self._select_teaching_concept(key_concepts)

            # Generate teaching challenge based on difficulty and audience
            audience = self.session_context['current_audience']

            # Create Feynman-style greeting and challenge
            greeting_templates = [
                f"Welcome to your Feynman learning session! Today, you'll master concepts by teaching them.",
                f"Ready to learn through teaching? The Feynman Technique will help you truly understand {primary_concept}.",
                f"Let's explore {primary_concept} using the Feynman method - if you can't explain it simply, you don't understand it!"
            ]

            teaching_challenges = {
                'child': f"Imagine you're explaining {primary_concept} to a curious 8-year-old. Use simple words and fun examples!",
                'peer': f"Explain {primary_concept} to a classmate who's hearing about it for the first time. Make it clear and engaging.",
                'expert': f"Teach {primary_concept} to someone with advanced knowledge. Focus on deep insights and connections."
            }

            # Combine greeting with teaching challenge
            greeting = random.choice(greeting_templates)
            challenge = teaching_challenges[audience]

            # Add context from documents
            document_context = ""
            if document_summaries:
                doc_titles = list(document_summaries.keys())[:2]  # Limit to 2 documents
                if doc_titles:
                    document_context = f"\n\nBased on your study materials ({', '.join(doc_titles)}), "

            prompt_text = f"{greeting}\n\n{challenge}{document_context}start by giving me your best explanation of {primary_concept}. Don't worry about being perfect - we'll refine your understanding together!"

            # Add teaching tips
            tips = self._get_teaching_tips(audience, primary_concept)
            if tips:
                prompt_text += f"\n\n💡 Teaching Tips:\n{tips}"

            return StudyPrompt(
                prompt_text=prompt_text,
                prompt_type=PromptType.EXPLANATION_REQUEST,
                difficulty_level=self.difficulty_level,
                expected_concepts=[primary_concept] + key_concepts[:3],
                context={
                    'voice_compatible': True,
                    'teaching_concept': primary_concept,
                    'target_audience': audience,
                    'feynman_stage': 'initial_explanation',
                    'encouragement_tone': True
                },
                related_documents=self.documents
            )

        except Exception as e:
            # Fallback prompt
            return StudyPrompt(
                prompt_text="Welcome to Feynman learning! Pick any concept from your materials and explain it as if you're teaching a friend. What would you like to teach me about?",
                prompt_type=PromptType.EXPLANATION_REQUEST,
                difficulty_level=self.difficulty_level,
                expected_concepts=['general concepts'],
                context={'voice_compatible': True, 'feynman_stage': 'fallback'},
                related_documents=self.documents
            )

    async def process_user_response(self, user_input: str, current_prompt: StudyPrompt) -> SessionResponse:
        """
        Process user's teaching attempt and provide Feynman-style feedback.

        Args:
            user_input: User's explanation/teaching attempt
            current_prompt: The prompt being responded to

        Returns:
            SessionResponse: Feedback and next teaching challenge
        """
        # Validate response
        if not self.validate_user_response(user_input):
            return self._generate_encouragement_response("I'd love to hear more! Can you expand on your explanation?")

        # Increment interactions
        self.increment_interactions()

        # Analyze the teaching attempt
        teaching_analysis = await self._analyze_teaching_attempt(user_input, current_prompt)

        # Store teaching attempt
        self.session_context['teaching_attempts'].append({
            'attempt': user_input,
            'timestamp': datetime.now().isoformat(),
            'concept': current_prompt.context.get('teaching_concept', 'unknown'),
            'audience': current_prompt.context.get('target_audience', 'peer'),
            'analysis': teaching_analysis
        })

        # Calculate quality score and progress
        quality_score = self._calculate_teaching_quality(user_input, teaching_analysis)
        self.session_context['explanation_quality_scores'].append(quality_score)

        # Update session progress (Feynman-specific progress calculation)
        progress_increment = min(15.0, quality_score * 20.0)  # Max 20% per excellent teaching
        new_progress = min(100.0, self.session_context.get('current_progress', 0) + progress_increment)
        self.session_context['current_progress'] = new_progress

        # Generate AI response based on teaching quality
        ai_response = await self._generate_feynman_feedback(user_input, teaching_analysis, current_prompt)

        # Determine next challenge
        next_prompt = await self._generate_next_teaching_challenge(teaching_analysis, current_prompt)

        # Generate suggestions
        suggestions = self._generate_teaching_suggestions(teaching_analysis, quality_score)

        # Determine session stage
        session_stage = self._determine_session_stage(teaching_analysis, quality_score)

        return SessionResponse(
            ai_message=ai_response,
            feedback=teaching_analysis.get('feedback', 'Keep practicing your explanations!'),
            suggestions=suggestions,
            progress_percentage=new_progress,
            next_prompt=next_prompt,
            session_stage=session_stage,
            metadata={
                'teaching_quality_score': quality_score,
                'feynman_stage': teaching_analysis.get('stage', 'explanation'),
                'knowledge_gaps': teaching_analysis.get('knowledge_gaps', []),
                'analogies_detected': teaching_analysis.get('analogies', []),
                'simplification_level': teaching_analysis.get('simplification_level', 0.5),
                'voice_compatible': True,
                'input_method': 'text',
                'response_time_ms': 800
            }
        )

    async def evaluate_understanding(self, user_responses: List[str]) -> Dict[str, float]:
        """
        Evaluate understanding based on teaching ability and explanation quality.

        Args:
            user_responses: List of user explanations/teaching attempts

        Returns:
            Dict mapping concepts to understanding scores (0.0-1.0)
        """
        understanding_scores = {}

        # Extract concepts from teaching attempts
        all_concepts = set()
        for attempt in self.session_context['teaching_attempts']:
            concept = attempt.get('concept', '')
            if concept:
                all_concepts.add(concept)

        # Add concepts from responses
        for response in user_responses:
            extracted_concepts = self.extract_concepts_from_response(response)
            all_concepts.update(extracted_concepts)

        # Evaluate each concept based on teaching mastery
        for concept in all_concepts:
            understanding_scores[concept] = await self._evaluate_teaching_mastery(concept, user_responses)

        # Add concepts from covered set
        for concept in self.get_covered_concepts():
            if concept not in understanding_scores:
                understanding_scores[concept] = await self._evaluate_teaching_mastery(concept, user_responses)

        return understanding_scores

    async def generate_session_summary(self, user_responses: List[str]) -> Dict[str, Any]:
        """
        Generate comprehensive Feynman session summary focused on teaching mastery.

        Args:
            user_responses: All user responses during session

        Returns:
            Dict containing session summary and teaching insights
        """
        # Calculate basic metrics
        total_interactions = len(user_responses)
        teaching_attempts = len(self.session_context['teaching_attempts'])
        avg_teaching_quality = sum(self.session_context['explanation_quality_scores']) / max(len(self.session_context['explanation_quality_scores']), 1)

        # Analyze teaching progression
        teaching_progression = self._analyze_teaching_progression()

        # Identify mastered concepts
        understanding_scores = await self.evaluate_understanding(user_responses)
        mastered_concepts = [concept for concept, score in understanding_scores.items() if score >= 0.8]
        needs_work_concepts = [concept for concept, score in understanding_scores.items() if score < 0.6]

        # Generate teaching insights
        teaching_insights = self._generate_teaching_insights()

        # Create recommendations
        recommendations = self._generate_feynman_recommendations(understanding_scores, teaching_insights)

        return {
            'total_interactions': total_interactions,
            'teaching_attempts': teaching_attempts,
            'concepts_covered': list(self.get_covered_concepts()),
            'mastered_concepts': mastered_concepts,
            'concepts_needing_work': needs_work_concepts,
            'understanding_scores': understanding_scores,
            'average_teaching_quality': avg_teaching_quality,
            'teaching_progression': teaching_progression,
            'knowledge_gaps_identified': len(set(sum([attempt['analysis'].get('knowledge_gaps', []) for attempt in self.session_context['teaching_attempts']], []))),
            'analogies_used': len(self.session_context['analogies_used']),
            'simplification_mastery': teaching_insights.get('simplification_mastery', 0.5),
            'explanation_clarity': teaching_insights.get('explanation_clarity', 0.5),
            'difficulty_progression': self.session_context['complexity_progression'],
            'session_duration_minutes': self.calculate_duration() / 60,
            'recommendations': recommendations,
            'next_learning_focus': self._determine_next_focus(understanding_scores),
            'feynman_mastery_level': self._calculate_feynman_mastery()
        }

    # Private helper methods for Feynman-specific functionality

    def _select_teaching_concept(self, available_concepts: List[str]) -> str:
        """Select the best concept for teaching based on difficulty and progression."""
        if not available_concepts:
            return "basic concepts"

        # For initial sessions, pick foundational concepts
        if self.get_interaction_count() == 0:
            foundational_keywords = ['introduction', 'basic', 'fundamental', 'overview', 'concept']
            for concept in available_concepts:
                if any(keyword in concept.lower() for keyword in foundational_keywords):
                    return concept
            return available_concepts[0]

        # For ongoing sessions, pick concepts not yet mastered
        taught_concepts = {attempt['concept'] for attempt in self.session_context['teaching_attempts']}
        untaught = [c for c in available_concepts if c not in taught_concepts]

        return random.choice(untaught) if untaught else random.choice(available_concepts)

    def _get_teaching_tips(self, audience: str, concept: str) -> str:
        """Generate audience-specific teaching tips."""
        tips = {
            'child': f"• Use simple words and avoid jargon\n• Think of fun analogies or examples\n• Make it like a story or game",
            'peer': f"• Explain step-by-step clearly\n• Use examples they can relate to\n• Ask yourself: would I understand this if I heard it for the first time?",
            'expert': f"• Focus on deep connections and implications\n• Highlight nuances and advanced aspects\n• Connect to broader theoretical frameworks"
        }
        return tips.get(audience, tips['peer'])

    async def _analyze_teaching_attempt(self, user_input: str, current_prompt: StudyPrompt) -> Dict[str, Any]:
        """Analyze the quality and characteristics of a teaching attempt."""
        analysis = {
            'word_count': len(user_input.split()),
            'simplicity_score': self._calculate_simplicity_score(user_input),
            'clarity_indicators': self._identify_clarity_indicators(user_input),
            'analogies': self._extract_analogies(user_input),
            'knowledge_gaps': self._identify_knowledge_gaps(user_input),
            'technical_depth': self._assess_technical_depth(user_input),
            'teaching_markers': self._identify_teaching_markers(user_input),
            'audience_appropriateness': self._assess_audience_appropriateness(user_input, current_prompt.context.get('target_audience', 'peer'))
        }

        # Generate specific feedback
        analysis['feedback'] = self._generate_detailed_feedback(analysis)
        analysis['stage'] = self._determine_feynman_stage(analysis)

        return analysis

    def _calculate_simplicity_score(self, text: str) -> float:
        """Calculate how simple/accessible the explanation is."""
        words = text.lower().split()

        # Simple indicators
        simple_words = sum(1 for word in words if len(word) <= 6)
        complex_words = sum(1 for word in words if len(word) > 10)

        # Jargon detection
        technical_terms = ['algorithm', 'implementation', 'methodology', 'optimization', 'parameters']
        jargon_count = sum(1 for term in technical_terms if term in text.lower())

        # Sentence complexity
        sentences = text.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

        # Calculate simplicity (0.0 = complex, 1.0 = very simple)
        simplicity = (simple_words / max(len(words), 1)) * 0.4
        simplicity += max(0, (1 - complex_words / max(len(words), 1))) * 0.3
        simplicity += max(0, (1 - jargon_count / 5)) * 0.2
        simplicity += max(0, (1 - avg_sentence_length / 20)) * 0.1

        return min(1.0, max(0.0, simplicity))

    def _identify_clarity_indicators(self, text: str) -> List[str]:
        """Identify markers of clear explanation."""
        clarity_markers = []

        # Structure indicators
        if any(phrase in text.lower() for phrase in ['first', 'second', 'then', 'next', 'finally']):
            clarity_markers.append('sequential_structure')

        if any(phrase in text.lower() for phrase in ['for example', 'such as', 'like when', 'imagine']):
            clarity_markers.append('concrete_examples')

        if any(phrase in text.lower() for phrase in ['in other words', 'basically', 'simply put', 'essentially']):
            clarity_markers.append('simplification_phrases')

        if any(phrase in text.lower() for phrase in ['because', 'since', 'as a result', 'therefore']):
            clarity_markers.append('causal_connections')

        # Question indicators (engaging teaching)
        if '?' in text:
            clarity_markers.append('interactive_questions')

        return clarity_markers

    def _extract_analogies(self, text: str) -> List[str]:
        """Extract analogies and metaphors from the explanation."""
        analogies = []

        # Analogy markers
        analogy_patterns = [
            r'like\s+(?:a\s+)?([^,.!?]+)',
            r'similar to\s+([^,.!?]+)',
            r'think of it as\s+([^,.!?]+)',
            r'imagine\s+([^,.!?]+)',
            r'it\'s like\s+([^,.!?]+)',
            r'just as\s+([^,.!?]+)'
        ]

        for pattern in analogy_patterns:
            matches = re.findall(pattern, text.lower())
            analogies.extend([match.strip() for match in matches])

        # Store unique analogies in session context
        for analogy in analogies:
            if analogy not in self.session_context['analogies_used']:
                self.session_context['analogies_used'].append(analogy)

        return analogies

    def _identify_knowledge_gaps(self, text: str) -> List[str]:
        """Identify potential knowledge gaps from the explanation."""
        gaps = []

        # Uncertainty markers
        uncertainty_phrases = [
            'i think', 'maybe', 'i guess', 'probably', 'i\'m not sure',
            'i believe', 'it might be', 'i don\'t really know'
        ]

        for phrase in uncertainty_phrases:
            if phrase in text.lower():
                gaps.append('uncertainty_in_explanation')
                break

        # Vague explanations
        if any(word in text.lower() for word in ['somehow', 'stuff', 'things', 'kind of']):
            gaps.append('vague_terminology')

        # Incomplete explanations
        if text.count('.') <= 2 and len(text.split()) < 30:
            gaps.append('insufficient_detail')

        # Missing connections
        if not any(word in text.lower() for word in ['because', 'so', 'therefore', 'since', 'as a result']):
            gaps.append('missing_causal_connections')

        return gaps

    def _assess_technical_depth(self, text: str) -> float:
        """Assess the technical depth of the explanation."""
        technical_indicators = ['algorithm', 'model', 'function', 'process', 'system', 'method']
        conceptual_indicators = ['understand', 'learn', 'recognize', 'identify', 'analyze']
        detailed_indicators = ['specifically', 'precisely', 'exactly', 'detailed', 'comprehensive']

        tech_count = sum(1 for indicator in technical_indicators if indicator in text.lower())
        concept_count = sum(1 for indicator in conceptual_indicators if indicator in text.lower())
        detail_count = sum(1 for indicator in detailed_indicators if indicator in text.lower())

        # Normalized depth score
        total_words = len(text.split())
        depth_score = (tech_count + concept_count + detail_count) / max(total_words / 20, 1)

        return min(1.0, depth_score)

    def _identify_teaching_markers(self, text: str) -> List[str]:
        """Identify markers that show teaching intent."""
        markers = []

        # Direct teaching language
        if any(phrase in text.lower() for phrase in ['let me explain', 'so basically', 'what this means']):
            markers.append('direct_teaching_language')

        # Audience awareness
        if any(phrase in text.lower() for phrase in ['you know how', 'you\'ve probably', 'think about']):
            markers.append('audience_engagement')

        # Checking understanding
        if any(phrase in text.lower() for phrase in ['does that make sense', 'understand so far', 'clear?']):
            markers.append('understanding_checks')

        # Building up complexity
        if any(phrase in text.lower() for phrase in ['starting with', 'build up to', 'once you get']):
            markers.append('progressive_complexity')

        return markers

    def _assess_audience_appropriateness(self, text: str, audience: str) -> float:
        """Assess how well the explanation matches the target audience."""
        if audience == 'child':
            # Should be simple, fun, use analogies
            score = self._calculate_simplicity_score(text) * 0.5
            if any(word in text.lower() for word in ['fun', 'game', 'toy', 'animal', 'story']):
                score += 0.3
            if len(self._extract_analogies(text)) > 0:
                score += 0.2
            return min(1.0, score)

        elif audience == 'expert':
            # Should have technical depth, precision, connections
            depth_score = self._assess_technical_depth(text)
            precision_score = 1.0 if any(word in text.lower() for word in ['specifically', 'precisely', 'exact']) else 0.5
            connection_score = 1.0 if any(word in text.lower() for word in ['relates to', 'connects', 'builds on']) else 0.5
            return (depth_score + precision_score + connection_score) / 3

        else:  # peer
            # Should be clear, structured, with examples
            clarity_score = len(self._identify_clarity_indicators(text)) / 5
            structure_score = 1.0 if any(word in text.lower() for word in ['first', 'then', 'finally']) else 0.5
            example_score = 1.0 if any(phrase in text.lower() for phrase in ['for example', 'like']) else 0.5
            return (clarity_score + structure_score + example_score) / 3

    def _generate_detailed_feedback(self, analysis: Dict[str, Any]) -> str:
        """Generate specific feedback based on analysis."""
        feedback_parts = []

        # Simplicity feedback
        if analysis['simplicity_score'] > 0.7:
            feedback_parts.append("Great job keeping your explanation simple and accessible!")
        elif analysis['simplicity_score'] < 0.4:
            feedback_parts.append("Try using simpler words and shorter sentences to make this clearer.")

        # Analogies feedback
        if analysis['analogies']:
            feedback_parts.append(f"Excellent use of analogies! '{analysis['analogies'][0]}' really helps clarify the concept.")
        else:
            feedback_parts.append("Consider adding an analogy or real-world example to make this more relatable.")

        # Knowledge gaps feedback
        if analysis['knowledge_gaps']:
            gap_feedback = {
                'uncertainty_in_explanation': "I can sense some uncertainty. Let's explore the parts you're less sure about.",
                'vague_terminology': "Try to be more specific - avoid words like 'stuff' or 'things'.",
                'insufficient_detail': "You're on the right track! Can you expand with more details?",
                'missing_causal_connections': "Great explanation! Now try adding 'because' or 'so that' to show how things connect."
            }
            for gap in analysis['knowledge_gaps']:
                if gap in gap_feedback:
                    feedback_parts.append(gap_feedback[gap])

        return " ".join(feedback_parts) if feedback_parts else "Good explanation! Let's refine it further."

    def _determine_feynman_stage(self, analysis: Dict[str, Any]) -> str:
        """Determine which stage of Feynman learning the user is in."""
        if analysis['knowledge_gaps']:
            return 'identifying_gaps'
        elif analysis['simplicity_score'] < 0.5:
            return 'simplification_needed'
        elif not analysis['analogies'] and analysis['technical_depth'] > 0.5:
            return 'needs_analogies'
        elif analysis['clarity_indicators'] and analysis['simplicity_score'] > 0.6:
            return 'mastery_demonstration'
        else:
            return 'explanation_refinement'

    def _calculate_teaching_quality(self, user_input: str, analysis: Dict[str, Any]) -> float:
        """Calculate overall teaching quality score."""
        # Weight different aspects
        simplicity_weight = 0.25
        clarity_weight = 0.25
        completeness_weight = 0.20
        audience_weight = 0.15
        engagement_weight = 0.15

        simplicity_score = analysis['simplicity_score']
        clarity_score = len(analysis['clarity_indicators']) / 5  # Normalize to 0-1
        completeness_score = 1.0 - (len(analysis['knowledge_gaps']) / 4)  # Fewer gaps = better
        audience_score = analysis['audience_appropriateness']
        engagement_score = (len(analysis['analogies']) + len(analysis['teaching_markers'])) / 4

        total_score = (
            simplicity_score * simplicity_weight +
            clarity_score * clarity_weight +
            max(0, completeness_score) * completeness_weight +
            audience_score * audience_weight +
            min(1.0, engagement_score) * engagement_weight
        )

        return min(1.0, max(0.0, total_score))

    async def _generate_feynman_feedback(self, user_input: str, analysis: Dict[str, Any], current_prompt: StudyPrompt) -> str:
        """Generate Feynman-style feedback focusing on teaching improvement."""
        # Start with positive reinforcement
        positive_starts = [
            "I love how you're thinking like a teacher!",
            "You're really getting the hang of explanation!",
            "That's the Feynman spirit - teaching to understand!",
            "Great teaching mindset!"
        ]

        feedback = random.choice(positive_starts) + " "

        # Add specific feedback based on analysis
        if analysis['analogies']:
            feedback += f"Your analogy about '{analysis['analogies'][0]}' is particularly helpful. "

        if analysis['simplicity_score'] > 0.7:
            feedback += "You're doing an excellent job keeping things simple and clear. "
        elif analysis['simplicity_score'] < 0.4:
            feedback += "Let's work on simplifying this - imagine explaining it to someone who's never heard of this before. "

        # Address knowledge gaps constructively
        if analysis['knowledge_gaps']:
            if 'uncertainty_in_explanation' in analysis['knowledge_gaps']:
                feedback += "I notice some uncertainty in your explanation. That's actually great - it shows you're identifying areas to explore deeper! "
            if 'vague_terminology' in analysis['knowledge_gaps']:
                feedback += "Try to be more specific with your terms - your future students will thank you! "

        # Encourage next steps
        stage = analysis['stage']
        if stage == 'identifying_gaps':
            feedback += "Perfect! You've identified some knowledge gaps. This is exactly what the Feynman technique is about - finding what we need to learn better."
        elif stage == 'simplification_needed':
            feedback += "Now let's see if you can explain this even more simply. What's the core idea in just one sentence?"
        elif stage == 'needs_analogies':
            feedback += "You've got the technical understanding! Now, can you think of an everyday analogy that would help someone visualize this?"
        elif stage == 'mastery_demonstration':
            feedback += "Excellent! You're showing real mastery. You can explain it clearly, simply, and with confidence."

        return feedback

    async def _generate_next_teaching_challenge(self, analysis: Dict[str, Any], current_prompt: StudyPrompt) -> Optional[StudyPrompt]:
        """Generate the next teaching challenge based on current performance."""
        current_concept = current_prompt.context.get('teaching_concept', 'concepts')
        current_audience = current_prompt.context.get('target_audience', 'peer')
        stage = analysis['stage']

        # Determine next challenge type
        if stage == 'identifying_gaps':
            # Address specific gaps
            challenge_text = f"Let's fill in those knowledge gaps! Pick one aspect of {current_concept} you felt uncertain about and research it. Then explain it to me in your own words."
            prompt_type = PromptType.CHALLENGE

        elif stage == 'simplification_needed':
            # Simplification challenge
            challenge_text = f"Challenge time! Explain {current_concept} using only the 1000 most common English words. This will force you to be really clear about the core ideas."
            prompt_type = PromptType.CHALLENGE

        elif stage == 'needs_analogies':
            # Analogy challenge
            challenge_text = f"Great technical understanding! Now create an analogy for {current_concept}. What everyday thing works similarly? Help me visualize it!"
            prompt_type = PromptType.CHALLENGE

        elif stage == 'mastery_demonstration':
            # Audience switch or complexity increase
            new_audience = self._get_next_audience(current_audience)
            if new_audience != current_audience:
                challenge_text = f"Excellent mastery! Now let's test your flexibility - explain {current_concept} to a {new_audience}. How would you adjust your teaching?"
                self.session_context['current_audience'] = new_audience
            else:
                # Move to next concept
                context = await self.get_document_context(self.documents)
                next_concept = self._select_teaching_concept(context.get('key_concepts', [current_concept]))
                challenge_text = f"You've mastered {current_concept}! Ready for the next challenge? Teach me about {next_concept}."
            prompt_type = PromptType.EXPLANATION_REQUEST

        else:
            # Refinement challenge
            challenge_text = f"You're doing well! Now refine your explanation of {current_concept} - make it even clearer and more engaging. What would make this stick in someone's memory?"
            prompt_type = PromptType.EXPLANATION_REQUEST

        return StudyPrompt(
            prompt_text=challenge_text,
            prompt_type=prompt_type,
            difficulty_level=self.difficulty_level,
            expected_concepts=[current_concept],
            context={
                'voice_compatible': True,
                'teaching_concept': current_concept,
                'target_audience': self.session_context['current_audience'],
                'feynman_stage': stage,
                'challenge_type': 'refinement'
            },
            related_documents=self.documents
        )

    def _generate_teaching_suggestions(self, analysis: Dict[str, Any], quality_score: float) -> List[str]:
        """Generate specific suggestions for improving teaching."""
        suggestions = []

        # Quality-based suggestions
        if quality_score < 0.5:
            suggestions.append("Break down complex ideas into smaller, digestible pieces")
            suggestions.append("Use more everyday language and avoid technical jargon")
        elif quality_score < 0.7:
            suggestions.append("Add concrete examples or analogies to clarify abstract concepts")
            suggestions.append("Structure your explanation with clear steps (first, then, finally)")
        else:
            suggestions.append("Try explaining this concept to different audiences")
            suggestions.append("Challenge yourself with even more complex related topics")

        # Analysis-specific suggestions
        if not analysis['analogies']:
            suggestions.append("Think of a real-world analogy that relates to this concept")

        if 'uncertainty_in_explanation' in analysis['knowledge_gaps']:
            suggestions.append("Research the parts you're unsure about, then try explaining again")

        if analysis['simplicity_score'] < 0.5:
            suggestions.append("Try the '1000 most common words' challenge for ultimate simplicity")

        if len(analysis['clarity_indicators']) < 2:
            suggestions.append("Use transition words (because, therefore, for example) to connect ideas")

        # Progressive suggestions
        interaction_count = self.get_interaction_count()
        if interaction_count > 3:
            suggestions.append("Try teaching this same concept to a child, then to an expert")
        if interaction_count > 5:
            suggestions.append("Create a visual diagram or flowchart of your explanation")

        return suggestions[:4]  # Limit to 4 suggestions

    def _determine_session_stage(self, analysis: Dict[str, Any], quality_score: float) -> SessionStage:
        """Determine appropriate session stage based on teaching progress."""
        if quality_score > 0.8 and len(analysis['knowledge_gaps']) == 0:
            return SessionStage.TRANSITIONING  # Ready for more advanced concepts
        elif self.get_interaction_count() > 10:
            return SessionStage.ACTIVE  # Ongoing productive session
        else:
            return SessionStage.ACTIVE

    def _get_next_audience(self, current_audience: str) -> str:
        """Get next audience for teaching progression."""
        progression = ['child', 'peer', 'expert']
        try:
            current_index = progression.index(current_audience)
            return progression[(current_index + 1) % len(progression)]
        except ValueError:
            return 'peer'

    def _analyze_teaching_progression(self) -> Dict[str, Any]:
        """Analyze how the user's teaching ability has progressed."""
        if not self.session_context['explanation_quality_scores']:
            return {'progression': 'insufficient_data'}

        scores = self.session_context['explanation_quality_scores']

        # Calculate trend
        if len(scores) >= 3:
            early_avg = sum(scores[:3]) / 3
            recent_avg = sum(scores[-3:]) / 3
            improvement = recent_avg - early_avg
        else:
            improvement = 0

        return {
            'initial_score': scores[0] if scores else 0,
            'current_score': scores[-1] if scores else 0,
            'improvement': improvement,
            'best_score': max(scores) if scores else 0,
            'consistency': self._calculate_consistency(scores),
            'progression': 'improving' if improvement > 0.1 else 'stable' if improvement > -0.1 else 'declining'
        }

    def _calculate_consistency(self, scores: List[float]) -> float:
        """Calculate consistency of teaching performance."""
        if len(scores) < 2:
            return 1.0

        # Calculate standard deviation
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = variance ** 0.5

        # Convert to consistency score (lower std_dev = higher consistency)
        consistency = max(0, 1 - (std_dev * 2))
        return consistency

    def _generate_teaching_insights(self) -> Dict[str, Any]:
        """Generate insights about teaching mastery."""
        insights = {}

        # Simplification mastery
        if self.session_context['explanation_quality_scores']:
            simplification_scores = [0.7, 0.8, 0.6]  # Placeholder for actual simplification tracking
            insights['simplification_mastery'] = sum(simplification_scores) / len(simplification_scores)
        else:
            insights['simplification_mastery'] = 0.5

        # Explanation clarity
        clarity_scores = [len(attempt['analysis'].get('clarity_indicators', [])) / 5
                         for attempt in self.session_context['teaching_attempts']]
        insights['explanation_clarity'] = sum(clarity_scores) / max(len(clarity_scores), 1)

        # Analogy usage
        insights['analogy_effectiveness'] = min(1.0, len(self.session_context['analogies_used']) / 3)

        # Knowledge gap identification
        total_gaps = sum(len(attempt['analysis'].get('knowledge_gaps', []))
                        for attempt in self.session_context['teaching_attempts'])
        insights['gap_identification'] = min(1.0, total_gaps / 5)  # More gaps found = better self-awareness

        return insights

    def _generate_feynman_recommendations(self, understanding_scores: Dict[str, float], insights: Dict[str, Any]) -> List[str]:
        """Generate Feynman-specific recommendations."""
        recommendations = []

        # Understanding-based recommendations
        weak_concepts = [concept for concept, score in understanding_scores.items() if score < 0.6]
        strong_concepts = [concept for concept, score in understanding_scores.items() if score > 0.8]

        if weak_concepts:
            recommendations.append(f"Focus on teaching {weak_concepts[0]} using the simplest possible language")

        if strong_concepts:
            recommendations.append(f"You've mastered {strong_concepts[0]}! Try teaching it to different audiences")

        # Insights-based recommendations
        if insights.get('simplification_mastery', 0.5) < 0.6:
            recommendations.append("Practice the '1000 most common words' challenge to improve simplification")

        if insights.get('analogy_effectiveness', 0.5) < 0.5:
            recommendations.append("Work on creating more analogies - they're key to great teaching")

        if insights.get('explanation_clarity', 0.5) < 0.6:
            recommendations.append("Use more transition words and structure in your explanations")

        # General Feynman recommendations
        recommendations.append("Try explaining concepts to friends or family - real teaching is the best practice")
        recommendations.append("When you get stuck, dig deeper into that specific area - gaps are learning opportunities")

        return recommendations[:5]  # Limit to 5 recommendations

    def _determine_next_focus(self, understanding_scores: Dict[str, float]) -> str:
        """Determine what the user should focus on next."""
        if not understanding_scores:
            return "Continue practicing explanations with simple language"

        # Find the concept with lowest score
        weakest_concept = min(understanding_scores.items(), key=lambda x: x[1])

        if weakest_concept[1] < 0.4:
            return f"Deep dive into {weakest_concept[0]} - break it down into smaller parts"
        elif weakest_concept[1] < 0.7:
            return f"Practice explaining {weakest_concept[0]} with analogies and examples"
        else:
            return "Explore more advanced concepts or try teaching to different audiences"

    def _calculate_feynman_mastery(self) -> float:
        """Calculate overall Feynman technique mastery level."""
        if not self.session_context['explanation_quality_scores']:
            return 0.0

        # Average teaching quality
        avg_quality = sum(self.session_context['explanation_quality_scores']) / len(self.session_context['explanation_quality_scores'])

        # Bonus for progression and consistency
        progression = self._analyze_teaching_progression()
        progression_bonus = 0.1 if progression.get('improvement', 0) > 0 else 0
        consistency_bonus = progression.get('consistency', 0.5) * 0.1

        # Bonus for analogy usage
        analogy_bonus = min(0.1, len(self.session_context['analogies_used']) / 10)

        mastery = avg_quality + progression_bonus + consistency_bonus + analogy_bonus
        return min(1.0, mastery)

    def _generate_encouragement_response(self, message: str) -> SessionResponse:
        """Generate an encouraging response for brief or unclear input."""
        return SessionResponse(
            ai_message=f"{message} Remember, the Feynman technique is all about learning through teaching. Take your time and explain it as if you're helping a friend understand for the first time.",
            feedback="More detail needed for effective teaching practice",
            suggestions=[
                "Expand your explanation with more details",
                "Think about how you'd explain this to someone who knows nothing about it",
                "Use examples or analogies to make it clearer"
            ],
            progress_percentage=self.calculate_session_progress(),
            session_stage=SessionStage.ACTIVE,
            metadata={
                'voice_compatible': True,
                'response_type': 'encouragement',
                'feynman_stage': 'needs_elaboration'
            }
        )

    async def _evaluate_teaching_mastery(self, concept: str, user_responses: List[str]) -> float:
        """Evaluate teaching mastery for a specific concept."""
        # Find responses that mention this concept
        relevant_responses = [response for response in user_responses if concept.lower() in response.lower()]

        if not relevant_responses:
            return 0.3  # Some basic understanding assumed

        # Analyze teaching quality for this concept
        total_score = 0
        for response in relevant_responses:
            # Mock analysis for concept-specific evaluation
            simplicity = self._calculate_simplicity_score(response)
            has_analogy = 1.0 if any(marker in response.lower() for marker in ['like', 'similar to', 'imagine']) else 0.5
            has_structure = 1.0 if any(marker in response.lower() for marker in ['first', 'then', 'because']) else 0.5

            score = (simplicity * 0.5) + (has_analogy * 0.25) + (has_structure * 0.25)
            total_score += score

        avg_score = total_score / len(relevant_responses)

        # Boost score based on teaching attempts for this concept
        teaching_attempts = [attempt for attempt in self.session_context['teaching_attempts']
                           if attempt['concept'] == concept]
        if teaching_attempts:
            latest_attempt = teaching_attempts[-1]
            quality_boost = latest_attempt['analysis'].get('simplicity_score', 0.5) * 0.2
            avg_score += quality_boost

        return min(1.0, avg_score)
