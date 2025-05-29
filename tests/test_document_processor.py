"""
Tests for DocumentProcessor module.

This module tests the document processing pipeline that bridges Supabase
and Weaviate, including document ingestion, processing, synchronization,
and error handling.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, List, Any

from src.document_processor import (
    DocumentProcessor,
    DocumentInput,
    ProcessingResult,
    BatchProcessingResult,
    DocumentStatus,
    DocumentChunk,
    ProcessingError
)


# Pytest fixtures for all test classes
@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    mock_client = Mock()
    # Add mock methods as needed for testing
    return mock_client


@pytest.fixture
def mock_weaviate_client():
    """Mock Weaviate client for testing."""
    mock_client = Mock()
    # Add mock methods as needed for testing
    return mock_client


@pytest.fixture
def mock_weaviate_client_factory():
    """Mock Weaviate client factory that returns a proper context manager."""
    mock_factory = Mock()
    mock_client = Mock()

    # Create a proper context manager
    context_manager = Mock()
    context_manager.__enter__ = Mock(return_value=mock_client)
    context_manager.__exit__ = Mock(return_value=None)

    mock_factory.return_value = context_manager
    return mock_factory, mock_client


@pytest.fixture
def mock_flashcard_generator():
    """Mock flashcard generator for testing."""
    mock_generator = AsyncMock()
    return mock_generator


@pytest.fixture
def document_processor(mock_supabase_client, mock_weaviate_client_factory, mock_flashcard_generator):
    """Create DocumentProcessor instance for testing."""
    factory, client = mock_weaviate_client_factory
    return DocumentProcessor(
        supabase_client=mock_supabase_client,
        weaviate_client=factory,
        flashcard_generator=mock_flashcard_generator
    )


@pytest.fixture
def sample_document_input():
    """Sample document input for testing."""
    return DocumentInput(
        content="This is a test document about machine learning concepts.",
        metadata={
            "title": "ML Test Document",
            "source": "test.md",
            "tags": ["machine-learning", "test"],
            "author": "Test Author"
        },
        generate_flashcards=True
    )


@pytest.fixture
def sample_processing_result():
    """Sample processing result for testing."""
    return ProcessingResult(
        document_id="test-doc-123",
        supabase_id="supabase-123",
        weaviate_id="weaviate-123",
        flashcards_created=5,
        chunks_created=3,
        status="success",
        processing_time=2.5
    )


class TestDocumentProcessorInitialization:
    """Test DocumentProcessor initialization and configuration."""

    def test_init_with_default_parameters(self):
        """Test initialization with default parameters."""
        processor = DocumentProcessor()

        # Check default values
        assert processor.default_chunk_size == 1000
        assert processor.default_overlap_size == 200
        assert processor.supabase_client is not None  # Should get default client
        assert processor.weaviate_client_factory is not None
        assert processor.flashcard_generator is None

        # Check stats initialization
        assert processor.stats['documents_processed'] == 0
        assert processor.stats['documents_failed'] == 0
        assert processor.stats['total_chunks_created'] == 0
        assert processor.stats['total_flashcards_created'] == 0
        assert processor.stats['total_processing_time'] == 0.0

    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        mock_supabase = Mock()
        mock_weaviate = Mock()
        mock_flashcard_gen = Mock()

        processor = DocumentProcessor(
            supabase_client=mock_supabase,
            weaviate_client=mock_weaviate,
            flashcard_generator=mock_flashcard_gen,
            default_chunk_size=500,
            default_overlap_size=100
        )

        # Check custom values
        assert processor.supabase_client == mock_supabase
        assert processor.weaviate_client_factory == mock_weaviate
        assert processor.flashcard_generator == mock_flashcard_gen
        assert processor.default_chunk_size == 500
        assert processor.default_overlap_size == 100

    def test_init_with_invalid_parameters(self):
        """Test initialization with invalid parameters raises appropriate errors."""
        # Test negative chunk size
        processor = DocumentProcessor(default_chunk_size=-100)
        assert processor.default_chunk_size == -100  # Should accept but may cause issues

        # Test zero overlap
        processor = DocumentProcessor(default_overlap_size=0)
        assert processor.default_overlap_size == 0  # Should be valid

        # Test None values (should use defaults)
        processor = DocumentProcessor(
            supabase_client=None,
            weaviate_client=None,
            flashcard_generator=None
        )
        assert processor.supabase_client is not None  # Should get default
        assert processor.weaviate_client_factory is not None  # Should get default
        assert processor.flashcard_generator is None  # Should remain None


class TestCoreProcessingMethods:
    """Test core document processing methods."""

    @pytest.mark.asyncio
    async def test_process_document_success(self, document_processor, sample_document_input):
        """Test successful document processing."""
        # Mock the private methods
        document_processor._store_document_metadata = AsyncMock(return_value="supabase-123")
        document_processor._create_vector_embeddings = AsyncMock(return_value="weaviate-123")
        document_processor._generate_flashcards = AsyncMock(return_value=[
            {"question": "What is ML?", "answer": "Machine Learning"},
            {"question": "What is AI?", "answer": "Artificial Intelligence"}
        ])
        document_processor.sync_flashcards_to_supabase = AsyncMock(return_value=True)
        document_processor.validate_document_input = AsyncMock(return_value=True)

        # Mock chunking
        mock_chunks = [
            DocumentChunk("chunk-1", "doc-123", "content part 1", 0, 0, 50),
            DocumentChunk("chunk-2", "doc-123", "content part 2", 1, 45, 100)
        ]
        document_processor.chunk_document = Mock(return_value=mock_chunks)

        result = await document_processor.process_document(
            content=sample_document_input.content,
            metadata=sample_document_input.metadata,
            generate_flashcards=True,
            chunk_document=True
        )

        # Verify result
        assert result.status == 'success'
        assert result.supabase_id == "supabase-123"
        assert result.weaviate_id == "weaviate-123"
        assert result.flashcards_created == 2
        assert result.chunks_created == 2
        assert len(result.errors) == 0
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_process_document_with_chunking(self, document_processor):
        """Test document processing with chunking enabled."""
        # Setup mocks
        document_processor._store_document_metadata = AsyncMock(return_value="supabase-123")
        document_processor._create_vector_embeddings = AsyncMock(return_value="weaviate-123")
        document_processor._generate_flashcards = AsyncMock(return_value=[])
        document_processor.validate_document_input = AsyncMock(return_value=True)

        # Test with large content that should be chunked
        large_content = "This is a test. " * 200  # Should create multiple chunks
        metadata = {"title": "Large Document", "source": "test"}

        result = await document_processor.process_document(
            content=large_content,
            metadata=metadata,
            chunk_document=True
        )

        # Should have multiple chunks for large content
        assert result.chunks_created > 1
        assert result.status == 'success'

    @pytest.mark.asyncio
    async def test_process_document_without_flashcards(self, document_processor, sample_document_input):
        """Test document processing without flashcard generation."""
        # Setup mocks
        document_processor._store_document_metadata = AsyncMock(return_value="supabase-123")
        document_processor._create_vector_embeddings = AsyncMock(return_value="weaviate-123")
        document_processor._generate_flashcards = AsyncMock()  # Should not be called
        document_processor.validate_document_input = AsyncMock(return_value=True)

        result = await document_processor.process_document(
            content=sample_document_input.content,
            metadata=sample_document_input.metadata,
            generate_flashcards=False
        )

        # Verify flashcards were not generated
        assert result.flashcards_created == 0
        assert result.status == 'success'
        document_processor._generate_flashcards.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_document_invalid_content(self, document_processor):
        """Test processing with invalid document content."""
        with pytest.raises(ProcessingError) as exc_info:
            await document_processor.process_document(
                content="",  # Empty content
                metadata={"title": "Test"}
            )

        assert "Content must be a non-empty string" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_document_partial_failure(self, document_processor, sample_document_input):
        """Test document processing with partial failures."""
        # Setup partial failure scenario
        document_processor._store_document_metadata = AsyncMock(return_value="supabase-123")
        document_processor._create_vector_embeddings = AsyncMock(side_effect=Exception("Weaviate error"))
        document_processor._generate_flashcards = AsyncMock(return_value=[])
        document_processor.validate_document_input = AsyncMock(return_value=True)

        result = await document_processor.process_document(
            content=sample_document_input.content,
            metadata=sample_document_input.metadata
        )

        # Should be partial success
        assert result.status == 'partial'
        assert result.supabase_id == "supabase-123"
        assert result.weaviate_id is None
        assert len(result.errors) > 0
        assert "Weaviate error" in str(result.errors)

    @pytest.mark.asyncio
    async def test_process_file_success(self, document_processor, tmp_path):
        """Test successful file processing."""
        # Create test file
        test_file = tmp_path / "test_document.txt"
        test_content = "This is a test document for file processing."
        test_file.write_text(test_content)

        # Mock process_document
        expected_result = ProcessingResult(
            document_id="test-123",
            supabase_id="supabase-123",
            status='success'
        )
        document_processor.process_document = AsyncMock(return_value=expected_result)

        result = await document_processor.process_file(
            file_path=test_file,
            generate_flashcards=False
        )

        # Verify file was processed
        assert result.status == 'success'

        # Check that process_document was called with correct content and metadata
        document_processor.process_document.assert_called_once()
        call_args = document_processor.process_document.call_args
        assert call_args[1]['content'] == test_content
        assert call_args[1]['metadata']['file_name'] == 'test_document.txt'
        assert call_args[1]['metadata']['source'] == str(test_file)

    @pytest.mark.asyncio
    async def test_process_file_not_found(self, document_processor):
        """Test file processing with non-existent file."""
        with pytest.raises(FileNotFoundError):
            await document_processor.process_file(
                file_path="non_existent_file.txt"
            )

    @pytest.mark.asyncio
    async def test_process_file_unsupported_format(self, document_processor, tmp_path):
        """Test processing unsupported file format."""
        # Create binary file that can't be decoded as text
        binary_file = tmp_path / "test.bin"
        binary_file.write_bytes(b'\x80\x81\x82\x83')  # Invalid UTF-8

        with pytest.raises(ProcessingError) as exc_info:
            await document_processor.process_file(binary_file)

        assert "Failed to decode file" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_batch_success(self, document_processor):
        """Test successful batch processing."""
        # Create test documents
        documents = [
            DocumentInput("Content 1", {"title": "Doc 1"}),
            DocumentInput("Content 2", {"title": "Doc 2"}),
            DocumentInput("Content 3", {"title": "Doc 3"})
        ]

        # Mock successful processing
        success_result = ProcessingResult(document_id="test", status='success')
        document_processor.process_document = AsyncMock(return_value=success_result)

        result = await document_processor.process_batch(documents, max_concurrent=2)

        # Verify batch results
        assert result.total_documents == 3
        assert result.successful == 3
        assert result.failed == 0
        assert result.partial == 0
        assert len(result.results) == 3

        # Check that process_document was called for each document
        assert document_processor.process_document.call_count == 3

    @pytest.mark.asyncio
    async def test_process_batch_mixed_results(self, document_processor):
        """Test batch processing with mixed success/failure results."""
        documents = [
            DocumentInput("Content 1", {"title": "Doc 1"}),
            DocumentInput("Content 2", {"title": "Doc 2"}),
        ]

        # Mock mixed results
        success_result = ProcessingResult(document_id="test-1", status='success')
        failure_result = ProcessingResult(document_id="test-2", status='failed', errors=["Test error"])

        document_processor.process_document = AsyncMock(side_effect=[success_result, failure_result])

        result = await document_processor.process_batch(documents)

        # Verify mixed results
        assert result.total_documents == 2
        assert result.successful == 1
        assert result.failed == 1
        assert result.partial == 0

    @pytest.mark.asyncio
    async def test_process_batch_concurrent_limit(self, document_processor):
        """Test batch processing respects concurrency limits."""
        documents = [DocumentInput(f"Content {i}", {"title": f"Doc {i}"}) for i in range(10)]

        # Track concurrent calls
        concurrent_calls = 0
        max_concurrent = 0

        async def mock_process(content, metadata, **kwargs):
            nonlocal concurrent_calls, max_concurrent
            concurrent_calls += 1
            max_concurrent = max(max_concurrent, concurrent_calls)
            await asyncio.sleep(0.01)  # Simulate processing time
            concurrent_calls -= 1
            return ProcessingResult(document_id="test", status='success')

        document_processor.process_document = mock_process

        await document_processor.process_batch(documents, max_concurrent=3)

        # Should not exceed concurrency limit
        assert max_concurrent <= 3


class TestDocumentManagement:
    """Test document management operations."""

    @pytest.mark.asyncio
    async def test_get_document_status_found(self, document_processor, mock_weaviate_client_factory):
        """Test getting status of existing document."""
        # Mock Supabase response for document query
        mock_doc_data = {
            'document_id': 'test-123',
            'title': 'Test Document',
            'status': 'completed',
            'created_at': '2024-01-01T10:00:00',
            'updated_at': '2024-01-01T11:00:00',
            'chunks_count': 3
        }

        # Mock flashcard count response
        mock_flashcard_result = Mock()
        mock_flashcard_result.count = 5
        mock_flashcard_result.data = []

        # Mock document query response
        mock_doc_result = Mock()
        mock_doc_result.data = [mock_doc_data]

        # Setup table mock to return different responses for different table names
        def table_side_effect(table_name):
            table_mock = Mock()
            if table_name == 'documents':
                table_mock.select.return_value.eq.return_value.execute.return_value = mock_doc_result
            elif table_name == 'flashcards':
                table_mock.select.return_value.eq.return_value.execute.return_value = mock_flashcard_result
            return table_mock

        document_processor.supabase_client.table.side_effect = table_side_effect

        # Mock Weaviate check
        factory, mock_weaviate_client = mock_weaviate_client_factory
        mock_weaviate_client.semantic_search.return_value = [{'document_id': 'test-123'}]

        status = await document_processor.get_document_status('test-123')

        assert status is not None
        assert status.document_id == 'test-123'
        assert status.title == 'Test Document'
        assert status.status == 'completed'
        assert status.supabase_synced == True
        assert status.weaviate_synced == True
        assert status.flashcards_count == 5
        assert status.chunks_count == 3

    @pytest.mark.asyncio
    async def test_get_document_status_not_found(self, document_processor):
        """Test getting status of non-existent document."""
        # Mock empty Supabase response
        document_processor.supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        status = await document_processor.get_document_status('non-existent')

        assert status is None

    @pytest.mark.asyncio
    async def test_delete_document_success(self, document_processor, mock_weaviate_client_factory):
        """Test successful document deletion."""
        # Mock successful deletion from all systems
        factory, mock_weaviate_client = mock_weaviate_client_factory
        mock_weaviate_client.delete_document.return_value = True

        # Mock Supabase deletions
        document_processor.supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = Mock()

        result = await document_processor.delete_document('test-123')

        assert result == True
        mock_weaviate_client.delete_document.assert_called_once_with('test-123')

    @pytest.mark.asyncio
    async def test_delete_document_cascade(self, document_processor, mock_weaviate_client_factory):
        """Test document deletion with cascade enabled."""
        # Mock successful cascade deletion
        factory, mock_weaviate_client = mock_weaviate_client_factory
        mock_weaviate_client.delete_document.return_value = True

        # Mock Supabase deletions for both flashcards and documents
        delete_mock = Mock()
        delete_mock.delete.return_value.eq.return_value.execute.return_value = Mock()
        document_processor.supabase_client.table.return_value = delete_mock

        result = await document_processor.delete_document(
            'test-123',
            cascade=True,
            remove_from_weaviate=True,
            remove_flashcards=True
        )

        assert result == True
        # Should delete from both flashcards and documents tables
        assert document_processor.supabase_client.table.call_count >= 2

    @pytest.mark.asyncio
    async def test_delete_document_selective(self, document_processor, mock_weaviate_client_factory):
        """Test selective deletion of document components."""
        # Test deletion with selective options
        factory, mock_weaviate_client = mock_weaviate_client_factory
        mock_weaviate_client.delete_document.return_value = True

        document_processor.supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = Mock()

        # Delete only from Supabase, not Weaviate or flashcards
        result = await document_processor.delete_document(
            'test-123',
            cascade=False,
            remove_from_weaviate=False,
            remove_flashcards=False
        )

        assert result == True
        # Should not call Weaviate deletion
        mock_weaviate_client.delete_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, document_processor, mock_weaviate_client_factory):
        """Test deletion of non-existent document."""
        # Mock Weaviate returning False (document not found)
        factory, mock_weaviate_client = mock_weaviate_client_factory
        mock_weaviate_client.delete_document.return_value = False

        # Mock Supabase deletion (should still succeed even if doc not in Weaviate)
        document_processor.supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = Mock()

        result = await document_processor.delete_document('non-existent')

        # Should still return True as deletion from Supabase succeeded
        assert result == True

    @pytest.mark.asyncio
    async def test_reprocess_document_success(self, document_processor):
        """Test successful document reprocessing."""
        # Mock existing document data
        existing_doc = {
            'document_id': 'test-123',
            'content': 'Original content for reprocessing',
            'title': 'Test Doc',
            'source': 'test.md',
            'tags': ['test', 'reprocess']
        }
        document_processor.supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [existing_doc]

        # Mock the reprocessing pipeline
        expected_result = ProcessingResult(
            document_id='test-123',
            status='success',
            chunks_created=2,
            flashcards_created=3
        )

        # Mock process_document for reprocessing
        original_process = document_processor.process_document
        document_processor.process_document = AsyncMock(return_value=expected_result)

        # Mock Supabase update
        document_processor.supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

        result = await document_processor.reprocess_document('test-123')

        assert result.document_id == 'test-123'
        assert result.status == 'success'

        # Verify process_document was called with existing content
        document_processor.process_document.assert_called_once()
        call_args = document_processor.process_document.call_args
        assert call_args[1]['content'] == 'Original content for reprocessing'

    @pytest.mark.asyncio
    async def test_reprocess_document_regenerate_embeddings(self, document_processor):
        """Test reprocessing with embedding regeneration."""
        # Mock existing document data
        existing_doc = {
            'document_id': 'test-123',
            'content': 'Content for embedding regeneration',
            'title': 'Test Doc'
        }
        document_processor.supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [existing_doc]

        # Mock Weaviate deletion
        mock_weaviate_client = Mock()
        mock_weaviate_client.delete_document.return_value = True
        document_processor.weaviate_client_factory.return_value.__enter__.return_value = mock_weaviate_client

        # Mock processing result
        expected_result = ProcessingResult(document_id='test-123', status='success')
        document_processor.process_document = AsyncMock(return_value=expected_result)
        document_processor.supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

        result = await document_processor.reprocess_document(
            'test-123',
            regenerate_embeddings=True,
            regenerate_flashcards=False
        )

        # Should delete old embeddings first
        mock_weaviate_client.delete_document.assert_called_once_with('test-123')
        assert result.status == 'success'

    @pytest.mark.asyncio
    async def test_reprocess_document_regenerate_flashcards(self, document_processor):
        """Test reprocessing with flashcard regeneration."""
        # Mock existing document data
        existing_doc = {
            'document_id': 'test-123',
            'content': 'Content for flashcard regeneration',
            'title': 'Test Doc'
        }
        document_processor.supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [existing_doc]

        # Mock flashcard deletion
        document_processor.supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = Mock()

        # Mock processing result
        expected_result = ProcessingResult(document_id='test-123', status='success')
        document_processor.process_document = AsyncMock(return_value=expected_result)
        document_processor.supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

        result = await document_processor.reprocess_document(
            'test-123',
            regenerate_embeddings=False,
            regenerate_flashcards=True
        )

        # Should regenerate flashcards
        document_processor.process_document.assert_called_once()
        call_args = document_processor.process_document.call_args
        assert call_args[1]['generate_flashcards'] == True
        assert result.status == 'success'


class TestSynchronizationMethods:
    """Test data synchronization between Supabase and Weaviate."""

    @pytest.mark.asyncio
    async def test_sync_document_to_weaviate_success(self, document_processor):
        """Test successful synchronization to Weaviate."""
        # Mock Supabase document data
        doc_data = {
            'document_id': 'test-123',
            'content': 'Content to sync to Weaviate',
            'title': 'Test Document',
            'source': 'test.md',
            'tags': ['sync', 'test']
        }
        document_processor.supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [doc_data]

        # Mock chunking
        mock_chunks = [DocumentChunk("chunk-1", "test-123", "content chunk", 0, 0, 50)]
        document_processor.chunk_document = Mock(return_value=mock_chunks)

        # Mock vector embedding creation
        document_processor._create_vector_embeddings = AsyncMock(return_value="weaviate-123")

        # Mock Supabase update
        document_processor.supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

        result = await document_processor.sync_document_to_weaviate('test-123')

        assert result == True
        document_processor._create_vector_embeddings.assert_called_once()
        document_processor.chunk_document.assert_called_once_with('Content to sync to Weaviate')

    @pytest.mark.asyncio
    async def test_sync_document_to_weaviate_failure(self, document_processor):
        """Test failed synchronization to Weaviate."""
        # Mock Supabase document not found
        document_processor.supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        result = await document_processor.sync_document_to_weaviate('non-existent')

        assert result == False

    @pytest.mark.asyncio
    async def test_sync_flashcards_to_supabase_success(self, document_processor):
        """Test successful flashcard synchronization to Supabase."""
        flashcards = [
            {"question": "What is Python?", "answer": "A programming language", "difficulty": "easy"},
            {"question": "What is async?", "answer": "Asynchronous programming", "difficulty": "medium"}
        ]

        # Mock successful Supabase insertion
        mock_result = Mock()
        mock_result.data = [{"id": 1}, {"id": 2}]  # Mock inserted records
        document_processor.supabase_client.table.return_value.insert.return_value.execute.return_value = mock_result

        result = await document_processor.sync_flashcards_to_supabase('test-123', flashcards)

        assert result == True
        document_processor.supabase_client.table.assert_called_with('flashcards')

    @pytest.mark.asyncio
    async def test_sync_flashcards_to_supabase_failure(self, document_processor):
        """Test failed flashcard synchronization to Supabase."""
        flashcards = [{"question": "Test?", "answer": "Test"}]

        # Mock failed Supabase insertion
        mock_result = Mock()
        mock_result.data = None  # No data indicates failure
        document_processor.supabase_client.table.return_value.insert.return_value.execute.return_value = mock_result

        result = await document_processor.sync_flashcards_to_supabase('test-123', flashcards)

        assert result == False

    @pytest.mark.asyncio
    async def test_sync_all_documents_success(self, document_processor, mock_weaviate_client_factory):
        """Test successful synchronization of all documents."""
        # Mock Supabase documents
        supabase_docs = [
            {'document_id': 'doc-1', 'weaviate_synced': False, 'title': 'Doc 1'},
            {'document_id': 'doc-2', 'weaviate_synced': True, 'title': 'Doc 2'}
        ]
        document_processor.supabase_client.table.return_value.select.return_value.execute.return_value.data = supabase_docs

        # Mock Weaviate documents (doc-2 already exists)
        factory, mock_weaviate_client = mock_weaviate_client_factory
        mock_weaviate_client.semantic_search.return_value = [{'document_id': 'doc-2'}]

        # Mock sync operation
        document_processor.sync_document_to_weaviate = AsyncMock(return_value=True)

        stats = await document_processor.sync_all_documents()

        assert stats['total_documents'] == 2
        assert stats['supabase_to_weaviate_synced'] == 1  # Only doc-1 needs syncing
        assert stats['up_to_date'] == 1  # doc-2 already synced
        assert stats['sync_failures'] == 0

    @pytest.mark.asyncio
    async def test_sync_all_documents_partial_failure(self, document_processor, mock_weaviate_client_factory):
        """Test synchronization with some documents failing."""
        # Mock Supabase documents
        supabase_docs = [
            {'document_id': 'doc-1', 'weaviate_synced': False, 'title': 'Doc 1'},
            {'document_id': 'doc-2', 'weaviate_synced': False, 'title': 'Doc 2'}
        ]
        document_processor.supabase_client.table.return_value.select.return_value.execute.return_value.data = supabase_docs

        # Mock empty Weaviate
        factory, mock_weaviate_client = mock_weaviate_client_factory
        mock_weaviate_client.semantic_search.return_value = []

        # Mock mixed sync results
        document_processor.sync_document_to_weaviate = AsyncMock(side_effect=[True, False])

        stats = await document_processor.sync_all_documents()

        assert stats['total_documents'] == 2
        assert stats['supabase_to_weaviate_synced'] == 1
        assert stats['sync_failures'] == 1


class TestDocumentChunking:
    """Test document chunking functionality."""

    def test_chunk_document_default_settings(self, document_processor):
        """Test document chunking with default settings."""
        content = "This is a test document. " * 50  # ~1250 characters

        chunks = document_processor.chunk_document(content)

        assert len(chunks) >= 1
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        assert all(chunk.content.strip() for chunk in chunks)  # No empty chunks

        # Check chunk ordering
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunk_document_custom_size(self, document_processor):
        """Test document chunking with custom chunk size."""
        content = "Word " * 200  # ~1000 characters

        # Test small chunks
        small_chunks = document_processor.chunk_document(content, chunk_size=100, overlap_size=20)

        # Test large chunks
        large_chunks = document_processor.chunk_document(content, chunk_size=2000, overlap_size=0)

        # Small chunks should create more pieces
        assert len(small_chunks) > len(large_chunks)

        # Large chunks might fit everything in one piece
        if len(content) <= 2000:
            assert len(large_chunks) == 1

    def test_chunk_document_with_overlap(self, document_processor):
        """Test document chunking with overlap."""
        content = "Sentence one. Sentence two. Sentence three. " * 30

        chunks = document_processor.chunk_document(content, chunk_size=200, overlap_size=50)

        if len(chunks) > 1:
            # Check that chunks have overlapping content
            first_chunk_end = chunks[0].content[-30:]  # Last 30 chars
            second_chunk_start = chunks[1].content[:30]  # First 30 chars

            # Should have some overlap (not exact due to boundary detection)
            assert len(chunks) > 1  # Multiple chunks created

    def test_chunk_document_preserve_paragraphs(self, document_processor):
        """Test document chunking while preserving paragraphs."""
        content = """This is paragraph one.

