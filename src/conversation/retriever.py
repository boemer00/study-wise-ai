"""
Context retrieval for the Conversational RAG system.

This module handles intelligent retrieval of relevant document context
based on user queries, conversation history, and semantic understanding.
"""

import asyncio
import time
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import logging
from dotenv import load_dotenv

load_dotenv()

# Legacy OpenAI SDK import removed; now using wrapper in studywise.llm

from .models import (
    DocumentSource,
    RetrievalResult,
    QuestionType,
    Message,
    MessageRole
)
from src.weaviate_client import WeaviateClient

# New helper wrappers (migration in progress)
from studywise.llm.openai_client import OpenAIClient, get_openai_client  # noqa: F401
from studywise.vector.weaviate_client import VectorClient  # noqa: F401

logger = logging.getLogger(__name__)


class ContextRetriever:
    """
    Intelligent context retrieval for conversational RAG.

    Handles query enhancement, semantic search, and context ranking
    to provide the most relevant document chunks for answering questions.
    """

    def __init__(
        self,
        weaviate_client: WeaviateClient,
        openai_api_key: str,
        *,
        openai_client: Optional[OpenAIClient] = None,
        vector_client: Optional[VectorClient] = None,
        max_chunks_per_query: int = 10,
        similarity_threshold: float = 0.7,
        rerank_enabled: bool = True
    ) -> None:
        """
        Initialize context retriever.

        Args:
            weaviate_client: Configured Weaviate client
            openai_api_key: OpenAI API key for embeddings
            openai_client: Optional OpenAI client
            vector_client: Optional Vector client
            max_chunks_per_query: Maximum chunks to retrieve per query
            similarity_threshold: Minimum similarity score for relevance
            rerank_enabled: Whether to use reranking for better results
        """
        # Prefer the new VectorClient wrapper when not explicitly provided.
        if weaviate_client is None and vector_client is None:
            from studywise.vector.weaviate_client import get_vector_client

            self.weaviate_client = get_vector_client()  # type: ignore[assignment]
        else:
            self.weaviate_client = weaviate_client if weaviate_client is not None else vector_client  # type: ignore[assignment]

        # Prefer the new OpenAIClient wrapper.
        if openai_client is None:
            self.openai_client = get_openai_client()  # type: ignore[assignment]
        else:
            self.openai_client = openai_client  # type: ignore[assignment]
        self.max_chunks_per_query = max_chunks_per_query
        self.similarity_threshold = similarity_threshold
        self.rerank_enabled = rerank_enabled

        # Question type patterns for classification
        self.question_patterns = {
            QuestionType.FACTUAL: [
                r'^what is\b', r'^what are\b', r'^define\b', r'^who is\b',
                r'^when was\b', r'^where is\b', r'^which\b'
            ],
            QuestionType.CONCEPTUAL: [
                r'^how does\b', r'^why does\b', r'^how do\b', r'^explain\b',
                r'^describe\b', r'^what happens when\b'
            ],
            QuestionType.APPLICATION: [
                r'^how to\b', r'^how can i\b', r'^what steps\b', r'^how do i\b',
                r'^can you show\b', r'^demonstrate\b'
            ],
            QuestionType.COMPARISON: [
                r'difference between\b', r'compare\b', r'versus\b', r'vs\b',
                r'what.*better\b', r'which.*best\b'
            ],
            QuestionType.EXPLANATION: [
                r'^why\b', r'reason\b', r'because\b', r'cause\b',
                r'what causes\b', r'what makes\b'
            ],
            QuestionType.SYNTHESIS: [
                r'relate\b', r'connection\b', r'relationship\b', r'combine\b',
                r'together\b', r'integrate\b'
            ]
        }

    async def retrieve_context(
        self,
        query: str,
        conversation_history: Optional[List[Message]] = None,
        user_documents: Optional[List[str]] = None,
        question_type: Optional[QuestionType] = None
    ) -> RetrievalResult:
        """
        Retrieve relevant context for answering a user query.

        Args:
            query: User's question or query
            conversation_history: Recent conversation messages
            user_documents: Specific documents to search within
            question_type: Type of question being asked

        Returns:
            RetrievalResult with ranked document chunks

        Raises:
            RetrievalError: If context retrieval fails
        """
        try:
            start_time = time.time()

            # Classify question type if not provided
            if question_type is None:
                question_type = await self.classify_question_type(query)

            # Enhance query with conversation context
            enhanced_query = await self.enhance_query(
                query,
                conversation_history,
                question_type
            )

            # Build document filters
            document_filters = {}
            if user_documents:
                document_filters['document_ids'] = user_documents

            # Search for relevant documents
            initial_results = await self.search_documents(
                enhanced_query,
                document_filters,
                limit=self.max_chunks_per_query * 2  # Get more for reranking
            )

            # Rerank results if enabled
            if self.rerank_enabled and len(initial_results) > self.max_chunks_per_query:
                conversation_context = self._build_conversation_context(conversation_history)
                reranked_results = await self.rerank_results(
                    query,
                    initial_results,
                    conversation_context
                )
                final_results = reranked_results[:self.max_chunks_per_query]
            else:
                final_results = initial_results[:self.max_chunks_per_query]

            # Get related chunks for better context
            if final_results:
                related_chunks = await self.get_related_chunks(final_results, max_related=3)
                # Merge and deduplicate
                all_chunks = final_results + related_chunks
                seen_chunk_ids = set()
                unique_chunks = []
                for chunk in all_chunks:
                    if chunk.chunk_id not in seen_chunk_ids:
                        unique_chunks.append(chunk)
                        seen_chunk_ids.add(chunk.chunk_id)
                final_results = unique_chunks[:self.max_chunks_per_query]

            search_time_ms = int((time.time() - start_time) * 1000)

            return RetrievalResult(
                query=query,
                chunks=final_results,
                total_results=len(initial_results),
                search_time_ms=search_time_ms,
                query_enhancement=enhanced_query if enhanced_query != query else None
            )

        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            raise RetrievalError(f"Failed to retrieve context: {str(e)}")

    async def enhance_query(
        self,
        original_query: str,
        conversation_history: Optional[List[Message]] = None,
        question_type: Optional[QuestionType] = None
    ) -> str:
        """
        Enhance user query with conversation context and intent understanding.

        Args:
            original_query: Original user query
            conversation_history: Recent conversation messages
            question_type: Detected question type

        Returns:
            Enhanced query string for better retrieval
        """
        try:
            enhanced_query = original_query.strip()

            # Extract key concepts from the query
            key_concepts = self._extract_key_concepts(enhanced_query)

            # Add context from conversation history
            if conversation_history:
                context_concepts = []
                recent_messages = conversation_history[-3:]  # Last 3 messages

                for message in recent_messages:
                    if message.role in [MessageRole.USER, MessageRole.ASSISTANT]:
                        message_concepts = self._extract_key_concepts(message.content)
                        context_concepts.extend(message_concepts[:2])  # Top 2 concepts per message

                # Add relevant context concepts that aren't already in the query
                query_lower = enhanced_query.lower()
                for concept in context_concepts[:3]:  # Max 3 additional concepts
                    if concept.lower() not in query_lower and len(concept) > 2:
                        enhanced_query += f" {concept}"

            # Add question type context
            if question_type:
                type_enhancement = {
                    QuestionType.FACTUAL: "definition explanation",
                    QuestionType.CONCEPTUAL: "how works mechanism process",
                    QuestionType.APPLICATION: "steps guide tutorial example",
                    QuestionType.COMPARISON: "differences similarities contrast",
                    QuestionType.EXPLANATION: "reasons why causes factors",
                    QuestionType.SYNTHESIS: "relationship connection integration"
                }.get(question_type, "")

                if type_enhancement:
                    enhanced_query += f" {type_enhancement}"

            logger.debug(f"Enhanced query: '{original_query}' -> '{enhanced_query}'")
            return enhanced_query

        except Exception as e:
            logger.warning(f"Query enhancement failed, using original: {str(e)}")
            return original_query

    async def classify_question_type(
        self,
        query: str,
        conversation_context: Optional[str] = None
    ) -> QuestionType:
        """
        Classify the type of question being asked.

        Args:
            query: User's question
            conversation_context: Recent conversation context

        Returns:
            Classified question type
        """
        try:
            query_lower = query.lower().strip()

            # Use pattern matching for fast classification
            for question_type, patterns in self.question_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, query_lower):
                        logger.debug(f"Classified question as {question_type.value}: {pattern}")
                        return question_type

            # Fallback: use LLM for complex questions
            try:
                prompt = f"""Classify this question into one of these types:
- factual: Questions asking for definitions, facts, or basic information
- conceptual: Questions about how things work or processes
- application: Questions about how to do something or practical steps
- comparison: Questions comparing different things
- explanation: Questions asking why something happens
- synthesis: Questions about relationships or connections

Question: "{query}"

Classification (one word only):"""

                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=10,
                    temperature=0.1
                )

                classification = response.choices[0].message.content.strip().lower()

                try:
                    return QuestionType.from_string(classification)
                except ValueError:
                    pass

            except Exception as e:
                logger.warning(f"LLM classification failed: {str(e)}")

            # Default fallback
            return QuestionType.FACTUAL

        except Exception as e:
            logger.warning(f"Question classification failed: {str(e)}")
            return QuestionType.FACTUAL

    async def search_documents(
        self,
        enhanced_query: str,
        document_filters: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> List[DocumentSource]:
        """
        Search documents using semantic similarity.

        Args:
            enhanced_query: Enhanced search query
            document_filters: Optional filters for document selection
            limit: Maximum number of results

        Returns:
            List of relevant document chunks

        Raises:
            SearchError: If document search fails
        """
        try:
            # Get query embedding
            query_embedding = await self._get_query_embedding(enhanced_query)

            # Prepare Weaviate query
            where_clause = {}
            if document_filters and 'document_ids' in document_filters:
                where_clause = {
                    "path": ["document_id"],
                    "operator": "ContainsAny",
                    "valueTextArray": document_filters['document_ids']
                }

            # Perform vector search using existing WeaviateClient
            search_results = await self.weaviate_client.search_similar_chunks(
                query_vector=query_embedding,
                limit=limit,
                where_clause=where_clause if where_clause else None,
                distance_threshold=1.0 - self.similarity_threshold  # Convert similarity to distance
            )

            # Convert to DocumentSource objects
            document_sources = []
            for result in search_results:
                try:
                    # Extract relevance score (convert distance back to similarity)
                    distance = result.get('_additional', {}).get('distance', 0.5)
                    relevance_score = max(0.0, 1.0 - distance)

                    # Skip results below threshold
                    if relevance_score < self.similarity_threshold:
                        continue

                    document_source = DocumentSource(
                        document_id=result.get('document_id', ''),
                        chunk_id=result.get('chunk_id', ''),
                        title=result.get('title', 'Unknown Document'),
                        content_snippet=result.get('content', '')[:500],  # Truncate snippet
                        relevance_score=relevance_score,
                        page_number=result.get('page_number'),
                        metadata=result.get('metadata', {})
                    )
                    document_sources.append(document_source)

                except Exception as e:
                    logger.warning(f"Error processing search result: {str(e)}")
                    continue

            logger.debug(f"Found {len(document_sources)} relevant chunks for query")
            return document_sources

        except Exception as e:
            logger.error(f"Document search failed: {str(e)}")
            raise SearchError(f"Failed to search documents: {str(e)}")

    async def rerank_results(
        self,
        query: str,
        initial_results: List[DocumentSource],
        conversation_context: Optional[str] = None
    ) -> List[DocumentSource]:
        """
        Rerank search results for better relevance.

        Args:
            query: Original user query
            initial_results: Initial search results
            conversation_context: Recent conversation context

        Returns:
            Reranked list of document sources
        """
        try:
            if len(initial_results) <= 1:
                return initial_results

            # Calculate context relevance scores
            reranked_results = []
            for chunk in initial_results:
                # Calculate enhanced relevance score
                base_score = chunk.relevance_score
                context_score = self._calculate_context_relevance(
                    chunk, query, conversation_context
                )

                # Weighted combination (70% original, 30% context)
                final_score = 0.7 * base_score + 0.3 * context_score

                # Create new DocumentSource with updated score
                reranked_chunk = DocumentSource(
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    title=chunk.title,
                    content_snippet=chunk.content_snippet,
                    relevance_score=final_score,
                    page_number=chunk.page_number,
                    metadata=chunk.metadata
                )
                reranked_results.append(reranked_chunk)

            # Sort by final relevance score
            reranked_results.sort(key=lambda x: x.relevance_score, reverse=True)

            logger.debug(f"Reranked {len(reranked_results)} results")
            return reranked_results

        except Exception as e:
            logger.warning(f"Reranking failed, using original order: {str(e)}")
            return initial_results

    async def get_related_chunks(
        self,
        primary_chunks: List[DocumentSource],
        max_related: int = 5
    ) -> List[DocumentSource]:
        """
        Get related chunks from the same documents as primary results.

        Args:
            primary_chunks: Primary relevant chunks
            max_related: Maximum related chunks to retrieve

        Returns:
            List of related document chunks
        """
        try:
            if not primary_chunks:
                return []

            related_chunks = []

            # Group chunks by document
            document_groups = {}
            for chunk in primary_chunks:
                doc_id = chunk.document_id
                if doc_id not in document_groups:
                    document_groups[doc_id] = []
                document_groups[doc_id].append(chunk)

            # For each document, find adjacent chunks
            for doc_id, chunks in document_groups.items():
                try:
                    # Get adjacent chunks using Weaviate metadata search
                    for chunk in chunks[:2]:  # Limit to top 2 chunks per document
                        # Search for chunks from same document with similar context
                        where_clause = {
                            "operator": "And",
                            "operands": [
                                {
                                    "path": ["document_id"],
                                    "operator": "Equal",
                                    "valueText": doc_id
                                },
                                {
                                    "path": ["chunk_id"],
                                    "operator": "NotEqual",
                                    "valueText": chunk.chunk_id
                                }
                            ]
                        }

                        # Get chunks from same document
                        nearby_results = await self.weaviate_client.search_similar_chunks(
                            query_text=chunk.content_snippet[:200],  # Use chunk content as query
                            limit=3,
                            where_clause=where_clause
                        )

                        for result in nearby_results[:2]:  # Max 2 per primary chunk
                            if len(related_chunks) >= max_related:
                                break

                            try:
                                related_chunk = DocumentSource(
                                    document_id=result.get('document_id', ''),
                                    chunk_id=result.get('chunk_id', ''),
                                    title=result.get('title', chunk.title),
                                    content_snippet=result.get('content', '')[:500],
                                    relevance_score=chunk.relevance_score * 0.8,  # Lower score for related
                                    page_number=result.get('page_number'),
                                    metadata=result.get('metadata', {})
                                )
                                related_chunks.append(related_chunk)

                            except Exception as e:
                                logger.warning(f"Error processing related chunk: {str(e)}")
                                continue

                        if len(related_chunks) >= max_related:
                            break

                except Exception as e:
                    logger.warning(f"Error finding related chunks for document {doc_id}: {str(e)}")
                    continue

            logger.debug(f"Found {len(related_chunks)} related chunks")
            return related_chunks

        except Exception as e:
            logger.warning(f"Failed to get related chunks: {str(e)}")
            return []

    def _calculate_context_relevance(
        self,
        chunk: DocumentSource,
        query: str,
        conversation_context: Optional[str] = None
    ) -> float:
        """
        Calculate relevance score considering conversation context.

        Args:
            chunk: Document chunk to score
            query: User query
            conversation_context: Recent conversation context

        Returns:
            Relevance score between 0 and 1
        """
        try:
            base_score = 0.5  # Default relevance

            # Query term overlap
            query_terms = set(query.lower().split())
            chunk_terms = set(chunk.content_snippet.lower().split())

            if query_terms:
                overlap_ratio = len(query_terms & chunk_terms) / len(query_terms)
                base_score += overlap_ratio * 0.3

            # Context term overlap
            if conversation_context:
                context_terms = set(conversation_context.lower().split())
                if context_terms:
                    context_overlap = len(context_terms & chunk_terms) / len(context_terms)
                    base_score += context_overlap * 0.2

            # Title relevance boost
            title_terms = set(chunk.title.lower().split())
            if query_terms & title_terms:
                base_score += 0.1

            return min(1.0, base_score)

        except Exception as e:
            logger.warning(f"Context relevance calculation failed: {str(e)}")
            return 0.5

    def _extract_key_concepts(
        self,
        text: str
    ) -> List[str]:
        """
        Extract key concepts from text for query enhancement.

        Args:
            text: Text to extract concepts from

        Returns:
            List of key concepts
        """
        try:
            # Simple concept extraction using common patterns
            text = text.lower()

            # Remove common stop words and short words
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                'should', 'can', 'may', 'might', 'this', 'that', 'these', 'those',
                'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
                'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their'
            }

            # Extract words and filter
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
            concepts = []

            for word in words:
                if word not in stop_words and len(word) > 2:
                    concepts.append(word)

            # Return most frequent concepts (simple frequency count)
            concept_freq = {}
            for concept in concepts:
                concept_freq[concept] = concept_freq.get(concept, 0) + 1

            # Sort by frequency and return top concepts
            sorted_concepts = sorted(concept_freq.items(), key=lambda x: x[1], reverse=True)
            return [concept for concept, _ in sorted_concepts[:5]]

        except Exception as e:
            logger.warning(f"Concept extraction failed: {str(e)}")
            return []

    def _build_conversation_context(
        self,
        conversation_history: Optional[List[Message]]
    ) -> Optional[str]:
        """
        Build context string from conversation history.

        Args:
            conversation_history: Recent conversation messages

        Returns:
            Context string or None
        """
        if not conversation_history:
            return None

        try:
            # Get last 3 messages for context
            recent_messages = conversation_history[-3:]
            context_parts = []

            for message in recent_messages:
                if message.role in [MessageRole.USER, MessageRole.ASSISTANT]:
                    # Take first 100 characters of each message
                    content_preview = message.content[:100]
                    context_parts.append(content_preview)

            return " ".join(context_parts) if context_parts else None

        except Exception as e:
            logger.warning(f"Failed to build conversation context: {str(e)}")
            return None

    async def _get_query_embedding(
        self,
        query: str
    ) -> List[float]:
        """Get embedding vector for a query."""
        try:
            # If using the wrapper, call `.embed`.
            if hasattr(self.openai_client, "embed"):
                return (await self.openai_client.embed([query]))[0]

            # Fallback to legacy SDK signature.
            response = await self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=query,
            )
            if not response.data:
                raise EmbeddingError("No embedding data returned")
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Failed to get query embedding: {str(e)}")
            raise EmbeddingError(f"Failed to get query embedding: {str(e)}")


class RetrievalError(Exception):
    """Raised when context retrieval fails."""
    pass


class SearchError(Exception):
    """Raised when document search fails."""
    pass


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    pass
