"""
Document processing module for Study-Wise AI.

This module provides the DocumentProcessor class that serves as the bridge between
Supabase (structured data) and Weaviate (vector embeddings), handling document
ingestion, processing, and synchronization across both systems.
"""

import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Literal, AsyncGenerator
from pathlib import Path
import uuid

from .supabase_client import get_supabase_client
from .weaviate_client import create_weaviate_client

# Configure logging
logger = logging.getLogger(__name__)


# Data Models
@dataclass
class DocumentInput:
    """Input data structure for document processing."""
    content: str
    metadata: Dict[str, Any]
    generate_flashcards: bool = True
    chunk_size: Optional[int] = None
    overlap_size: Optional[int] = None


@dataclass
class ProcessingResult:
    """Result of document processing operations."""
    document_id: str
    supabase_id: Optional[str] = None
    weaviate_id: Optional[str] = None
    flashcards_created: int = 0
    chunks_created: int = 0
    status: Literal['success', 'partial', 'failed'] = 'success'
    errors: List[str] = field(default_factory=list)
    processing_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchProcessingResult:
    """Result of batch document processing operations."""
    total_documents: int
    successful: int
    partial: int
    failed: int
    results: List[ProcessingResult]
    total_processing_time: float
    errors: List[str] = field(default_factory=list)


@dataclass
class DocumentStatus:
    """Status information for a processed document."""
    document_id: str
    title: str
    status: Literal['processing', 'completed', 'failed', 'partial']
    created_at: datetime
    updated_at: datetime
    supabase_synced: bool
    weaviate_synced: bool
    flashcards_count: int
    chunks_count: int
    error_message: Optional[str] = None