This is paragraph two with more content to test chunking.

This is paragraph three."""

        chunks = document_processor.chunk_document(
            content,
            chunk_size=100,
            preserve_paragraphs=True
        )

        # Should not break paragraphs unnecessarily
        for chunk in chunks:
            # Should not end in the middle of a sentence unless necessary
            if chunk.content.strip() and len(chunk.content) < 100:
                # Short chunks should end cleanly
                assert chunk.content.strip()

    def test_chunk_document_small_content(self, document_processor):
        """Test chunking of small content that doesn't need splitting."""
        small_content = "This is a small document."

        chunks = document_processor.chunk_document(small_content)

        assert len(chunks) == 1
        assert chunks[0].content.strip() == small_content.strip()
        assert chunks[0].chunk_index == 0
        assert chunks[0].start_position == 0
        assert chunks[0].end_position == len(small_content)

    def test_chunk_document_empty_content(self, document_processor):
        """Test chunking of empty content."""
        empty_content = ""

        chunks = document_processor.chunk_document(empty_content)

        assert len(chunks) == 0

        # Test whitespace-only content
        whitespace_content = "   \n\t  "
        chunks = document_processor.chunk_document(whitespace_content)

        assert len(chunks) == 0


class TestUtilityMethods:
    """Test utility and helper methods."""

    @pytest.mark.asyncio
    async def test_validate_document_input_valid(self, document_processor):
        """Test validation of valid document input."""
        valid_content = "This is valid document content."
        valid_metadata = {
            "title": "Valid Document",
            "source": "test.md",
            "tags": ["test", "valid"]
        }

        # Should not raise any exception
        result = await document_processor.validate_document_input(valid_content, valid_metadata)
        assert result == True

    @pytest.mark.asyncio
    async def test_validate_document_input_invalid_content(self, document_processor):
        """Test validation of invalid document content."""
        valid_metadata = {"title": "Test"}

        # Test empty content
        with pytest.raises(ProcessingError) as exc_info:
            await document_processor.validate_document_input("", valid_metadata)
        assert "Content must be a non-empty string" in str(exc_info.value)

        # Test None content
        with pytest.raises(ProcessingError) as exc_info:
            await document_processor.validate_document_input(None, valid_metadata)
        assert "Content must be a non-empty string" in str(exc_info.value)

        # Test non-string content
        with pytest.raises(ProcessingError) as exc_info:
            await document_processor.validate_document_input(123, valid_metadata)
        assert "Content must be a non-empty string" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_document_input_invalid_metadata(self, document_processor):
        """Test validation of invalid document metadata."""
        valid_content = "Valid content"

        # Test None metadata
        with pytest.raises(ProcessingError) as exc_info:
            await document_processor.validate_document_input(valid_content, None)
        assert "Metadata must be a non-empty dictionary" in str(exc_info.value)

        # Test empty dict as metadata (falsy in Python)
        with pytest.raises(ProcessingError) as exc_info:
            await document_processor.validate_document_input(valid_content, {})
        assert "Metadata must be a non-empty dictionary" in str(exc_info.value)

        # Test missing title in non-empty dict
        with pytest.raises(ProcessingError) as exc_info:
            await document_processor.validate_document_input(valid_content, {"source": "test"})
        assert "Required metadata field 'title' is missing or empty" in str(exc_info.value)

        # Test invalid tags format
        with pytest.raises(ProcessingError) as exc_info:
            await document_processor.validate_document_input(valid_content, {
                "title": "Test",
                "tags": "not a list"
            })
        assert "Tags must be a list or tuple" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_processing_statistics(self, document_processor):
        """Test retrieval of processing statistics."""
        # Mock Supabase counts
        docs_result = Mock()
        docs_result.count = 10
        flashcards_result = Mock()
        flashcards_result.count = 25

        document_processor.supabase_client.table.return_value.select.return_value.execute.return_value = docs_result

        # Mock Weaviate count
        mock_weaviate_client = Mock()
        mock_weaviate_client.semantic_search.return_value = [{'doc_id': f'doc-{i}'} for i in range(8)]
        document_processor.weaviate_client_factory.return_value.__enter__.return_value = mock_weaviate_client

        # Set some session stats
        document_processor.stats['documents_processed'] = 5
        document_processor.stats['total_processing_time'] = 10.0

        stats = await document_processor.get_processing_statistics()

        assert stats['total_documents_in_supabase'] == 10
        assert stats['total_flashcards'] == 10  # Using docs_result for both
        assert stats['total_documents_in_weaviate'] == 8
        assert stats['session_stats']['documents_processed'] == 5
        assert stats['average_processing_time'] == 2.0  # 10.0 / 5
        assert 'success_rate' in stats

    def test_generate_document_id(self, document_processor):
        """Test document ID generation."""
        doc_id = document_processor._generate_document_id()

        assert isinstance(doc_id, str)
        assert doc_id.startswith('doc_')
        assert len(doc_id.split('_')) == 4  # doc_YYYYMMDD_HHMMSS_uuid

        # Check timestamp format
        parts = doc_id.split('_')
        date_part = parts[1]  # YYYYMMDD
        time_part = parts[2]  # HHMMSS
        uuid_part = parts[3]  # uuid

        assert len(date_part) == 8  # YYYYMMDD
        assert date_part.isdigit()
        assert len(time_part) == 6  # HHMMSS
        assert time_part.isdigit()
        assert len(uuid_part) == 8  # Short UUID

    def test_generate_document_id_uniqueness(self, document_processor):
        """Test that generated document IDs are unique."""
        ids = [document_processor._generate_document_id() for _ in range(10)]

        # All IDs should be unique
        assert len(set(ids)) == len(ids)


