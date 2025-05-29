"""
Weaviate client for vector database operations.

This module provides a high-level interface for interacting with Weaviate,
including document storage, semantic search, and hybrid search capabilities.
"""

import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass
import weaviate
import weaviate.classes as wvc
from weaviate.classes.init import Auth, AdditionalConfig, Timeout


@dataclass
class DocumentEmbedding:
    """Data model for document embeddings stored in Weaviate."""
    id: str
    content: str
    title: str
    source: str
    tags: List[str]
    supabase_id: Optional[str]
    created_at: datetime


@dataclass
class SearchResult:
    """Data model for search results from Weaviate."""
    id: str
    content: str
    title: str
    score: float
    metadata: Dict[str, Any]


def create_weaviate_client(
    url: Optional[str] = None,
    api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    local: bool = False
) -> 'WeaviateClient':
    """
    Factory function to create WeaviateClient with proper configuration.

    Args:
        url: Weaviate Cloud URL or custom host
        api_key: Weaviate API key (for WCD)
        openai_api_key: OpenAI API key for embeddings
        local: Whether to connect to local Weaviate instance

    Returns:
        Configured WeaviateClient instance
    """
    # Use environment variables as fallback
    weaviate_url = url or os.getenv("WEAVIATE_URL")
    weaviate_api_key = api_key or os.getenv("WEAVIATE_API_KEY")
    openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")

    if not weaviate_url:
        raise ValueError("WEAVIATE_URL must be provided or set in environment variables")

    if not local and not weaviate_api_key:
        raise ValueError("WEAVIATE_API_KEY must be provided for cloud instances")

    return WeaviateClient(
        url=weaviate_url,
        api_key=weaviate_api_key,
        openai_api_key=openai_key
    )