@dataclass
class DocumentChunk:
    """Represents a chunk of a larger document."""
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    start_position: int
    end_position: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProcessingError(Exception):
    """Custom exception for document processing errors."""

    def __init__(self, message: str, document_id: Optional[str] = None, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.document_id = document_id
        self.errors = errors or []


class DocumentProcessor:
    """
    Document processor that bridges Supabase and Weaviate for document management.

    This class handles the complete document processing pipeline:
    1. Document ingestion and validation
    2. Storage of metadata in Supabase
    3. Vector embedding creation in Weaviate
    4. Flashcard generation and storage
    5. Cross-system synchronization
    """

    def __init__(
        self,
        supabase_client=None,
        weaviate_client=None,
        flashcard_generator=None,
        default_chunk_size: int = 1000,
        default_overlap_size: int = 200
    ):
        """
        Initialize the DocumentProcessor.

        Args:
            supabase_client: Supabase client instance (defaults to get_supabase_client())
            weaviate_client: Weaviate client factory (defaults to create_weaviate_client)
            flashcard_generator: Flashcard generator instance (optional)
            default_chunk_size: Default size for document chunks
            default_overlap_size: Default overlap between chunks
        """
        self.supabase_client = supabase_client or get_supabase_client()
        self.weaviate_client_factory = weaviate_client or create_weaviate_client
        self.flashcard_generator = flashcard_generator
        self.default_chunk_size = default_chunk_size
        self.default_overlap_size = default_overlap_size

        # Processing statistics
        self.stats = {
            'documents_processed': 0,
            'documents_failed': 0,
            'total_chunks_created': 0,
            'total_flashcards_created': 0,
            'total_processing_time': 0.0
        }

        logger.info(f"DocumentProcessor initialized with chunk_size={default_chunk_size}, overlap={default_overlap_size}")

    # Core Processing Methods
    async def process_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        generate_flashcards: bool = True,
        chunk_document: bool = True
    ) -> ProcessingResult:
        """
        Process a single document through the complete pipeline.

        Args:
            content: The document content as text
            metadata: Document metadata (title, source, tags, etc.)
            generate_flashcards: Whether to generate flashcards from content
            chunk_document: Whether to split document into chunks for better embeddings

        Returns:
            ProcessingResult: Detailed results of the processing operation

        Raises:
            ProcessingError: If critical processing steps fail
        """
        start_time = datetime.now()
        document_id = self._generate_document_id()
        errors = []

        try:
            logger.info(f"Starting document processing for {document_id}")

            # Validate input
            await self.validate_document_input(content, metadata)

            # Prepare result object
            result = ProcessingResult(
                document_id=document_id,
                metadata=metadata.copy()
            )

            # Step 1: Store document metadata in Supabase
            try:
                supabase_id = await self._store_document_metadata(document_id, content, metadata)
                result.supabase_id = supabase_id
                logger.info(f"Document metadata stored in Supabase: {supabase_id}")
            except Exception as e:
                error_msg = f"Failed to store metadata in Supabase: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

            # Step 2: Create document chunks if requested
            chunks = []
            if chunk_document:
                try:
                    chunks = self.chunk_document(content)
                    result.chunks_created = len(chunks)
                    logger.info(f"Created {len(chunks)} chunks for document {document_id}")
                except Exception as e:
                    error_msg = f"Failed to chunk document: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    # Create a single chunk with the entire content
                    chunks = [DocumentChunk(
                        chunk_id=f"{document_id}_chunk_0",
                        document_id=document_id,
                        content=content,
                        chunk_index=0,
                        start_position=0,
                        end_position=len(content)
                    )]
                    result.chunks_created = 1
            else:
                # Single chunk with entire content
                chunks = [DocumentChunk(
                    chunk_id=f"{document_id}_chunk_0",
                    document_id=document_id,
                    content=content,
                    chunk_index=0,
                    start_position=0,
                    end_position=len(content)
                )]
                result.chunks_created = 1

            # Step 3: Create vector embeddings in Weaviate
            try:
                weaviate_id = await self._create_vector_embeddings(document_id, chunks, metadata)
                result.weaviate_id = weaviate_id
                logger.info(f"Vector embeddings created in Weaviate: {weaviate_id}")
            except Exception as e:
                error_msg = f"Failed to create vector embeddings: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

            # Step 4: Generate flashcards if requested
            if generate_flashcards:
                try:
                    flashcards = await self._generate_flashcards(document_id, content, metadata)
                    if flashcards:
                        # Sync flashcards to Supabase
                        await self.sync_flashcards_to_supabase(document_id, flashcards)
                        result.flashcards_created = len(flashcards)
                        logger.info(f"Generated and stored {len(flashcards)} flashcards")
                except Exception as e:
                    error_msg = f"Failed to generate flashcards: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # Determine final status
            if not errors:
                result.status = 'success'
                self.stats['documents_processed'] += 1
            elif result.supabase_id or result.weaviate_id:
                result.status = 'partial'
                self.stats['documents_processed'] += 1
            else:
                result.status = 'failed'
                self.stats['documents_failed'] += 1

            result.errors = errors

        except Exception as e:
            error_msg = f"Critical error during document processing: {str(e)}"
            logger.error(error_msg)
            result = ProcessingResult(
                document_id=document_id,
                status='failed',
                errors=[error_msg]
            )
            self.stats['documents_failed'] += 1
            raise ProcessingError(error_msg, document_id, [error_msg])

        finally:
            # Calculate processing time
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            result.processing_time = processing_time
            self.stats['total_processing_time'] += processing_time
            self.stats['total_chunks_created'] += result.chunks_created
            self.stats['total_flashcards_created'] += result.flashcards_created

            logger.info(f"Document processing completed for {document_id} in {processing_time:.2f}s, status: {result.status}")

        return result

    async def process_file(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        generate_flashcards: bool = True
    ) -> ProcessingResult:
        """
        Process a document from a file path.

        Args:
            file_path: Path to the document file
            metadata: Optional metadata (will be auto-detected if not provided)
            generate_flashcards: Whether to generate flashcards from content

        Returns:
            ProcessingResult: Detailed results of the processing operation

        Raises:
            ProcessingError: If file reading or processing fails
            FileNotFoundError: If the specified file doesn't exist
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Auto-generate metadata if not provided
            if metadata is None:
                metadata = {
                    'title': file_path.stem,
                    'source': str(file_path),
                    'file_name': file_path.name,
                    'file_size': file_path.stat().st_size,
                    'file_type': file_path.suffix.lower()
                }
            else:
                # Merge with auto-detected metadata
                auto_metadata = {
                    'source': str(file_path),
                    'file_name': file_path.name,
                    'file_size': file_path.stat().st_size,
                    'file_type': file_path.suffix.lower()
                }
                metadata = {**auto_metadata, **metadata}

            logger.info(f"Processing file: {file_path} ({len(content)} characters)")

            # Process the document content
            return await self.process_document(
                content=content,
                metadata=metadata,
                generate_flashcards=generate_flashcards
            )

        except UnicodeDecodeError as e:
            error_msg = f"Failed to decode file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise ProcessingError(error_msg, errors=[error_msg])
        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise ProcessingError(error_msg, errors=[error_msg])

    async def process_batch(
        self,
        documents: List[DocumentInput],
        max_concurrent: int = 5
    ) -> BatchProcessingResult:
        """
        Process multiple documents concurrently.

        Args:
            documents: List of DocumentInput objects to process
            max_concurrent: Maximum number of concurrent processing operations

        Returns:
            BatchProcessingResult: Aggregate results of batch processing
        """
        start_time = datetime.now()
        logger.info(f"Starting batch processing of {len(documents)} documents with concurrency {max_concurrent}")

        results = []
        errors = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single(doc_input: DocumentInput) -> ProcessingResult:
            async with semaphore:
                try:
                    return await self.process_document(
                        content=doc_input.content,
                        metadata=doc_input.metadata,
                        generate_flashcards=doc_input.generate_flashcards,
                        chunk_document=True
                    )
                except Exception as e:
                    error_msg = f"Failed to process document: {str(e)}"
                    errors.append(error_msg)
                    return ProcessingResult(
                        document_id=self._generate_document_id(),
                        status='failed',
                        errors=[error_msg]
                    )

        try:
            # Process all documents concurrently
            tasks = [process_single(doc) for doc in documents]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions that were returned
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = f"Document {i} failed with exception: {str(result)}"
                    errors.append(error_msg)
                    processed_results.append(ProcessingResult(
                        document_id=self._generate_document_id(),
                        status='failed',
                        errors=[error_msg]
                    ))
                else:
                    processed_results.append(result)

            results = processed_results

        except Exception as e:
            error_msg = f"Batch processing failed: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)

        # Calculate statistics
        successful = sum(1 for r in results if r.status == 'success')
        partial = sum(1 for r in results if r.status == 'partial')
        failed = sum(1 for r in results if r.status == 'failed')

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        batch_result = BatchProcessingResult(
            total_documents=len(documents),
            successful=successful,
            partial=partial,
            failed=failed,
            results=results,
            total_processing_time=total_time,
            errors=errors
        )

        logger.info(f"Batch processing completed: {successful} success, {partial} partial, {failed} failed in {total_time:.2f}s")

        return batch_result

    # Document Management Methods
    async def get_document_status(self, document_id: str) -> Optional[DocumentStatus]:
        """
        Get the current status of a processed document.

        Args:
            document_id: Unique identifier for the document

        Returns:
            DocumentStatus: Current status information, None if not found
        """
        try:
            # Query Supabase for document metadata
            result = self.supabase_client.table('documents').select('*').eq('document_id', document_id).execute()

            if not result.data:
                logger.warning(f"Document {document_id} not found in Supabase")
                return None

            doc_data = result.data[0]

            # Check if document exists in Weaviate
            weaviate_synced = False
            try:
                with self.weaviate_client_factory() as weaviate_client:
                    # Try to find document in Weaviate
                    weaviate_results = weaviate_client.semantic_search(
                        query="",  # Empty query to get documents
                        limit=1,
                        where_filter={"path": ["document_id"], "operator": "Equal", "valueText": document_id}
                    )
                    weaviate_synced = len(weaviate_results) > 0
            except Exception as e:
                logger.warning(f"Could not check Weaviate status for {document_id}: {e}")

            # Count flashcards for this document
            flashcards_count = 0
            try:
                flashcard_result = self.supabase_client.table('flashcards').select('id', count='exact').eq('document_id', document_id).execute()
                flashcards_count = flashcard_result.count if hasattr(flashcard_result, 'count') else len(flashcard_result.data)
            except Exception as e:
                logger.warning(f"Could not count flashcards for {document_id}: {e}")

            return DocumentStatus(
                document_id=document_id,
                title=doc_data.get('title', 'Unknown'),
                status=doc_data.get('status', 'unknown'),
                created_at=datetime.fromisoformat(doc_data['created_at']),
                updated_at=datetime.fromisoformat(doc_data['updated_at']),
                supabase_synced=True,  # Found in Supabase
                weaviate_synced=weaviate_synced,
                flashcards_count=flashcards_count,
                chunks_count=doc_data.get('chunks_count', 0),
                error_message=doc_data.get('error_message')
            )

        except Exception as e:
            logger.error(f"Failed to get document status for {document_id}: {e}")
            return None

    async def delete_document(
        self,
        document_id: str,
        cascade: bool = True,
        remove_from_weaviate: bool = True,
        remove_flashcards: bool = True
    ) -> bool:
        """
        Delete a document and optionally its related data.

        Args:
            document_id: Unique identifier for the document
            cascade: Whether to delete all related data
            remove_from_weaviate: Whether to remove from vector database
            remove_flashcards: Whether to remove generated flashcards

        Returns:
            bool: True if deletion was successful
        """
        success = True
        errors = []

        try:
            logger.info(f"Deleting document {document_id} (cascade={cascade})")

            # Delete from Weaviate if requested
            if remove_from_weaviate:
                try:
                    with self.weaviate_client_factory() as weaviate_client:
                        deleted = weaviate_client.delete_document(document_id)
                        if deleted:
                            logger.info(f"Document {document_id} deleted from Weaviate")
                        else:
                            logger.warning(f"Document {document_id} not found in Weaviate")
                except Exception as e:
                    error_msg = f"Failed to delete from Weaviate: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    success = False

            # Delete flashcards if requested
            if remove_flashcards and cascade:
                try:
                    result = self.supabase_client.table('flashcards').delete().eq('document_id', document_id).execute()
                    logger.info(f"Deleted flashcards for document {document_id}")
                except Exception as e:
                    error_msg = f"Failed to delete flashcards: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    success = False

            # Delete document metadata from Supabase
            try:
                result = self.supabase_client.table('documents').delete().eq('document_id', document_id).execute()
                logger.info(f"Document {document_id} deleted from Supabase")
            except Exception as e:
                error_msg = f"Failed to delete from Supabase: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
                success = False

            if success:
                logger.info(f"Document {document_id} successfully deleted")
            else:
                logger.error(f"Document deletion had errors: {errors}")

            return success

        except Exception as e:
            logger.error(f"Critical error during document deletion: {e}")
            return False

    async def reprocess_document(
        self,
        document_id: str,
        regenerate_embeddings: bool = True,
        regenerate_flashcards: bool = False
    ) -> ProcessingResult:
        """
        Reprocess an existing document with updated settings.

        Args:
            document_id: Unique identifier for the document
            regenerate_embeddings: Whether to regenerate vector embeddings
            regenerate_flashcards: Whether to regenerate flashcards

        Returns:
            ProcessingResult: Results of the reprocessing operation
        """
        try:
            logger.info(f"Reprocessing document {document_id}")

            # Get existing document data from Supabase
            result = self.supabase_client.table('documents').select('*').eq('document_id', document_id).execute()

            if not result.data:
                raise ProcessingError(f"Document {document_id} not found for reprocessing")

            doc_data = result.data[0]
            content = doc_data.get('content', '')
            metadata = {
                'title': doc_data.get('title'),
                'source': doc_data.get('source'),
                'tags': doc_data.get('tags', [])
            }

            # If regenerating embeddings, delete old ones first
            if regenerate_embeddings:
                try:
                    with self.weaviate_client_factory() as weaviate_client:
                        weaviate_client.delete_document(document_id)
                        logger.info(f"Deleted old embeddings for {document_id}")
                except Exception as e:
                    logger.warning(f"Could not delete old embeddings: {e}")

            # If regenerating flashcards, delete old ones first
            if regenerate_flashcards:
                try:
                    self.supabase_client.table('flashcards').delete().eq('document_id', document_id).execute()
                    logger.info(f"Deleted old flashcards for {document_id}")
                except Exception as e:
                    logger.warning(f"Could not delete old flashcards: {e}")

            # Reprocess the document with the same ID
            original_generate_id = self._generate_document_id
            self._generate_document_id = lambda: document_id  # Override to use same ID

            try:
                result = await self.process_document(
                    content=content,
                    metadata=metadata,
                    generate_flashcards=regenerate_flashcards,
                    chunk_document=regenerate_embeddings
                )

                # Update the document status in Supabase
                self.supabase_client.table('documents').update({
                    'status': result.status,
                    'updated_at': datetime.now().isoformat(),
                    'chunks_count': result.chunks_created,
                    'error_message': '; '.join(result.errors) if result.errors else None
                }).eq('document_id', document_id).execute()

                logger.info(f"Document {document_id} reprocessed successfully")
                return result

            finally:
                # Restore original ID generator
                self._generate_document_id = original_generate_id

        except Exception as e:
            error_msg = f"Failed to reprocess document {document_id}: {e}"
            logger.error(error_msg)
            raise ProcessingError(error_msg, document_id, [error_msg])

    # Synchronization Methods
    async def sync_document_to_weaviate(self, document_id: str) -> bool:
        """
        Synchronize document data from Supabase to Weaviate.

        Args:
            document_id: Unique identifier for the document

        Returns:
            bool: True if synchronization was successful
        """
        try:
            logger.info(f"Synchronizing document {document_id} to Weaviate")

            # Get document data from Supabase
            result = self.supabase_client.table('documents').select('*').eq('document_id', document_id).execute()

            if not result.data:
                logger.error(f"Document {document_id} not found in Supabase")
                return False

            doc_data = result.data[0]
            content = doc_data.get('content', '')
            metadata = {
                'title': doc_data.get('title'),
                'source': doc_data.get('source'),
                'tags': doc_data.get('tags', []),
                'document_id': document_id
            }

            # Create chunks for the document
            chunks = self.chunk_document(content)

            # Create vector embeddings in Weaviate
            weaviate_id = await self._create_vector_embeddings(document_id, chunks, metadata)

            if weaviate_id:
                # Update Supabase with Weaviate sync status
                self.supabase_client.table('documents').update({
                    'weaviate_id': weaviate_id,
                    'weaviate_synced': True,
                    'updated_at': datetime.now().isoformat()
                }).eq('document_id', document_id).execute()

                logger.info(f"Document {document_id} successfully synchronized to Weaviate")
                return True
            else:
                logger.error(f"Failed to create embeddings for document {document_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to sync document {document_id} to Weaviate: {e}")
            return False

    async def sync_flashcards_to_supabase(
        self,
        document_id: str,
        flashcards: List[Dict[str, Any]]
    ) -> bool:
        """
        Synchronize generated flashcards to Supabase.

        Args:
            document_id: Source document identifier
            flashcards: List of flashcard data to store

        Returns:
            bool: True if synchronization was successful
        """
        try:
            logger.info(f"Synchronizing {len(flashcards)} flashcards to Supabase for document {document_id}")

            # Prepare flashcard data for insertion
            flashcard_records = []
            for i, flashcard in enumerate(flashcards):
                record = {
                    'document_id': document_id,
                    'question': flashcard.get('question', ''),
                    'answer': flashcard.get('answer', ''),
                    'difficulty': flashcard.get('difficulty', 'medium'),
                    'tags': flashcard.get('tags', []),
                    'metadata': flashcard.get('metadata', {}),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                flashcard_records.append(record)

            # Insert flashcards into Supabase
            if flashcard_records:
                result = self.supabase_client.table('flashcards').insert(flashcard_records).execute()

                if result.data:
                    logger.info(f"Successfully inserted {len(result.data)} flashcards for document {document_id}")
                    return True
                else:
                    logger.error(f"Failed to insert flashcards for document {document_id}")
                    return False
            else:
                logger.warning(f"No flashcards to sync for document {document_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to sync flashcards to Supabase: {e}")
            return False

    async def sync_all_documents(self) -> Dict[str, int]:
        """
        Synchronize all documents between Supabase and Weaviate.

        Returns:
            Dict[str, int]: Statistics about synchronization results
        """
        stats = {
            'total_documents': 0,
            'supabase_to_weaviate_synced': 0,
            'weaviate_to_supabase_synced': 0,
            'sync_failures': 0,
            'up_to_date': 0
        }

        try:
            logger.info("Starting full synchronization between Supabase and Weaviate")

            # Get all documents from Supabase
            supabase_result = self.supabase_client.table('documents').select('document_id, weaviate_synced, title').execute()
            supabase_docs = {doc['document_id']: doc for doc in supabase_result.data}
            stats['total_documents'] = len(supabase_docs)

            # Get all documents from Weaviate
            weaviate_docs = set()
            try:
                with self.weaviate_client_factory() as weaviate_client:
                    # Get all document IDs from Weaviate
                    weaviate_results = weaviate_client.semantic_search(
                        query="",  # Empty query to get all documents
                        limit=1000,  # Adjust as needed
                        properties=["document_id"]
                    )
                    weaviate_docs = {doc.get('document_id') for doc in weaviate_results if doc.get('document_id')}
            except Exception as e:
                logger.error(f"Failed to get documents from Weaviate: {e}")

            # Sync documents that exist in Supabase but not in Weaviate
            for doc_id, doc_data in supabase_docs.items():
                if doc_id not in weaviate_docs:
                    try:
                        success = await self.sync_document_to_weaviate(doc_id)
                        if success:
                            stats['supabase_to_weaviate_synced'] += 1
                        else:
                            stats['sync_failures'] += 1
                    except Exception as e:
                        logger.error(f"Failed to sync document {doc_id} to Weaviate: {e}")
                        stats['sync_failures'] += 1
                else:
                    stats['up_to_date'] += 1

            # Note: Documents that exist in Weaviate but not in Supabase would need
            # more complex handling as we don't have the original content in Weaviate
            # This could be implemented as a separate cleanup operation

            logger.info(f"Synchronization completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed during full synchronization: {e}")
            return stats

    # Document Chunking Methods
    def chunk_document(
        self,
        content: str,
        chunk_size: Optional[int] = None,
        overlap_size: Optional[int] = None,
        preserve_paragraphs: bool = True
    ) -> List[DocumentChunk]:
        """
        Split a document into smaller chunks for better embedding quality.

        Args:
            content: The document content to chunk
            chunk_size: Maximum size of each chunk (defaults to instance default)
            overlap_size: Overlap between chunks (defaults to instance default)
            preserve_paragraphs: Whether to avoid splitting paragraphs

        Returns:
            List[DocumentChunk]: List of document chunks
        """
        if not content or not content.strip():
            return []

        chunk_size = chunk_size or self.default_chunk_size
        overlap_size = overlap_size or self.default_overlap_size

        # If content is smaller than chunk size, return as single chunk
        if len(content) <= chunk_size:
            return [DocumentChunk(
                chunk_id=f"{uuid.uuid4()}_chunk_0",
                document_id="",  # Will be set by caller
                content=content.strip(),
                chunk_index=0,
                start_position=0,
                end_position=len(content)
            )]

        chunks = []
        chunk_index = 0
        start_pos = 0

        while start_pos < len(content):
            # Calculate end position for this chunk
            end_pos = min(start_pos + chunk_size, len(content))

            # If preserving paragraphs, try to end at paragraph boundary
            if preserve_paragraphs and end_pos < len(content):
                # Look for paragraph breaks near the end
                search_start = max(start_pos + chunk_size // 2, end_pos - 200)
                search_end = min(end_pos + 200, len(content))

                # Find the best break point (paragraph > sentence > word)
                best_break = end_pos

                # Look for paragraph breaks (double newlines)
                for i in range(search_end - 1, search_start - 1, -1):
                    if content[i:i+2] == '\n\n':
                        best_break = i
                        break

                # If no paragraph break found, look for sentence endings
                if best_break == end_pos:
                    for i in range(search_end - 1, search_start - 1, -1):
                        if content[i] in '.!?' and i + 1 < len(content) and content[i + 1].isspace():
                            best_break = i + 1
                            break

                # If no sentence break found, look for word boundaries
                if best_break == end_pos:
                    for i in range(search_end - 1, search_start - 1, -1):
                        if content[i].isspace():
                            best_break = i
                            break

                end_pos = best_break

            # Extract chunk content
            chunk_content = content[start_pos:end_pos].strip()

            if chunk_content:  # Only add non-empty chunks
                chunk = DocumentChunk(
                    chunk_id=f"{uuid.uuid4()}_chunk_{chunk_index}",
                    document_id="",  # Will be set by caller
                    content=chunk_content,
                    chunk_index=chunk_index,
                    start_position=start_pos,
                    end_position=end_pos
                )
                chunks.append(chunk)
                chunk_index += 1

            # Calculate next start position with overlap
            if end_pos >= len(content):
                break

            # Move start position, considering overlap
            next_start = end_pos - overlap_size

            # Ensure we make progress (don't get stuck)
            if next_start <= start_pos:
                next_start = start_pos + max(1, chunk_size // 2)

            start_pos = next_start

        logger.info(f"Document chunked into {len(chunks)} pieces (size: {chunk_size}, overlap: {overlap_size})")
        return chunks

    # Utility Methods
    async def validate_document_input(self, content: str, metadata: Dict[str, Any]) -> bool:
        """
        Validate document input before processing.

        Args:
            content: Document content to validate
            metadata: Document metadata to validate

        Returns:
            bool: True if input is valid

        Raises:
            ProcessingError: If validation fails with details
        """
        errors = []

        # Validate content
        if not content or not isinstance(content, str):
            errors.append("Content must be a non-empty string")
        elif len(content.strip()) == 0:
            errors.append("Content cannot be empty or only whitespace")
        elif len(content) > 10_000_000:  # 10MB limit
            errors.append("Content exceeds maximum size limit (10MB)")

        # Validate metadata
        if not metadata or not isinstance(metadata, dict):
            errors.append("Metadata must be a non-empty dictionary")
        else:
            # Check required fields
            required_fields = ['title']
            for field in required_fields:
                if field not in metadata or not metadata[field]:
                    errors.append(f"Required metadata field '{field}' is missing or empty")

            # Validate specific fields
            if 'title' in metadata and len(str(metadata['title'])) > 500:
                errors.append("Title cannot exceed 500 characters")

            if 'tags' in metadata and not isinstance(metadata['tags'], (list, tuple)):
                errors.append("Tags must be a list or tuple")

        if errors:
            error_msg = f"Document validation failed: {'; '.join(errors)}"
            logger.error(error_msg)
            raise ProcessingError(error_msg, errors=errors)

        logger.debug("Document input validation passed")
        return True

    async def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get overall processing statistics.

        Returns:
            Dict[str, Any]: Statistics about processed documents
        """
        try:
            # Get counts from Supabase
            docs_result = self.supabase_client.table('documents').select('id', count='exact').execute()
            flashcards_result = self.supabase_client.table('flashcards').select('id', count='exact').execute()

            docs_count = docs_result.count if hasattr(docs_result, 'count') else len(docs_result.data)
            flashcards_count = flashcards_result.count if hasattr(flashcards_result, 'count') else len(flashcards_result.data)

            # Get Weaviate statistics
            weaviate_count = 0
            try:
                with self.weaviate_client_factory() as weaviate_client:
                    # Count documents in Weaviate
                    weaviate_results = weaviate_client.semantic_search(
                        query="",
                        limit=1000,  # Adjust as needed
                        properties=["document_id"]
                    )
                    weaviate_count = len(weaviate_results)
            except Exception as e:
                logger.warning(f"Could not get Weaviate statistics: {e}")

            statistics = {
                'total_documents_in_supabase': docs_count,
                'total_flashcards': flashcards_count,
                'total_documents_in_weaviate': weaviate_count,
                'session_stats': self.stats.copy(),
                'average_processing_time': (
                    self.stats['total_processing_time'] / max(1, self.stats['documents_processed'])
                    if self.stats['documents_processed'] > 0 else 0
                ),
                'success_rate': (
                    self.stats['documents_processed'] /
                    max(1, self.stats['documents_processed'] + self.stats['documents_failed'])
                    if (self.stats['documents_processed'] + self.stats['documents_failed']) > 0 else 1
                )
            }

            return statistics

        except Exception as e:
            logger.error(f"Failed to get processing statistics: {e}")
            return {
                'error': str(e),
                'session_stats': self.stats.copy()
            }

    def _generate_document_id(self) -> str:
        """
        Generate a unique document identifier.

        Returns:
            str: Unique document ID
        """
        # Use UUID4 for uniqueness with timestamp prefix for readability
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"doc_{timestamp}_{unique_id}"

    async def _store_document_metadata(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Store document metadata in Supabase.

        Args:
            document_id: Unique document identifier
            content: Document content
            metadata: Document metadata

        Returns:
            str: Supabase record ID
        """
        try:
            # Prepare document record for Supabase
            now = datetime.now().isoformat()
            document_record = {
                'document_id': document_id,
                'title': metadata.get('title', 'Untitled'),
                'content': content,
                'source': metadata.get('source', ''),
                'tags': metadata.get('tags', []),
                'file_name': metadata.get('file_name'),
                'file_size': metadata.get('file_size'),
                'file_type': metadata.get('file_type'),
                'status': 'processing',
                'created_at': now,
                'updated_at': now,
                'weaviate_synced': False,
                'chunks_count': 0,
                'metadata': metadata
            }

            # Insert into Supabase
            result = self.supabase_client.table('documents').insert(document_record).execute()

            if result.data:
                supabase_id = result.data[0]['id']
                logger.info(f"Document metadata stored in Supabase with ID: {supabase_id}")
                return str(supabase_id)
            else:
                raise Exception("No data returned from Supabase insert")

        except Exception as e:
            logger.error(f"Failed to store document metadata: {e}")
            raise

    async def _create_vector_embeddings(
        self,
        document_id: str,
        chunks: List[DocumentChunk],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Create vector embeddings in Weaviate.

        Args:
            document_id: Source document identifier
            chunks: Document chunks to embed
            metadata: Document metadata

        Returns:
            str: Weaviate document ID
        """
        try:
            # Update chunk document IDs
            for chunk in chunks:
                chunk.document_id = document_id

            with self.weaviate_client_factory() as weaviate_client:
                # Prepare documents for Weaviate
                weaviate_docs = []
                for chunk in chunks:
                    doc = {
                        'content': chunk.content,
                        'title': metadata.get('title', 'Untitled'),
                        'source': metadata.get('source', ''),
                        'tags': metadata.get('tags', []),
                        'document_id': document_id,
                        'chunk_id': chunk.chunk_id,
                        'chunk_index': chunk.chunk_index,
                        'start_position': chunk.start_position,
                        'end_position': chunk.end_position,
                        'metadata': metadata
                    }
                    weaviate_docs.append(doc)

                # Add documents to Weaviate
                success_count = weaviate_client.add_documents(weaviate_docs)

                if success_count > 0:
                    logger.info(f"Added {success_count}/{len(chunks)} chunks to Weaviate for document {document_id}")
                    return document_id  # Use document_id as Weaviate identifier
                else:
                    raise Exception("Failed to add any chunks to Weaviate")

        except Exception as e:
            logger.error(f"Failed to create vector embeddings: {e}")
            raise

    async def _generate_flashcards(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate flashcards from document content.

        Args:
            document_id: Source document identifier
            content: Document content
            metadata: Document metadata

        Returns:
            List[Dict[str, Any]]: Generated flashcard data
        """
        try:
            if not self.flashcard_generator:
                logger.warning("No flashcard generator configured, returning empty list")
                return []

            # Use the flashcard generator if available
            flashcards = await self.flashcard_generator.generate_flashcards(
                content=content,
                metadata=metadata
            )

            # Ensure each flashcard has required fields
            processed_flashcards = []
            for i, flashcard in enumerate(flashcards):
                processed_card = {
                    'question': flashcard.get('question', f'Question {i+1}'),
                    'answer': flashcard.get('answer', 'No answer provided'),
                    'difficulty': flashcard.get('difficulty', 'medium'),
                    'tags': flashcard.get('tags', metadata.get('tags', [])),
                    'metadata': {
                        'document_id': document_id,
                        'generated_at': datetime.now().isoformat(),
                        'source_title': metadata.get('title', 'Unknown'),
                        **flashcard.get('metadata', {})
                    }
                }
                processed_flashcards.append(processed_card)

            logger.info(f"Generated {len(processed_flashcards)} flashcards for document {document_id}")
            return processed_flashcards

        except Exception as e:
            logger.error(f"Failed to generate flashcards: {e}")
            # Return empty list instead of raising to allow partial success
            return []

    async def __aenter__(self):
        """Async context manager entry."""
        logger.info("DocumentProcessor context manager entered")
        # Initialize any resources if needed
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        try:
            if exc_type is not None:
                logger.error(f"DocumentProcessor context exiting with exception: {exc_type.__name__}: {exc_val}")
            else:
                logger.info("DocumentProcessor context manager exiting normally")

            # Log final statistics
            stats = await self.get_processing_statistics()
            logger.info(f"Final processing statistics: {stats}")

            # Close any resources if needed
            # Note: Weaviate clients are context-managed individually
            # Supabase client doesn't need explicit closing

        except Exception as e:
            logger.error(f"Error during context manager exit: {e}")

        # Don't suppress exceptions
        return False