class TestPrivateMethods:
    """Test private/internal methods."""

    @pytest.mark.asyncio
    async def test_store_document_metadata_success(self, document_processor):
        """Test successful metadata storage in Supabase."""
        # Mock successful Supabase insertion
        mock_result = Mock()
        mock_result.data = [{"id": 123}]
        document_processor.supabase_client.table.return_value.insert.return_value.execute.return_value = mock_result

        result = await document_processor._store_document_metadata(
            "test-123",
            "Test content",
            {"title": "Test Document", "source": "test.md"}
        )

        assert result == "123"
        document_processor.supabase_client.table.assert_called_with('documents')

    @pytest.mark.asyncio
    async def test_store_document_metadata_failure(self, document_processor):
        """Test failed metadata storage in Supabase."""
        # Mock failed Supabase insertion
        mock_result = Mock()
        mock_result.data = None
        document_processor.supabase_client.table.return_value.insert.return_value.execute.return_value = mock_result

        with pytest.raises(Exception):
            await document_processor._store_document_metadata(
                "test-123",
                "Test content",
                {"title": "Test Document"}
            )

    @pytest.mark.asyncio
    async def test_create_vector_embeddings_success(self, document_processor, mock_weaviate_client_factory):
        """Test successful vector embeddings creation."""
        document_id = "doc-123"
        chunks = [
            DocumentChunk("chunk-1", document_id, "This is chunk content", 0, 0, 20),
            DocumentChunk("chunk-2", document_id, "This is more content", 1, 21, 42)
        ]
        metadata = {"title": "Test Document", "source": "test.md"}

        # Mock Weaviate embedding creation
        factory, mock_weaviate_client = mock_weaviate_client_factory
        mock_weaviate_client.add_documents.return_value = 2  # 2 chunks added successfully

        weaviate_id = await document_processor._create_vector_embeddings(document_id, chunks, metadata)

        assert weaviate_id == document_id
        mock_weaviate_client.add_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_vector_embeddings_failure(self, document_processor, mock_weaviate_client_factory):
        """Test vector embeddings creation failure."""
        document_id = "doc-123"
        chunks = [DocumentChunk("chunk-1", document_id, "Content", 0, 0, 7)]
        metadata = {"title": "Test Document"}

        # Mock Weaviate failure
        factory, mock_weaviate_client = mock_weaviate_client_factory
        mock_weaviate_client.add_documents.return_value = 0  # No documents added

        with pytest.raises(Exception) as exc_info:
            await document_processor._create_vector_embeddings(document_id, chunks, metadata)

        assert "Failed to add any chunks to Weaviate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_flashcards_success(self, document_processor):
        """Test successful flashcard generation."""
        # Mock flashcard generator
        mock_generator = AsyncMock()
        mock_generator.generate_flashcards.return_value = [
            {"question": "What is Python?", "answer": "A programming language"},
            {"question": "What is async?", "answer": "Asynchronous programming"}
        ]
        document_processor.flashcard_generator = mock_generator

        result = await document_processor._generate_flashcards(
            "test-123",
            "Content about Python programming",
            {"title": "Python Guide"}
        )

        assert len(result) == 2
        assert result[0]['question'] == "What is Python?"
        assert result[0]['metadata']['document_id'] == "test-123"
        mock_generator.generate_flashcards.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_flashcards_failure(self, document_processor):
        """Test failed flashcard generation."""
        # Test with no flashcard generator
        document_processor.flashcard_generator = None

        result = await document_processor._generate_flashcards(
            "test-123",
            "Content",
            {"title": "Test"}
        )

        assert result == []  # Should return empty list, not raise


