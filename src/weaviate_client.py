"""
Weaviate client for vector database operations.

This module provides a high-level interface for interacting with Weaviate,
including document storage, semantic search, and hybrid search capabilities.
"""

import os
import logging
import json
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

    # Ensure URL has proper protocol for cloud instances
    if not weaviate_url.startswith(('http://', 'https://')):
        if 'localhost' in weaviate_url or '127.0.0.1' in weaviate_url:
            weaviate_url = f"http://{weaviate_url}"
        else:
            weaviate_url = f"https://{weaviate_url}"

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
        Create the Document schema in Weaviate for storing document chunks.
        Updated to support the conversational RAG system requirements.

        Returns:
            True if schema created successfully, False otherwise
        """
        try:
            # Check if collection already exists
            if self.client.collections.exists("Document"):
                self.logger.info("Document collection already exists")
                return True

            # Create Document collection for document chunks
            collection = self.client.collections.create(
                name="Document",
                vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-3-small"  # Use available model
                ),
                properties=[
                    wvc.config.Property(
                        name="document_id",
                        data_type=wvc.config.DataType.TEXT,
                        description="ID of the parent document"
                    ),
                    wvc.config.Property(
                        name="chunk_id",
                        data_type=wvc.config.DataType.TEXT,
                        description="Unique ID for this chunk"
                    ),
                    wvc.config.Property(
                        name="title",
                        data_type=wvc.config.DataType.TEXT,
                        description="Document title"
                    ),
                    wvc.config.Property(
                        name="content",
                        data_type=wvc.config.DataType.TEXT,
                        description="Chunk content"
                    ),
                    wvc.config.Property(
                        name="page_number",
                        data_type=wvc.config.DataType.NUMBER,
                        description="Page number in the document"
                    ),
                    wvc.config.Property(
                        name="source",
                        data_type=wvc.config.DataType.TEXT,
                        description="Document source (file path, URL, etc.)"
                    ),
                    wvc.config.Property(
                        name="metadata",
                        data_type=wvc.config.DataType.TEXT,
                        description="Additional metadata as JSON string"
                    ),
                    wvc.config.Property(
                        name="created_at",
                        data_type=wvc.config.DataType.DATE,
                        description="Chunk creation timestamp"
                    ),
                ]
            )

            self.logger.info("Document collection created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create schema: {e}")
            return False

    async def search_similar_chunks(
        self,
        query_vector: Optional[List[float]] = None,
        query_text: Optional[str] = None,
        limit: int = 10,
        where_clause: Optional[Dict[str, Any]] = None,
        distance_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks using vector similarity.
        This method is specifically required by the conversational RAG system.

        Args:
            query_vector: Pre-computed query embedding vector
            query_text: Text query (will be embedded automatically)
            limit: Maximum number of results
            where_clause: Optional filter conditions
            distance_threshold: Maximum distance threshold for results

        Returns:
            List of chunk results with conversational RAG expected format
        """
        try:
            collection = self.client.collections.get("Document")

            # Build where filter if provided
            where_filter = None
            if where_clause:
                where_filter = self._build_where_filter(where_clause)

            # Perform search based on input type
            if query_vector:
                # Vector similarity search
                if where_filter:
                    response = collection.query.near_vector(
                        near_vector=query_vector,
                        limit=limit,
                        where=where_filter,
                        return_metadata=wvc.query.MetadataQuery(distance=True)
                    )
                else:
                    response = collection.query.near_vector(
                        near_vector=query_vector,
                        limit=limit,
                        return_metadata=wvc.query.MetadataQuery(distance=True)
                    )
            elif query_text:
                # Text-based semantic search
                if where_filter:
                    response = collection.query.near_text(
                        query=query_text,
                        limit=limit,
                        where=where_filter,
                        return_metadata=wvc.query.MetadataQuery(distance=True)
                    )
                else:
                    response = collection.query.near_text(
                        query=query_text,
                        limit=limit,
                        return_metadata=wvc.query.MetadataQuery(distance=True)
                    )
            else:
                raise ValueError("Either query_vector or query_text must be provided")

            # Convert to format expected by conversational RAG
            results = []
            for obj in response.objects:
                # Get distance and convert to similarity if needed
                distance = getattr(obj.metadata, 'distance', 0.5)

                # Skip results beyond threshold
                if distance > distance_threshold:
                    continue

                # Get metadata safely - handle None values
                metadata_raw = obj.properties.get('metadata')
                metadata = self._parse_metadata(metadata_raw) if metadata_raw else {}
                
                result = {
                    'document_id': obj.properties.get('document_id', ''),
                    'chunk_id': obj.properties.get('chunk_id', str(obj.uuid)),
                    'title': obj.properties.get('title', ''),
                    'content': obj.properties.get('content', ''),
                    'page_number': obj.properties.get('page_number'),
                    'metadata': metadata,
                    '_additional': {
                        'distance': float(distance),
                        'id': str(obj.uuid)
                    }
                }
                results.append(result)

            self.logger.debug(f"Found {len(results)} similar chunks")
            return results

        except Exception as e:
            self.logger.error(f"Chunk search failed: {e}")
            return []

    def _build_where_filter(self, where_clause: Dict[str, Any]) -> wvc.query.Filter:
        """
        Build Weaviate where filter from dictionary specification.

        Args:
            where_clause: Filter specification

        Returns:
            Weaviate Filter object
        """
        try:
            if "operator" in where_clause:
                operator = where_clause["operator"]

                if operator == "And":
                    operands = where_clause.get("operands", [])
                    if len(operands) >= 2:
                        filter_obj = self._build_where_filter(operands[0])
                        for operand in operands[1:]:
                            filter_obj = filter_obj & self._build_where_filter(operand)
                        return filter_obj

                elif operator == "Or":
                    operands = where_clause.get("operands", [])
                    if len(operands) >= 2:
                        filter_obj = self._build_where_filter(operands[0])
                        for operand in operands[1:]:
                            filter_obj = filter_obj | self._build_where_filter(operand)
                        return filter_obj

                elif operator == "Equal":
                    path = where_clause.get("path", [""])
                    value = where_clause.get("valueText", "")
                    return wvc.query.Filter.by_property(path[0]).equal(value)

                elif operator == "NotEqual":
                    path = where_clause.get("path", [""])
                    value = where_clause.get("valueText", "")
                    return ~wvc.query.Filter.by_property(path[0]).equal(value)

                elif operator == "ContainsAny":
                    path = where_clause.get("path", [""])
                    values = where_clause.get("valueTextArray", [])
                    return wvc.query.Filter.by_property(path[0]).contains_any(values)

            else:
                # Simple property filter
                path = where_clause.get("path", [""])
                operator = where_clause.get("operator", "Equal")

                if operator == "Equal":
                    value = where_clause.get("valueText", "")
                    return wvc.query.Filter.by_property(path[0]).equal(value)

            # Fallback - return a basic filter
            return wvc.query.Filter.by_property("document_id").exists()

        except Exception as e:
            self.logger.warning(f"Failed to build where filter: {e}")
            return wvc.query.Filter.by_property("document_id").exists()

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

    def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Add multiple documents to Weaviate with automatic embedding generation.

        Args:
            documents: List of document data with content and metadata

        Returns:
            Number of documents successfully added
        """
        try:
            collection = self.client.collections.get("Document")
            success_count = 0

            for doc in documents:
                try:
                    # Prepare document properties for Weaviate schema
                    properties = {
                        "document_id": doc.get("document_id", ""),
                        "chunk_id": doc.get("chunk_id", ""),
                        "title": doc.get("title", ""),
                        "content": doc.get("content", ""),
                        "page_number": doc.get("chunk_index", 0) + 1,  # Convert chunk_index to page_number
                        "source": doc.get("source", ""),
                        "metadata": json.dumps({
                            "document_id": doc.get("document_id"),
                            "chunk_index": doc.get("chunk_index", 0),
                            "start_position": doc.get("start_position", 0),
                            "end_position": doc.get("end_position", 0),
                            "tags": doc.get("tags", []),
                            **doc.get("metadata", {})
                        }),
                        "created_at": datetime.now(timezone.utc)
                    }

                    # Add document chunk to Weaviate
                    result = collection.data.insert(properties)
                    success_count += 1
                    self.logger.debug(f"Added document chunk {doc.get('chunk_id')} with ID: {result}")

                except Exception as e:
                    self.logger.error(f"Failed to add document chunk {doc.get('chunk_id', 'unknown')}: {e}")
                    continue

            self.logger.info(f"Successfully added {success_count}/{len(documents)} document chunks to Weaviate")
            return success_count

        except Exception as e:
            self.logger.error(f"Failed to add documents to Weaviate: {e}")
            return 0

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

    def _parse_metadata(self, metadata_str: str) -> Dict[str, Any]:
        """
        Parse metadata from a JSON string.

        Args:
            metadata_str: JSON string representation of metadata

        Returns:
            Parsed metadata as a dictionary
        """
        try:
            return json.loads(metadata_str)
        except Exception as e:
            self.logger.warning(f"Failed to parse metadata: {e}")
            return {}
