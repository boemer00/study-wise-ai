"""
Response generation for the Conversational RAG system.

This module handles generating intelligent, contextual responses to user
questions using retrieved document context and conversation history.
"""

import asyncio
import re
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from openai import AsyncOpenAI

from .models import (
    ChatResponse,
    DocumentSource,
    Message,
    QuestionType,
    ResponseStrategy,
    MessageRole
)

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generates intelligent responses using LLM and retrieved context.

    Handles prompt engineering, response generation, and post-processing
    to create helpful, accurate, and engaging study assistant responses.
    """

    def __init__(
        self,
        openai_api_key: str,
        model_name: str = "gpt-4",
        max_response_tokens: int = 1000,
        temperature: float = 0.7,
        include_sources: bool = True
    ) -> None:
        """
        Initialize response generator.

        Args:
            openai_api_key: OpenAI API key
            model_name: OpenAI model to use for generation
            max_response_tokens: Maximum tokens in response
            temperature: Creativity/randomness of responses (0-1)
            include_sources: Whether to include source citations
        """
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.model_name = model_name
        self.max_response_tokens = max_response_tokens
        self.temperature = temperature
        self.include_sources = include_sources

        # Safety filters
        self.safety_keywords = {
            'harmful', 'dangerous', 'illegal', 'inappropriate', 'offensive',
            'discriminatory', 'hateful', 'violent', 'explicit', 'nsfw'
        }

    async def generate_response(
        self,
        user_query: str,
        retrieved_context: List[DocumentSource],
        conversation_history: Optional[List[Message]] = None,
        question_type: Optional[QuestionType] = None,
        response_strategy: Optional[ResponseStrategy] = None
    ) -> ChatResponse:
        """
        Generate a comprehensive response to the user's question.

        Args:
            user_query: User's question
            retrieved_context: Relevant document chunks
            conversation_history: Recent conversation messages
            question_type: Type of question being asked
            response_strategy: Strategy for response generation

        Returns:
            ChatResponse with answer and metadata

        Raises:
            ResponseGenerationError: If response generation fails
        """
        try:
            # Determine response strategy if not provided
            if response_strategy is None:
                context_quality = sum(chunk.relevance_score for chunk in retrieved_context) / len(retrieved_context) if retrieved_context else 0.0
                response_strategy = await self.determine_response_strategy(
                    question_type or QuestionType.FACTUAL,
                    context_quality
                )

            # Build system prompt
            system_prompt = self._build_system_prompt(
                question_type or QuestionType.FACTUAL,
                response_strategy
            )

            # Format context for LLM
            formatted_context = self._format_context_for_llm(retrieved_context)

            # Format conversation history
            conversation_context = self._format_conversation_history(conversation_history)

            # Build user prompt
            user_prompt = self._build_user_prompt(
                user_query,
                formatted_context,
                conversation_context,
                response_strategy
            )

            # Generate response using OpenAI
            response_text = await self._call_openai_api(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                self.max_response_tokens,
                self.temperature
            )

            # Apply safety filters
            filtered_response = self._apply_response_filters(response_text)

            # Extract citations if enabled
            used_sources = []
            if self.include_sources and retrieved_context:
                used_sources = self._extract_citations(filtered_response, retrieved_context)

            # Generate follow-up suggestions
            follow_up_suggestions = await self.generate_follow_up_suggestions(
                user_query,
                filtered_response,
                retrieved_context
            )

            # Assess confidence
            confidence_score = await self.assess_response_confidence(
                user_query,
                retrieved_context,
                filtered_response
            )

            return ChatResponse(
                answer=filtered_response,
                sources=used_sources,
                conversation_id="",  # Will be set by caller
                response_id="",  # Will be set by caller
                follow_up_suggestions=follow_up_suggestions,
                confidence_score=confidence_score,
                processing_time_ms=None,  # Will be set by caller
                metadata={
                    "question_type": question_type.value if question_type else None,
                    "response_strategy": response_strategy.value,
                    "context_chunks_used": len(retrieved_context),
                    "model_used": self.model_name
                }
            )

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise ResponseGenerationError(f"Failed to generate response: {str(e)}")

    async def determine_response_strategy(
        self,
        question_type: QuestionType,
        context_quality: float,
        user_level: Optional[str] = None
    ) -> ResponseStrategy:
        """
        Determine the best strategy for responding to the question.

        Args:
            question_type: Type of question being asked
            context_quality: Quality score of retrieved context
            user_level: User's expertise level (beginner/intermediate/advanced)

        Returns:
            Optimal response strategy
        """
        try:
            # Base strategy mapping by question type
            type_strategies = {
                QuestionType.FACTUAL: ResponseStrategy.DIRECT_ANSWER,
                QuestionType.CONCEPTUAL: ResponseStrategy.GUIDED_DISCOVERY,
                QuestionType.APPLICATION: ResponseStrategy.STEP_BY_STEP,
                QuestionType.COMPARISON: ResponseStrategy.COMPARATIVE,
                QuestionType.EXPLANATION: ResponseStrategy.GUIDED_DISCOVERY,
                QuestionType.SYNTHESIS: ResponseStrategy.EXAMPLE_BASED
            }

            base_strategy = type_strategies.get(question_type, ResponseStrategy.DIRECT_ANSWER)

            # Adjust based on context quality
            if context_quality < 0.5:
                # Low quality context - use simpler approach
                if base_strategy == ResponseStrategy.GUIDED_DISCOVERY:
                    return ResponseStrategy.DIRECT_ANSWER
                elif base_strategy == ResponseStrategy.EXAMPLE_BASED:
                    return ResponseStrategy.DIRECT_ANSWER
            elif context_quality > 0.8:
                # High quality context - can use more sophisticated approaches
                if base_strategy == ResponseStrategy.DIRECT_ANSWER and question_type in [QuestionType.CONCEPTUAL, QuestionType.EXPLANATION]:
                    return ResponseStrategy.GUIDED_DISCOVERY

            # Adjust based on user level
            if user_level == "beginner":
                if base_strategy in [ResponseStrategy.GUIDED_DISCOVERY, ResponseStrategy.EXAMPLE_BASED]:
                    return ResponseStrategy.STEP_BY_STEP
            elif user_level == "advanced":
                if base_strategy == ResponseStrategy.STEP_BY_STEP:
                    return ResponseStrategy.DIRECT_ANSWER

            logger.debug(f"Selected strategy {base_strategy.value} for {question_type.value} question")
            return base_strategy

        except Exception as e:
            logger.warning(f"Strategy determination failed: {str(e)}")
            return ResponseStrategy.DIRECT_ANSWER

    async def generate_follow_up_suggestions(
        self,
        user_query: str,
        generated_response: str,
        context_sources: List[DocumentSource]
    ) -> List[str]:
        """
        Generate suggested follow-up questions for continued learning.

        Args:
            user_query: Original user question
            generated_response: Generated response
            context_sources: Document sources used

        Returns:
            List of suggested follow-up questions
        """
        try:
            # Extract key topics from response and sources
            topics = set()

            # Extract from response (simple keyword extraction)
            response_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', generated_response)
            topics.update(response_words[:5])

            # Extract from source titles
            for source in context_sources[:3]:
                title_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', source.title)
                topics.update(title_words[:2])

            if not topics:
                return []

            # Generate follow-up questions using LLM
            topics_text = ", ".join(list(topics)[:5])
            prompt = f"""Based on this study session about "{user_query}", suggest 3 follow-up questions that would help the student learn more.