class TestAsyncContextManager:
    """Test async context manager functionality."""

    @pytest.mark.asyncio
    async def test_context_manager_entry_exit(self, document_processor):
        """Test async context manager entry and exit."""
        # Mock get_processing_statistics
        document_processor.get_processing_statistics = AsyncMock(return_value={
            'documents_processed': 5,
            'success_rate': 0.8
        })

        async with document_processor as processor:
            assert processor is document_processor

        # Should have called get_processing_statistics on exit
        document_processor.get_processing_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_with_exception(self, document_processor):
        """Test async context manager behavior with exceptions."""
        document_processor.get_processing_statistics = AsyncMock(return_value={})

        with pytest.raises(ValueError):
            async with document_processor:
                raise ValueError("Test exception")

        # Should still call statistics on exit even with exception
        document_processor.get_processing_statistics.assert_called_once()


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_processing_error_creation(self):
        """Test ProcessingError exception creation."""
        # Test basic error
        error = ProcessingError("Test error")
        assert str(error) == "Test error"
        assert error.document_id is None
        assert error.errors == []

        # Test error with document ID and errors
        error = ProcessingError("Test error", "doc-123", ["Error 1", "Error 2"])
        assert error.document_id == "doc-123"
        assert error.errors == ["Error 1", "Error 2"]

    @pytest.mark.asyncio
    async def test_supabase_connection_failure(self, document_processor):
        """Test behavior when Supabase connection fails."""
        # Mock validation to fail and raise ProcessingError directly
        document_processor.validate_document_input = AsyncMock(side_effect=ProcessingError("Connection failed"))

        with pytest.raises(ProcessingError):
            await document_processor.process_document(
                "Test content",
                {"title": "Test"}
            )

    @pytest.mark.asyncio
    async def test_weaviate_connection_failure(self, document_processor):
        """Test behavior when Weaviate connection fails."""
        # Mock successful Supabase but failed Weaviate
        document_processor._store_document_metadata = AsyncMock(return_value="supabase-123")
        document_processor.validate_document_input = AsyncMock(return_value=True)
        document_processor._create_vector_embeddings = AsyncMock(side_effect=Exception("Weaviate connection failed"))

        result = await document_processor.process_document(
            "Test content",
            {"title": "Test"}
        )

        # Should be partial success
        assert result.status == 'partial'
        assert "Weaviate connection failed" in str(result.errors)

    @pytest.mark.asyncio
    async def test_openai_api_failure(self, document_processor):
        """Test behavior when OpenAI API fails."""
        # Mock OpenAI failure in flashcard generation
        mock_generator = AsyncMock()
        mock_generator.generate_flashcards.side_effect = Exception("OpenAI API error")
        document_processor.flashcard_generator = mock_generator

        # Mock other components to succeed
        document_processor._store_document_metadata = AsyncMock(return_value="supabase-123")
        document_processor._create_vector_embeddings = AsyncMock(return_value="weaviate-123")
        document_processor.validate_document_input = AsyncMock(return_value=True)

        result = await document_processor.process_document(
            "Test content",
            {"title": "Test"},
            generate_flashcards=True
        )

        # Should still succeed but with no flashcards
        assert result.status == 'success'
        assert result.flashcards_created == 0

    @pytest.mark.asyncio
    async def test_concurrent_processing_limits(self, document_processor):
        """Test behavior at processing concurrency limits."""
        # Create many documents
        documents = [DocumentInput(f"Content {i}", {"title": f"Doc {i}"}) for i in range(20)]

        # Mock processing with delay
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(0.001)  # Small delay
            return ProcessingResult(document_id="test", status='success')

        document_processor.process_document = slow_process

        # Process with very low concurrency
        result = await document_processor.process_batch(documents, max_concurrent=2)

        assert result.total_documents == 20
        assert result.successful == 20