class WeaviateClient:
    """
    High-level client for Weaviate vector database operations.

    Provides methods for document storage, semantic search, and hybrid search
    with automatic embedding generation using OpenAI's text-embedding-ada-002.
    """

    def __init__(self, url: str, api_key: Optional[str] = None, openai_api_key: Optional[str] = None):
        """
        Initialize Weaviate client.

        Args:
            url: Weaviate instance URL (for WCD) or host for local
            api_key: Weaviate API key (for WCD)
            openai_api_key: OpenAI API key for embeddings
        """
        self.url = url
        self.api_key = api_key
        self.openai_api_key = openai_api_key
        self.client = None
        self.logger = logging.getLogger(__name__)

        # Initialize connection
        self._connect()

    def _connect(self):
        """Establish connection to Weaviate."""
        try:
            headers = {}
            if self.openai_api_key:
                headers["X-OpenAI-Api-Key"] = self.openai_api_key

            if self.api_key:
                # Weaviate Cloud connection
                self.client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.url,
                    auth_credentials=Auth.api_key(self.api_key),
                    headers=headers,
                    additional_config=AdditionalConfig(
                        timeout=Timeout(init=30, query=60, insert=120)
                    )
                )
            else:
                # Local Weaviate connection
                self.client = weaviate.connect_to_local(
                    host=self.url,
                    headers=headers,
                    additional_config=AdditionalConfig(
                        timeout=Timeout(init=30, query=60, insert=120)
                    )
                )

            self.logger.info(f"Connected to Weaviate at {self.url}")

        except Exception as e:
            self.logger.error(f"Failed to connect to Weaviate: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure connection is closed."""
        self.close()

    def close(self):
        """Close the Weaviate client connection."""
        if self.client:
            self.client.close()
            self.logger.info("Weaviate client connection closed")

    def create_schema(self) -> bool:
        """
        Create the Document schema in Weaviate.

        Returns:
            True if schema created successfully, False otherwise
        """
        try:
            # Check if collection already exists
            if self.client.collections.exists("Document"):
                self.logger.info("Document collection already exists")
                return True

            # Create Document collection
            collection = self.client.collections.create(
                name="Document",
                vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-3-small"
                ),
                properties=[
                    wvc.config.Property(
                        name="title",
                        data_type=wvc.config.DataType.TEXT,
                        description="Document title"
                    ),
                    wvc.config.Property(
                        name="content",
                        data_type=wvc.config.DataType.TEXT,
                        description="Document content"
                    ),
                    wvc.config.Property(
                        name="source",
                        data_type=wvc.config.DataType.TEXT,
                        description="Document source (file path, URL, etc.)"
                    ),
                    wvc.config.Property(
                        name="tags",
                        data_type=wvc.config.DataType.TEXT_ARRAY,
                        description="Document tags"
                    ),
                    wvc.config.Property(
                        name="supabase_id",
                        data_type=wvc.config.DataType.TEXT,
                        description="Corresponding Supabase record ID"
                    ),
                    wvc.config.Property(
                        name="created_at",
                        data_type=wvc.config.DataType.DATE,
                        description="Document creation timestamp"
                    ),
                ]
            )

            self.logger.info("Document collection created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create schema: {e}")
            return False

    def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Add a document to Weaviate with automatic embedding generation.

        Args:
            content: Document text content
            metadata: Document metadata (title, source, tags, etc.)

        Returns:
            Document ID in Weaviate
        """
        try:
            collection = self.client.collections.get("Document")

            # Prepare document properties
            properties = {
                "title": metadata.get("title", ""),
                "content": content,
                "source": metadata.get("source", ""),
                "tags": metadata.get("tags", []),
                "supabase_id": metadata.get("supabase_id"),
                "created_at": metadata.get("created_at", datetime.now(timezone.utc))
            }

            # Add document to Weaviate
            result = collection.data.insert(properties)

            self.logger.info(f"Document added to Weaviate with ID: {result}")
            return str(result)

        except Exception as e:
            self.logger.error(f"Failed to add document: {e}")
            raise

    def semantic_search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Perform semantic search using vector similarity.

        Args:
            query: Search query text
            limit: Maximum number of results

        Returns:
            List of search results ordered by relevance
        """
        try:
            collection = self.client.collections.get("Document")

            # Perform vector similarity search
            response = collection.query.near_text(
                query=query,
                limit=limit,
                return_metadata=wvc.query.MetadataQuery(certainty=True, distance=True)
            )

            # Convert to SearchResult objects
            results = []
            for obj in response.objects:
                # Use certainty as primary score (0-1, higher = better)
                # Fall back to distance-based score if certainty not available
                if hasattr(obj.metadata, 'certainty') and obj.metadata.certainty is not None:
                    score = float(obj.metadata.certainty)
                elif hasattr(obj.metadata, 'distance') and obj.metadata.distance is not None:
                    # Convert distance to similarity score (distance is 0-2, lower = better)
                    score = max(0.0, 1.0 - (float(obj.metadata.distance) / 2.0))
                else:
                    score = 0.0

                result = SearchResult(
                    id=str(obj.uuid),
                    content=obj.properties.get("content", ""),
                    title=obj.properties.get("title", ""),
                    score=score,
                    metadata={
                        "source": obj.properties.get("source", ""),
                        "tags": obj.properties.get("tags", []),
                        "supabase_id": obj.properties.get("supabase_id"),
                        "created_at": obj.properties.get("created_at")
                    }
                )
                results.append(result)

            self.logger.info(f"Semantic search returned {len(results)} results")
            return results

        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            return []

    def hybrid_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining vector similarity and keyword matching.

        Args:
            query: Search query text
            filters: Optional filters (tags, source, date range, etc.)
            limit: Maximum number of results

        Returns:
            List of search results ordered by relevance
        """
        try:
            collection = self.client.collections.get("Document")

            # Build where filter if provided
            where_filter = None
            if filters:
                conditions = []

                if "tags" in filters:
                    conditions.append(
                        wvc.query.Filter.by_property("tags").contains_any(filters["tags"])
                    )

                if "source" in filters:
                    conditions.append(
                        wvc.query.Filter.by_property("source").equal(filters["source"])
                    )

                if "date_from" in filters:
                    conditions.append(
                        wvc.query.Filter.by_property("created_at").greater_or_equal(filters["date_from"])
                    )

                if "date_to" in filters:
                    conditions.append(
                        wvc.query.Filter.by_property("created_at").less_or_equal(filters["date_to"])
                    )

                # Combine conditions with AND
                if conditions:
                    where_filter = conditions[0]
                    for condition in conditions[1:]:
                        where_filter = where_filter & condition

            # Perform hybrid search
            response = collection.query.hybrid(
                query=query,
                limit=limit,
                where=where_filter,
                return_metadata=wvc.query.MetadataQuery(certainty=True, distance=True)
            )

            # Convert to SearchResult objects
            results = []
            for obj in response.objects:
                # Use certainty as primary score (0-1, higher = better)
                # Fall back to distance-based score if certainty not available
                if hasattr(obj.metadata, 'certainty') and obj.metadata.certainty is not None:
                    score = float(obj.metadata.certainty)
                elif hasattr(obj.metadata, 'distance') and obj.metadata.distance is not None:
                    # Convert distance to similarity score (distance is 0-2, lower = better)
                    score = max(0.0, 1.0 - (float(obj.metadata.distance) / 2.0))
                else:
                    score = 0.0

                result = SearchResult(
                    id=str(obj.uuid),
                    content=obj.properties.get("content", ""),
                    title=obj.properties.get("title", ""),
                    score=score,
                    metadata={
                        "source": obj.properties.get("source", ""),
                        "tags": obj.properties.get("tags", []),
                        "supabase_id": obj.properties.get("supabase_id"),
                        "created_at": obj.properties.get("created_at")
                    }
                )
                results.append(result)

            self.logger.info(f"Hybrid search returned {len(results)} results")
            return results

        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            return []

    def get_similar_documents(self, document_id: str, limit: int = 5) -> List[SearchResult]:
        """
        Find documents similar to a given document.

        Args:
            document_id: ID of the reference document
            limit: Maximum number of similar documents

        Returns:
            List of similar documents ordered by similarity
        """
        try:
            collection = self.client.collections.get("Document")

            # Perform similarity search using document ID
            response = collection.query.near_object(
                near_object=document_id,
                limit=limit + 1,  # +1 to exclude the original document
                return_metadata=wvc.query.MetadataQuery(certainty=True, distance=True)
            )

            # Convert to SearchResult objects, excluding the original document
            results = []
            for obj in response.objects:
                if str(obj.uuid) != document_id:  # Exclude the original document
                    # Use certainty as primary score (0-1, higher = better)
                    # Fall back to distance-based score if certainty not available
                    if hasattr(obj.metadata, 'certainty') and obj.metadata.certainty is not None:
                        score = float(obj.metadata.certainty)
                    elif hasattr(obj.metadata, 'distance') and obj.metadata.distance is not None:
                        # Convert distance to similarity score (distance is 0-2, lower = better)
                        score = max(0.0, 1.0 - (float(obj.metadata.distance) / 2.0))
                    else:
                        score = 0.0

                    result = SearchResult(
                        id=str(obj.uuid),
                        content=obj.properties.get("content", ""),
                        title=obj.properties.get("title", ""),
                        score=score,
                        metadata={
                            "source": obj.properties.get("source", ""),
                            "tags": obj.properties.get("tags", []),
                            "supabase_id": obj.properties.get("supabase_id"),
                            "created_at": obj.properties.get("created_at")
                        }
                    )
                    results.append(result)

                    if len(results) >= limit:
                        break

            self.logger.info(f"Found {len(results)} similar documents")
            return results

        except Exception as e:
            self.logger.error(f"Similar documents search failed: {e}")
            return []

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from Weaviate.

        Args:
            document_id: ID of document to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            collection = self.client.collections.get("Document")

            # Delete document by ID
            collection.data.delete_by_id(document_id)

            self.logger.info(f"Document {document_id} deleted successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    def get_document_count(self) -> int:
        """
        Get total number of documents in Weaviate.

        Returns:
            Total number of documents
        """
        try:
            collection = self.client.collections.get("Document")

            # Get aggregate count
            response = collection.aggregate.over_all(total_count=True)
            count = response.total_count or 0

            self.logger.info(f"Total documents in Weaviate: {count}")
            return count

        except Exception as e:
            self.logger.error(f"Failed to get document count: {e}")
            return 0

    def health_check(self) -> bool:
        """
        Check if Weaviate is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            is_ready = self.client.is_ready()
            self.logger.info(f"Weaviate health check: {'OK' if is_ready else 'FAILED'}")
            return is_ready

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks for better embedding quality.

        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Number of overlapping characters between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at word boundary
            if end < len(text):
                # Find the last space within the chunk
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = end - overlap
            if start >= len(text):
                break

        return chunks

    def _format_search_result(self, weaviate_result: Dict[str, Any]) -> SearchResult:
        """
        Convert Weaviate result to SearchResult object.

        Args:
            weaviate_result: Raw result from Weaviate

        Returns:
            Formatted SearchResult object
        """
        properties = weaviate_result.get("properties", {})
        additional = weaviate_result.get("_additional", {})

        return SearchResult(
            id=weaviate_result.get("id", ""),
            content=properties.get("content", ""),
            title=properties.get("title", ""),
            score=additional.get("score", 0.0),
            metadata={
                "source": properties.get("source", ""),
                "tags": properties.get("tags", []),
                "supabase_id": properties.get("supabase_id"),
                "created_at": properties.get("created_at")
            }
        )