Topics covered: {topics_text}

Generate questions that:
1. Explore related concepts
2. Apply the knowledge practically
3. Make connections to other topics

Return only the questions, one per line:"""

            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.8
                )

                suggestions_text = response.choices[0].message.content.strip()
                suggestions = [q.strip() for q in suggestions_text.split('\n') if q.strip() and '?' in q]

                # Clean and validate suggestions
                cleaned_suggestions = []
                for suggestion in suggestions[:3]:
                    # Remove numbering, bullets, etc.
                    cleaned = re.sub(r'^\d+\.\s*|^-\s*|^\*\s*', '', suggestion).strip()
                    if len(cleaned) > 10 and len(cleaned) < 100:
                        cleaned_suggestions.append(cleaned)

                return cleaned_suggestions

            except Exception as e:
                logger.warning(f"LLM follow-up generation failed: {str(e)}")

            # Fallback: template-based suggestions
            fallback_suggestions = [
                f"Can you explain more about {list(topics)[0]}?" if topics else "Can you provide more examples?",
                f"How does this relate to other concepts?",
                f"What are some practical applications of this?"
            ]

            return fallback_suggestions[:2]

        except Exception as e:
            logger.warning(f"Follow-up generation failed: {str(e)}")
            return []

    async def assess_response_confidence(
        self,
        user_query: str,
        context_sources: List[DocumentSource],
        generated_response: str
    ) -> float:
        """
        Assess confidence level in the generated response.

        Args:
            user_query: User's question
            context_sources: Retrieved context sources
            generated_response: Generated response

        Returns:
            Confidence score between 0 and 1
        """
        try:
            confidence_score = 0.5  # Base confidence

            # Factor 1: Context quality (40% weight)
            if context_sources:
                avg_relevance = sum(source.relevance_score for source in context_sources) / len(context_sources)
                context_contribution = min(avg_relevance, 0.4)
                confidence_score += context_contribution

            # Factor 2: Response completeness (30% weight)
            response_length = len(generated_response.split())
            if response_length > 50:  # Detailed response
                confidence_score += 0.2
            elif response_length > 20:  # Moderate response
                confidence_score += 0.1

            # Factor 3: Source citations (20% weight)
            if self.include_sources and context_sources:
                # Check if response references sources
                citation_indicators = ['according to', 'as stated', 'from the', 'in the document', 'the source']
                has_citations = any(indicator in generated_response.lower() for indicator in citation_indicators)
                if has_citations:
                    confidence_score += 0.15

            # Factor 4: Query-response alignment (10% weight)
            query_words = set(user_query.lower().split())
            response_words = set(generated_response.lower().split())
            if query_words:
                alignment = len(query_words & response_words) / len(query_words)
                confidence_score += alignment * 0.1

            # Ensure score is within bounds
            final_confidence = max(0.0, min(1.0, confidence_score))

            logger.debug(f"Assessed response confidence: {final_confidence:.2f}")
            return final_confidence

        except Exception as e:
            logger.warning(f"Confidence assessment failed: {str(e)}")
            return 0.5

    def _build_system_prompt(
        self,
        question_type: QuestionType,
        response_strategy: ResponseStrategy,
        user_level: Optional[str] = None
    ) -> str:
        """
        Build system prompt for the language model.

        Args:
            question_type: Type of question being asked
            response_strategy: Strategy for response generation
            user_level: User's expertise level

        Returns:
            System prompt string
        """
        base_prompt = """You are StudyWise AI, an intelligent study assistant designed to help students learn effectively. Your role is to provide accurate, helpful, and engaging responses to student questions based on their course materials and documents.