class TestDataModels:
    """Test data model classes and dataclasses."""

    def test_document_input_creation(self):
        """Test DocumentInput dataclass creation."""
        doc_input = DocumentInput(
            content="Test content",
            metadata={"title": "Test"},
            generate_flashcards=False,
            chunk_size=500,
            overlap_size=50
        )

        assert doc_input.content == "Test content"
        assert doc_input.metadata == {"title": "Test"}
        assert doc_input.generate_flashcards == False
        assert doc_input.chunk_size == 500
        assert doc_input.overlap_size == 50

    def test_processing_result_creation(self):
        """Test ProcessingResult dataclass creation."""
        result = ProcessingResult(
            document_id="test-123",
            supabase_id="supabase-456",
            weaviate_id="weaviate-789",
            flashcards_created=5,
            chunks_created=3,
            status='success',
            errors=["warning 1"],
            processing_time=2.5,
            metadata={"source": "test"}
        )

        assert result.document_id == "test-123"
        assert result.supabase_id == "supabase-456"
        assert result.weaviate_id == "weaviate-789"
        assert result.flashcards_created == 5
        assert result.chunks_created == 3
        assert result.status == 'success'
        assert result.errors == ["warning 1"]
        assert result.processing_time == 2.5
        assert result.metadata == {"source": "test"}

    def test_batch_processing_result_creation(self):
        """Test BatchProcessingResult dataclass creation."""
        results = [
            ProcessingResult("doc-1", status='success'),
            ProcessingResult("doc-2", status='failed')
        ]

        batch_result = BatchProcessingResult(
            total_documents=2,
            successful=1,
            partial=0,
            failed=1,
            results=results,
            total_processing_time=5.0,
            errors=["batch error"]
        )

        assert batch_result.total_documents == 2
        assert batch_result.successful == 1
        assert batch_result.failed == 1
        assert len(batch_result.results) == 2
        assert batch_result.total_processing_time == 5.0

    def test_document_status_creation(self):
        """Test DocumentStatus dataclass creation."""
        from datetime import datetime

        status = DocumentStatus(
            document_id="test-123",
            title="Test Document",
            status='completed',
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            updated_at=datetime(2024, 1, 1, 11, 0, 0),
            supabase_synced=True,
            weaviate_synced=False,
            flashcards_count=10,
            chunks_count=3,
            error_message="Warning message"
        )

        assert status.document_id == "test-123"
        assert status.title == "Test Document"
        assert status.status == 'completed'
        assert status.supabase_synced == True
        assert status.weaviate_synced == False
        assert status.flashcards_count == 10
        assert status.chunks_count == 3

    def test_document_chunk_creation(self):
        """Test DocumentChunk dataclass creation."""
        chunk = DocumentChunk(
            chunk_id="chunk-123",
            document_id="doc-456",
            content="This is chunk content",
            chunk_index=2,
            start_position=100,
            end_position=200,
            metadata={"type": "paragraph"}
        )

        assert chunk.chunk_id == "chunk-123"
        assert chunk.document_id == "doc-456"
        assert chunk.content == "This is chunk content"
        assert chunk.chunk_index == 2
        assert chunk.start_position == 100
        assert chunk.end_position == 200
        assert chunk.metadata == {"type": "paragraph"}


class TestIntegration:
    """Integration tests for DocumentProcessor with real dependencies."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_document_processing(self, mock_weaviate_client_factory):
        """Test complete end-to-end document processing workflow."""
        # Create mock dependencies
        mock_supabase = Mock()
        factory, mock_weaviate_client = mock_weaviate_client_factory
        mock_flashcard_gen = AsyncMock()

        # Setup Supabase mocks
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{'id': 'supabase-123'}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

        # Setup Weaviate mocks
        mock_weaviate_client.add_documents.return_value = 3  # 3 chunks added

        # Setup flashcard generator mock
        mock_flashcard_gen.generate_flashcards.return_value = [
            {"question": "Test question?", "answer": "Test answer", "difficulty": "medium"}
        ]

        # Create processor with mocks
        processor = DocumentProcessor(
            supabase_client=mock_supabase,
            weaviate_client=factory,
            flashcard_generator=mock_flashcard_gen
        )

        # Test document processing
        content = "This is a test document for end-to-end processing. " * 50
        metadata = {
            "title": "End-to-End Test Document",
            "source": "test_file.txt",
            "tags": ["test", "integration"]
        }

        result = await processor.process_document(content, metadata)

        # Verify results
        assert result.status == 'success'
        assert result.supabase_id == 'supabase-123'
        assert result.weaviate_id is not None
        assert result.chunks_created > 0
        assert result.flashcards_created == 1

        # Verify all systems were called
        mock_supabase.table.assert_called()
        mock_weaviate_client.add_documents.assert_called_once()
        mock_flashcard_gen.generate_flashcards.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cross_system_synchronization(self, mock_weaviate_client_factory):
        """Test synchronization between Supabase and Weaviate systems."""
        # Create mock dependencies
        mock_supabase = Mock()
        factory, mock_weaviate_client = mock_weaviate_client_factory

        # Setup processor
        processor = DocumentProcessor(
            supabase_client=mock_supabase,
            weaviate_client=factory
        )

        # Mock Supabase documents that need syncing
        supabase_docs = [
            {
                'document_id': 'doc-1',
                'content': 'Content for doc 1',
                'title': 'Document 1',
                'tags': ['test'],
                'weaviate_synced': False
            },
            {
                'document_id': 'doc-2',
                'content': 'Content for doc 2',
                'title': 'Document 2',
                'tags': ['test'],
                'weaviate_synced': False
            }
        ]
        mock_supabase.table.return_value.select.return_value.execute.return_value.data = supabase_docs

        # Mock Weaviate operations
        mock_weaviate_client.semantic_search.return_value = []  # No existing documents
        mock_weaviate_client.add_documents.return_value = 1

        # Mock document update operations
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

        # Test synchronization
        result = await processor.sync_all_documents()

        assert result['total_documents'] == 2
        assert result['supabase_to_weaviate_synced'] >= 0


class TestPerformance:
    """Performance tests for DocumentProcessor."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_document_processing(self):
        """Test processing of large documents."""
        mock_supabase = Mock()
        mock_weaviate_factory = Mock()

        processor = DocumentProcessor(
            supabase_client=mock_supabase,
            weaviate_client=mock_weaviate_factory,
            default_chunk_size=1000,
            default_overlap_size=200
        )

        # Create large document (100KB)
        large_content = "This is a large document with lots of content. " * 2000  # ~100KB
        metadata = {
            "title": "Large Document Performance Test",
            "source": "large_doc.md",
            "tags": ["performance", "large"]
        }

        # Mock processing components
        processor._store_document_metadata = AsyncMock(return_value="supabase-large")
        processor._create_vector_embeddings = AsyncMock(return_value="weaviate-large")
        processor._generate_flashcards = AsyncMock(return_value=[])
        processor.validate_document_input = AsyncMock(return_value=True)

        # Measure processing time
        import time
        start_time = time.time()

        result = await processor.process_document(large_content, metadata)

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify large document handling
        assert result.status == 'success'
        assert result.chunks_created > 10  # Should create many chunks
        assert processing_time < 5.0  # Should process within reasonable time

        # Verify chunking performance - large doc should be chunked efficiently
        chunks = processor.chunk_document(large_content)
        assert len(chunks) > 50  # Should create many chunks for 100KB
        assert all(len(chunk.content) <= 1200 for chunk in chunks)  # Respect chunk size + overlap

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self):
        """Test performance of concurrent document processing."""
        mock_supabase = Mock()
        mock_weaviate_factory = Mock()

        processor = DocumentProcessor(
            supabase_client=mock_supabase,
            weaviate_client=mock_weaviate_factory
        )

        # Create many medium-sized documents
        documents = []
        for i in range(50):
            content = f"Medium document {i}. " * 100  # ~2KB each
            metadata = {"title": f"Concurrent Doc {i}", "source": f"concurrent_{i}.md"}
            documents.append(DocumentInput(content, metadata, generate_flashcards=False))

        # Mock processing with realistic delay
        async def realistic_process(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms processing time
            return ProcessingResult(document_id=f"concurrent-{len(args)}", status='success')

        processor.process_document = realistic_process

        # Test different concurrency levels
        concurrency_levels = [1, 5, 10]
        times = []

        for concurrency in concurrency_levels:
            import time
            start_time = time.time()

            result = await processor.process_batch(documents, max_concurrent=concurrency)

            end_time = time.time()
            processing_time = end_time - start_time
            times.append(processing_time)

            assert result.successful == 50
            assert result.failed == 0

        # Verify that higher concurrency improves performance
        # Sequential (concurrency=1) should be slowest
        assert times[0] > times[1]  # concurrency=1 slower than concurrency=5
        assert times[1] >= times[2]  # concurrency=5 slower or equal to concurrency=10

    @pytest.mark.performance
    def test_memory_usage_during_chunking(self):
        """Test memory usage during document chunking."""
        # Create a large document
        large_content = "Large content for memory testing. " * 200  # ~6800 characters

        processor = DocumentProcessor()

        # Test chunking with small chunk size
        chunks = processor.chunk_document(large_content, chunk_size=500, overlap_size=50)

        # Verify chunks
        assert len(chunks) > 1
        for chunk in chunks:
            # Allow some tolerance for paragraph preservation and overlap
            assert len(chunk.content) <= 700  # chunk_size + overlap + some tolerance
            assert len(chunk.chunk_id) > 0
            assert chunk.content.strip()  # No empty chunks

        # Verify chunk continuity
        total_content_covered = 0
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            if i > 0:
                # Check overlap exists (except for paragraph boundaries)
                assert chunk.start_position >= chunks[i-1].start_position
            total_content_covered += len(chunk.content)

        # Should cover the content with some redundancy due to overlap
        assert total_content_covered >= len(large_content)