Core principles:
- Be accurate and factual, grounding responses in provided context
- Adapt your explanation style to the student's needs
- Encourage deeper learning and critical thinking
- Cite sources when available
- Be concise but thorough"""

        # Add question type specific guidance
        type_guidance = {
            QuestionType.FACTUAL: "\n\nFor factual questions: Provide clear, precise definitions and facts. Include relevant examples when helpful.",
            QuestionType.CONCEPTUAL: "\n\nFor conceptual questions: Explain the underlying mechanisms and processes. Use analogies and examples to clarify complex ideas.",
            QuestionType.APPLICATION: "\n\nFor application questions: Provide step-by-step guidance and practical examples. Focus on how-to instructions.",
            QuestionType.COMPARISON: "\n\nFor comparison questions: Clearly highlight similarities and differences. Use structured comparisons and contrasts.",
            QuestionType.EXPLANATION: "\n\nFor explanation questions: Focus on the 'why' and underlying reasons. Explain cause-and-effect relationships.",
            QuestionType.SYNTHESIS: "\n\nFor synthesis questions: Show connections and relationships between concepts. Help integrate knowledge."
        }

        # Add strategy specific guidance
        strategy_guidance = {
            ResponseStrategy.DIRECT_ANSWER: "\n\nResponse style: Provide direct, straightforward answers. Be clear and to the point.",
            ResponseStrategy.GUIDED_DISCOVERY: "\n\nResponse style: Guide the student to discover answers through leading questions and hints. Encourage thinking.",
            ResponseStrategy.EXAMPLE_BASED: "\n\nResponse style: Use concrete examples and case studies to illustrate concepts. Make abstract ideas tangible.",
            ResponseStrategy.COMPARATIVE: "\n\nResponse style: Use comparisons and contrasts to explain concepts. Highlight relationships between ideas.",
            ResponseStrategy.STEP_BY_STEP: "\n\nResponse style: Break down complex processes into clear, sequential steps. Number or structure your explanation."
        }

        # Add user level adaptation
        level_guidance = ""
        if user_level == "beginner":
            level_guidance = "\n\nUser level: Beginner - Use simple language, define technical terms, and provide extra context."
        elif user_level == "intermediate":
            level_guidance = "\n\nUser level: Intermediate - Balance detail with clarity, introduce some advanced concepts."
        elif user_level == "advanced":
            level_guidance = "\n\nUser level: Advanced - Use technical language appropriately, focus on nuanced details and advanced applications."

        # Combine all parts
        full_prompt = (
            base_prompt +
            type_guidance.get(question_type, "") +
            strategy_guidance.get(response_strategy, "") +
            level_guidance
        )

        return full_prompt

    def _format_context_for_llm(
        self,
        context_sources: List[DocumentSource],
        max_context_length: int = 3000
    ) -> str:
        """
        Format retrieved context for inclusion in LLM prompt.

        Args:
            context_sources: Retrieved document chunks
            max_context_length: Maximum context length in characters

        Returns:
            Formatted context string
        """
        if not context_sources:
            return "No relevant context found in your documents."

        formatted_parts = []
        current_length = 0

        for i, source in enumerate(context_sources):
            # Format source with citation
            source_text = f"[Source {i+1}: {source.title}]\n{source.content_snippet}\n"

            # Check if adding this source would exceed limit
            if current_length + len(source_text) > max_context_length:
                break

            formatted_parts.append(source_text)
            current_length += len(source_text)

        if formatted_parts:
            context_header = f"Relevant information from your study materials ({len(formatted_parts)} sources):\n\n"
            return context_header + "\n".join(formatted_parts)
        else:
            return "Limited relevant context found in your documents."

    def _format_conversation_history(
        self,
        conversation_history: Optional[List[Message]],
        max_messages: int = 5
    ) -> str:
        """
        Format conversation history for LLM context.

        Args:
            conversation_history: Recent conversation messages
            max_messages: Maximum messages to include

        Returns:
            Formatted conversation history
        """
        if not conversation_history:
            return ""

        # Get recent messages
        recent_messages = conversation_history[-max_messages:]

        formatted_messages = []
        for message in recent_messages:
            if message.role == MessageRole.USER:
                formatted_messages.append(f"Student: {message.content}")
            elif message.role == MessageRole.ASSISTANT:
                # Truncate long assistant responses
                content = message.content[:200] + "..." if len(message.content) > 200 else message.content
                formatted_messages.append(f"StudyWise: {content}")

        if formatted_messages:
            return f"Previous conversation:\n" + "\n".join(formatted_messages) + "\n\n"
        else:
            return ""

    def _build_user_prompt(
        self,
        user_query: str,
        formatted_context: str,
        conversation_context: str,
        response_strategy: ResponseStrategy
    ) -> str:
        """
        Build the complete user prompt for the LLM.

        Args:
            user_query: User's question
            formatted_context: Formatted document context
            conversation_context: Formatted conversation history
            response_strategy: Response generation strategy

        Returns:
            Complete user prompt
        """
        prompt_parts = []

        # Add conversation context if present
        if conversation_context:
            prompt_parts.append(conversation_context)

        # Add document context
        prompt_parts.append(formatted_context)

        # Add current question
        prompt_parts.append(f"Current question: {user_query}")

        # Add strategy-specific instructions
        strategy_instructions = {
            ResponseStrategy.DIRECT_ANSWER: "Please provide a clear, direct answer based on the context above.",
            ResponseStrategy.GUIDED_DISCOVERY: "Help me understand this by asking questions and providing hints rather than giving the answer directly.",
            ResponseStrategy.EXAMPLE_BASED: "Please explain this using concrete examples from the context or related real-world examples.",
            ResponseStrategy.COMPARATIVE: "Please explain this by comparing and contrasting with related concepts.",
            ResponseStrategy.STEP_BY_STEP: "Please break this down into clear, sequential steps."
        }

        instruction = strategy_instructions.get(response_strategy, "Please provide a helpful response based on the context above.")
        prompt_parts.append(instruction)

        return "\n\n".join(prompt_parts)

    def _extract_citations(
        self,
        response_text: str,
        context_sources: List[DocumentSource]
    ) -> List[DocumentSource]:
        """
        Extract and validate citations from the generated response.

        Args:
            response_text: Generated response text
            context_sources: Available context sources

        Returns:
            List of cited document sources
        """
        try:
            cited_sources = []

            # Look for source references in response
            source_patterns = [
                r'\[Source (\d+)(?::\s*[^\]]+)?\]',  # [Source 1] or [Source 1: Title]
                r'according to source (\d+)',         # according to source 1
                r'source (\d+) states',               # source 1 states
                r'from source (\d+)',                 # from source 1
            ]

            referenced_indices = set()
            for pattern in source_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                for match in matches:
                    try:
                        index = int(match) - 1  # Convert to 0-based index
                        if 0 <= index < len(context_sources):
                            referenced_indices.add(index)
                    except ValueError:
                        continue

            # If no explicit citations found, assume all sources were potentially used
            if not referenced_indices and context_sources:
                # Use heuristic: check if source content appears in response
                response_lower = response_text.lower()
                for i, source in enumerate(context_sources):
                    # Check if key phrases from source appear in response
                    source_words = source.content_snippet.lower().split()
                    if len(source_words) >= 3:
                        # Look for 3-word phrases from source in response
                        for j in range(len(source_words) - 2):
                            phrase = " ".join(source_words[j:j+3])
                            if phrase in response_lower:
                                referenced_indices.add(i)
                                break

            # Build list of cited sources
            for index in sorted(referenced_indices):
                if index < len(context_sources):
                    cited_sources.append(context_sources[index])

            # If still no sources identified but we have high-quality sources, include top ones
            if not cited_sources and context_sources:
                # Include sources with relevance > 0.8
                high_quality_sources = [source for source in context_sources if source.relevance_score > 0.8]
                cited_sources = high_quality_sources[:2]  # Top 2 high-quality sources

            logger.debug(f"Extracted {len(cited_sources)} citations from response")
            return cited_sources

        except Exception as e:
            logger.warning(f"Citation extraction failed: {str(e)}")
            return context_sources[:2] if context_sources else []

    def _apply_response_filters(
        self,
        response_text: str,
        safety_filters: List[str] = None
    ) -> str:
        """
        Apply safety and quality filters to response.

        Args:
            response_text: Generated response text
            safety_filters: List of safety filters to apply

        Returns:
            Filtered response text
        """
        try:
            filtered_text = response_text.strip()

            # Basic safety check
            response_lower = filtered_text.lower()
            for keyword in self.safety_keywords:
                if keyword in response_lower:
                    logger.warning(f"Safety keyword '{keyword}' detected in response")
                    # For now, just log; in production, might want to regenerate

            # Remove excessive whitespace
            filtered_text = re.sub(r'\n\s*\n\s*\n', '\n\n', filtered_text)
            filtered_text = re.sub(r' +', ' ', filtered_text)

            # Ensure response ends properly
            if filtered_text and not filtered_text.endswith(('.', '!', '?', ':')):
                filtered_text += '.'

            # Length check
            if len(filtered_text) < 10:
                logger.warning("Generated response too short")
                filtered_text = "I apologize, but I need more information to provide a helpful response. Could you please rephrase your question or provide more context?"
            elif len(filtered_text) > 5000:
                logger.warning("Generated response too long, truncating")
                filtered_text = filtered_text[:4500] + "..."

            return filtered_text

        except Exception as e:
            logger.warning(f"Response filtering failed: {str(e)}")
            return response_text

    async def _call_openai_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> str:
        """
        Make API call to OpenAI for response generation.

        Args:
            messages: Conversation messages for the API
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature

        Returns:
            Generated response text

        Raises:
            OpenAIAPIError: If API call fails
        """
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )

            if not response.choices:
                raise OpenAIAPIError("No response choices returned from OpenAI")

            generated_text = response.choices[0].message.content
            if not generated_text:
                raise OpenAIAPIError("Empty response from OpenAI")

            logger.debug(f"Generated response: {len(generated_text)} characters")
            return generated_text.strip()

        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise OpenAIAPIError(f"OpenAI API error: {str(e)}")


class ResponseGenerationError(Exception):
    """Raised when response generation fails."""
    pass


class OpenAIAPIError(Exception):
    """Raised when OpenAI API calls fail."""
    pass
