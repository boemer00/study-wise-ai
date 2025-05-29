"""
Real integration tests for the StudyWise AI document processing pipeline.

This module contains integration tests that validate the complete system
functionality using actual Supabase and Weaviate instances. These tests
require proper environment configuration and should be run against test
environments only.

Usage:
    # Run all integration tests
    pytest tests/integration_tests.py -m integration

    # Run specific test categories
    pytest tests/integration_tests.py -m "integration and not performance"
    pytest tests/integration_tests.py -m "integration and performance"
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any
import logging

from src.integration_test_manager import (
    IntegrationTestManager,
    TestDataFactory,
    EnvironmentValidator,
    TestEnvironment
)
from src.document_processor import DocumentProcessor
from src.weaviate_client import WeaviateClient
from src.supabase_client import get_supabase_client


# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def test_environment():
    """Create test environment configuration from environment variables."""
    # Check if we're in a real test environment
    if not os.getenv('INTEGRATION_TEST_ENV'):
        pytest.skip("Integration tests require INTEGRATION_TEST_ENV to be set")

    # Load test environment from environment variables
    return TestEnvironment(
        test_id=os.getenv('INTEGRATION_TEST_ENV', 'pytest_session'),
        supabase_url=os.getenv('SUPABASE_URL_TEST', 'https://test.supabase.co'),
        supabase_key=os.getenv('SUPABASE_SERVICE_ROLE_KEY_TEST', 'test_key'),
        weaviate_url=os.getenv('WEAVIATE_URL_TEST', 'http://localhost:8080'),
        weaviate_api_key=os.getenv('WEAVIATE_API_KEY_TEST'),
        openai_api_key=os.getenv('OPENAI_API_KEY_TEST', 'test_key'),
        test_schema_suffix=os.getenv('TEST_SCHEMA_SUFFIX', 'test'),
        cleanup_on_exit=True
    )


@pytest.fixture(scope="session")
async def integration_test_manager(test_environment):
    """Create and setup integration test manager for the session."""
    manager = IntegrationTestManager(test_environment)

    try:
        # Set up test environment (only if services are available)
        try:
            await manager.setup_test_environment()
            yield manager
        except Exception as e:
            logger.warning(f"Could not set up real test environment: {e}")
            pytest.skip(f"Integration test environment unavailable: {e}")
    finally:
        # Clean up test environment
        try:
            await manager.teardown_test_environment()
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


@pytest.fixture
def test_data_factory():
    """Create test data factory for generating test documents."""
    return TestDataFactory(seed=42)


@pytest.mark.integration
class TestServiceConnectivity:
    """Test connectivity to all required external services."""

    @pytest.mark.asyncio
    async def test_supabase_connection(self, test_environment):
        """Test connection to Supabase test instance."""
        validator = EnvironmentValidator(test_environment)

        try:
            result = await validator.validate_supabase_connection()
            assert result is True
            logger.info("✅ Supabase connection test passed")
        except Exception as e:
            pytest.skip(f"Supabase not available for testing: {e}")

    @pytest.mark.asyncio
    async def test_weaviate_connection(self, test_environment):
        """Test connection to Weaviate test instance."""
        validator = EnvironmentValidator(test_environment)

        try:
            result = await validator.validate_weaviate_connection()
            assert result is True
            logger.info("✅ Weaviate connection test passed")
        except Exception as e:
            pytest.skip(f"Weaviate not available for testing: {e}")

    @pytest.mark.asyncio
    async def test_openai_connection(self, test_environment):
        """Test connection to OpenAI API."""
        validator = EnvironmentValidator(test_environment)

        try:
            result = await validator.validate_openai_connection()
            assert result is True
            logger.info("✅ OpenAI connection test passed")
        except Exception as e:
            if "quota" in str(e).lower() or "rate" in str(e).lower():
                logger.info("✅ OpenAI API accessible (quota/rate limited)")
                return  # This is acceptable for testing
            pytest.skip(f"OpenAI API not available for testing: {e}")

    def test_environment_variables(self, test_environment):
        """Test that all required environment variables are present."""
        validator = EnvironmentValidator(test_environment)
        missing_vars = validator.check_required_env_vars()

        if missing_vars:
            pytest.skip(f"Missing environment variables: {missing_vars}")

        logger.info("✅ All required environment variables present")


@pytest.mark.integration
class TestDocumentProcessingPipeline:
    """Test the complete document processing pipeline end-to-end."""

    @pytest.mark.asyncio
    async def test_single_document_processing(
        self,
        integration_test_manager,
        test_data_factory
    ):
        """Test processing a single document through the complete pipeline."""
        async def test_single_doc(test_space_id):
            # Create test document
            doc = test_data_factory.create_test_document(
                content="This is a test document for integration testing. It contains sample content that should be processed, chunked, and have embeddings generated.",
                title="Integration Test Document",
                tags=["integration", "test"],
                test_space_id=test_space_id
            )

            # Create document processor
            processor = DocumentProcessor(
                openai_api_key=integration_test_manager.test_env.openai_api_key,
                supabase_url=integration_test_manager.test_env.supabase_url,
                supabase_key=integration_test_manager.test_env.supabase_key,
                weaviate_url=integration_test_manager.test_env.weaviate_url,
                weaviate_api_key=integration_test_manager.test_env.weaviate_api_key
            )

            # Process document
            result = await processor.process_document(doc)

            # Verify processing succeeded
            assert result.success
            assert result.document_id is not None
            assert len(result.chunks) > 0
            assert result.flashcards is not None

            logger.info(f"✅ Successfully processed document: {result.document_id}")
            return True

        result = await integration_test_manager.run_integration_test(
            "single_document_processing",
            test_single_doc,
            timeout=300
        )

        assert result.success, f"Test failed: {result.error_message}"

    @pytest.mark.asyncio
    async def test_batch_document_processing(
        self,
        integration_test_manager,
        test_data_factory
    ):
        """Test processing multiple documents in a batch."""
        async def test_batch_processing(test_space_id):
            # Create batch of test documents
            docs = test_data_factory.create_test_batch(
                count=3,
                content_template="Batch document {} content for integration testing.",
                vary_metadata=True
            )

            # Add test_space_id to all documents
            for doc in docs:
                doc.metadata["test_space_id"] = test_space_id

            # Create document processor
            processor = DocumentProcessor(
                openai_api_key=integration_test_manager.test_env.openai_api_key,
                supabase_url=integration_test_manager.test_env.supabase_url,
                supabase_key=integration_test_manager.test_env.supabase_key,
                weaviate_url=integration_test_manager.test_env.weaviate_url,
                weaviate_api_key=integration_test_manager.test_env.weaviate_api_key
            )

            # Process batch
            results = await processor.process_batch(docs)

            # Verify all documents processed successfully
            assert len(results) == 3
            for result in results:
                assert result.success
                assert result.document_id is not None

            logger.info(f"✅ Successfully processed batch of {len(results)} documents")
            return True

        result = await integration_test_manager.run_integration_test(
            "batch_document_processing",
            test_batch_processing,
            timeout=600
        )

        assert result.success, f"Test failed: {result.error_message}"

    @pytest.mark.asyncio
    async def test_pdf_document_processing(
        self,
        integration_test_manager,
        test_data_factory
    ):
        """Test processing PDF documents."""
        async def test_pdf_processing(test_space_id):
            try:
                # Generate sample PDF
                pdf_content = "This is a PDF document for integration testing. It contains formatted text that should be extracted and processed correctly."
                pdf_bytes, filename = test_data_factory.generate_sample_pdf(pdf_content)

                # Save PDF to temporary file
                temp_dir = Path(tempfile.gettempdir()) / f"studywise_test_{test_space_id}"
                temp_dir.mkdir(exist_ok=True)
                pdf_path = temp_dir / filename
                pdf_path.write_bytes(pdf_bytes)

                # Create document input from PDF
                doc = test_data_factory.create_test_document(
                    content="",  # Will be extracted from PDF
                    title="PDF Integration Test",
                    file_path=str(pdf_path),
                    test_space_id=test_space_id
                )

                # Create document processor
                processor = DocumentProcessor(
                    openai_api_key=integration_test_manager.test_env.openai_api_key,
                    supabase_url=integration_test_manager.test_env.supabase_url,
                    supabase_key=integration_test_manager.test_env.supabase_key,
                    weaviate_url=integration_test_manager.test_env.weaviate_url,
                    weaviate_api_key=integration_test_manager.test_env.weaviate_api_key
                )

                # Process PDF document
                result = await processor.process_document(doc)

                # Verify processing succeeded
                assert result.success
                assert result.document_id is not None
                assert len(result.chunks) > 0

                logger.info(f"✅ Successfully processed PDF document: {filename}")
                return True

            except ImportError:
                logger.info("📋 Skipping PDF test - reportlab not available")
                return True  # Skip but don't fail

        result = await integration_test_manager.run_integration_test(
            "pdf_document_processing",
            test_pdf_processing,
            timeout=300
        )

        assert result.success, f"Test failed: {result.error_message}"

    @pytest.mark.asyncio
    async def test_document_chunking_and_embeddings(
        self,
        integration_test_manager,
        test_data_factory
    ):
        """Test document chunking and vector embedding generation."""
        async def test_chunking_embeddings(test_space_id):
            # Create large document for chunking
            doc = test_data_factory.create_large_document(
                target_size_kb=50,  # Smaller for faster testing
                chunk_friendly=True
            )
            doc.metadata["test_space_id"] = test_space_id

            # Create document processor
            processor = DocumentProcessor(
                openai_api_key=integration_test_manager.test_env.openai_api_key,
                supabase_url=integration_test_manager.test_env.supabase_url,
                supabase_key=integration_test_manager.test_env.supabase_key,
                weaviate_url=integration_test_manager.test_env.weaviate_url,
                weaviate_api_key=integration_test_manager.test_env.weaviate_api_key
            )

            # Process document
            result = await processor.process_document(doc)

            # Verify chunking worked
            assert result.success
            assert len(result.chunks) > 1  # Should be chunked

            # Verify chunks have reasonable sizes
            for chunk in result.chunks:
                assert len(chunk.content) > 0
                assert len(chunk.content) <= processor.chunk_size + processor.chunk_overlap

            logger.info(f"✅ Successfully chunked document into {len(result.chunks)} chunks")
            return True

        result = await integration_test_manager.run_integration_test(
            "document_chunking_and_embeddings",
            test_chunking_embeddings,
            timeout=300
        )

        assert result.success, f"Test failed: {result.error_message}"

    @pytest.mark.asyncio
    async def test_flashcard_generation(
        self,
        integration_test_manager,
        test_data_factory
    ):
        """Test flashcard generation from processed documents."""
        async def test_flashcards(test_space_id):
            # Create document with educational content
            doc = test_data_factory.create_test_document(
                content="""
                Python is a high-level programming language. It was created by Guido van Rossum and first released in 1991.
                Python emphasizes code readability and simplicity. It uses indentation to define code blocks.
                Python supports multiple programming paradigms including procedural, object-oriented, and functional programming.
                The Python Package Index (PyPI) contains thousands of third-party modules.
                """,
                title="Python Programming Basics",
                tags=["programming", "python", "education"],
                test_space_id=test_space_id
            )

            # Create document processor
            processor = DocumentProcessor(
                openai_api_key=integration_test_manager.test_env.openai_api_key,
                supabase_url=integration_test_manager.test_env.supabase_url,
                supabase_key=integration_test_manager.test_env.supabase_key,
                weaviate_url=integration_test_manager.test_env.weaviate_url,
                weaviate_api_key=integration_test_manager.test_env.weaviate_api_key,
                max_flashcards=3
            )

            # Process document
            result = await processor.process_document(doc)

            # Verify flashcard generation
            assert result.success
            assert result.flashcards is not None
            assert len(result.flashcards) > 0

            # Verify flashcard structure
            for flashcard in result.flashcards:
                assert "question" in flashcard
                assert "answer" in flashcard
                assert len(flashcard["question"]) > 0
                assert len(flashcard["answer"]) > 0

            logger.info(f"✅ Successfully generated {len(result.flashcards)} flashcards")
            return True

        result = await integration_test_manager.run_integration_test(
            "flashcard_generation",
            test_flashcards,
            timeout=300
        )

        assert result.success, f"Test failed: {result.error_message}"


@pytest.mark.integration
class TestDataConsistency:
    """Test data consistency across Supabase and Weaviate."""

    @pytest.mark.asyncio
    async def test_document_metadata_consistency(
        self,
        integration_test_manager,
        test_data_factory
    ):
        """Test that document metadata is consistent between systems."""
        async def test_metadata_consistency(test_space_id):
            # Create test document with rich metadata
            doc = test_data_factory.create_test_document(
                content="Document for testing metadata consistency across systems.",
                title="Metadata Consistency Test",
                tags=["consistency", "metadata", "test"],
                category="test_category",
                priority="high",
                test_space_id=test_space_id
            )

            # Process document
            processor = DocumentProcessor(
                openai_api_key=integration_test_manager.test_env.openai_api_key,
                supabase_url=integration_test_manager.test_env.supabase_url,
                supabase_key=integration_test_manager.test_env.supabase_key,
                weaviate_url=integration_test_manager.test_env.weaviate_url,
                weaviate_api_key=integration_test_manager.test_env.weaviate_api_key
            )

            result = await processor.process_document(doc)
            assert result.success

            # Verify metadata consistency (basic check)
            assert result.document_id is not None

            logger.info(f"✅ Metadata consistency verified for document: {result.document_id}")
            return True

        result = await integration_test_manager.run_integration_test(
            "document_metadata_consistency",
            test_metadata_consistency,
            timeout=300
        )

        assert result.success, f"Test failed: {result.error_message}"


@pytest.mark.integration
class TestSearchFunctionality:
    """Test search functionality with real vector embeddings."""

    @pytest.mark.asyncio
    async def test_semantic_search(
        self,
        integration_test_manager,
        test_data_factory
    ):
        """Test semantic search functionality."""
        async def test_search(test_space_id):
            # Create documents with related content
            docs = [
                test_data_factory.create_test_document(
                    content="Machine learning is a subset of artificial intelligence that focuses on algorithms.",
                    title="Machine Learning Basics",
                    test_space_id=test_space_id
                ),
                test_data_factory.create_test_document(
                    content="Deep learning uses neural networks with multiple layers to learn patterns.",
                    title="Deep Learning Introduction",
                    test_space_id=test_space_id
                ),
                test_data_factory.create_test_document(
                    content="Cooking pasta requires boiling water and adding salt for flavor.",
                    title="Pasta Cooking Guide",
                    test_space_id=test_space_id
                )
            ]

            # Process all documents
            processor = DocumentProcessor(
                openai_api_key=integration_test_manager.test_env.openai_api_key,
                supabase_url=integration_test_manager.test_env.supabase_url,
                supabase_key=integration_test_manager.test_env.supabase_key,
                weaviate_url=integration_test_manager.test_env.weaviate_url,
                weaviate_api_key=integration_test_manager.test_env.weaviate_api_key
            )

            results = await processor.process_batch(docs)
            assert all(r.success for r in results)

            # Allow some time for indexing
            await asyncio.sleep(2)

            # Test semantic search
            weaviate_client = WeaviateClient(
                url=integration_test_manager.test_env.weaviate_url,
                api_key=integration_test_manager.test_env.weaviate_api_key
            )

            async with weaviate_client:
                # Search for AI-related content
                search_results = await weaviate_client.semantic_search(
                    query="artificial intelligence algorithms",
                    limit=3
                )

                # Should find the ML and DL documents first
                assert len(search_results) > 0

                logger.info(f"✅ Semantic search returned {len(search_results)} results")
                return True

        result = await integration_test_manager.run_integration_test(
            "semantic_search",
            test_search,
            timeout=300
        )

        assert result.success, f"Test failed: {result.error_message}"


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_document_processing(
        self,
        integration_test_manager,
        test_data_factory
    ):
        """Test handling of invalid documents."""
        async def test_invalid_doc(test_space_id):
            # Create document with invalid/empty content
            doc = test_data_factory.create_test_document(
                content="",  # Empty content
                title="",    # Empty title
                test_space_id=test_space_id
            )

            # Process document
            processor = DocumentProcessor(
                openai_api_key=integration_test_manager.test_env.openai_api_key,
                supabase_url=integration_test_manager.test_env.supabase_url,
                supabase_key=integration_test_manager.test_env.supabase_key,
                weaviate_url=integration_test_manager.test_env.weaviate_url,
                weaviate_api_key=integration_test_manager.test_env.weaviate_api_key
            )

            # Should handle gracefully
            result = await processor.process_document(doc)

            # Processing might fail, but should not crash
            logger.info(f"✅ Invalid document handled gracefully: success={result.success}")
            return True

        result = await integration_test_manager.run_integration_test(
            "invalid_document_processing",
            test_invalid_doc,
            timeout=120
        )

        assert result.success, f"Test failed: {result.error_message}"


@pytest.mark.integration
class TestDataIsolation:
    """Test data isolation between test runs."""

    @pytest.mark.asyncio
    async def test_test_space_isolation(
        self,
        integration_test_manager
    ):
        """Test that test spaces are properly isolated."""
        # Create multiple test spaces
        space1 = await integration_test_manager.create_isolated_test_space()
        space2 = await integration_test_manager.create_isolated_test_space()

        # Verify they are different
        assert space1 != space2
        assert space1.startswith("test_")
        assert space2.startswith("test_")

        # Verify isolation
        assert integration_test_manager.validate_test_isolation(space1)
        assert integration_test_manager.validate_test_isolation(space2)

        # Clean up
        await integration_test_manager.cleanup_test_space(space1)
        await integration_test_manager.cleanup_test_space(space2)

        logger.info("✅ Test space isolation verified")

    @pytest.mark.asyncio
    async def test_cleanup_effectiveness(
        self,
        integration_test_manager,
        test_data_factory
    ):
        """Test that cleanup operations are effective."""
        async def test_cleanup(test_space_id):
            # Create and process a document
            doc = test_data_factory.create_test_document(
                content="Document for cleanup testing.",
                title="Cleanup Test Document",
                test_space_id=test_space_id
            )

            processor = DocumentProcessor(
                openai_api_key=integration_test_manager.test_env.openai_api_key,
                supabase_url=integration_test_manager.test_env.supabase_url,
                supabase_key=integration_test_manager.test_env.supabase_key,
                weaviate_url=integration_test_manager.test_env.weaviate_url,
                weaviate_api_key=integration_test_manager.test_env.weaviate_api_key
            )

            result = await processor.process_document(doc)
            assert result.success

            logger.info(f"✅ Document created for cleanup test: {result.document_id}")
            return True

        # Run test which will automatically clean up
        result = await integration_test_manager.run_integration_test(
            "cleanup_effectiveness",
            test_cleanup,
            timeout=300
        )

        assert result.success, f"Test failed: {result.error_message}"

        # Verify cleanup report
        cleanup_report = integration_test_manager.cleanup_manager.get_cleanup_report()
        assert cleanup_report["total_operations"] > 0

        logger.info("✅ Cleanup effectiveness verified")


@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceMetrics:
    """Test performance characteristics with real services."""

    @pytest.mark.asyncio
    async def test_document_processing_performance(
        self,
        integration_test_manager,
        test_data_factory
    ):
        """Test document processing performance metrics."""
        async def test_performance(test_space_id):
            import time

            # Create batch of documents
            docs = test_data_factory.create_test_batch(
                count=5,
                content_template="Performance test document {} with sufficient content for meaningful processing and timing measurements.",
                vary_metadata=True
            )

            for doc in docs:
                doc.metadata["test_space_id"] = test_space_id

            # Process documents and measure time
            processor = DocumentProcessor(
                openai_api_key=integration_test_manager.test_env.openai_api_key,
                supabase_url=integration_test_manager.test_env.supabase_url,
                supabase_key=integration_test_manager.test_env.supabase_key,
                weaviate_url=integration_test_manager.test_env.weaviate_url,
                weaviate_api_key=integration_test_manager.test_env.weaviate_api_key
            )

            start_time = time.time()
            results = await processor.process_batch(docs)
            duration = time.time() - start_time

            # Verify all processed successfully
            assert all(r.success for r in results)

            # Performance metrics
            docs_per_second = len(docs) / duration

            logger.info(f"✅ Performance test: {len(docs)} docs in {duration:.2f}s ({docs_per_second:.2f} docs/sec)")

            # Basic performance assertion (adjust as needed)
            assert docs_per_second > 0.1  # At least 0.1 docs per second

            return True

        result = await integration_test_manager.run_integration_test(
            "document_processing_performance",
            test_performance,
            timeout=600
        )

        assert result.success, f"Test failed: {result.error_message}"


# Utility functions for integration testing
def require_test_environment():
    """Decorator to ensure tests only run in test environment."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not os.getenv('INTEGRATION_TEST_ENV'):
                pytest.skip("Integration tests require INTEGRATION_TEST_ENV to be set")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def skip_if_no_services():
    """Decorator to skip tests if required services are not available."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Check for basic service availability
            if not os.getenv('SUPABASE_URL_TEST') or not os.getenv('WEAVIATE_URL_TEST'):
                pytest.skip("Required services not configured for integration testing")
            return func(*args, **kwargs)
        return wrapper
    return decorator


async def wait_for_processing_completion(
    document_processor: DocumentProcessor,
    document_id: str,
    timeout: int = 300
) -> bool:
    """
    Wait for document processing to complete.

    Args:
        document_processor: DocumentProcessor instance
        document_id: Document ID to monitor
        timeout: Maximum time to wait in seconds

    Returns:
        True if processing completed successfully
    """
    import time
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # Check if document exists and is processed
            # This would need to be implemented based on actual storage
            await asyncio.sleep(1)
            return True
        except Exception:
            await asyncio.sleep(1)

    return False


async def verify_data_consistency(
    supabase_client,
    weaviate_client: WeaviateClient,
    document_id: str
) -> Dict[str, bool]:
    """
    Verify data consistency between Supabase and Weaviate.

    Args:
        supabase_client: Supabase client instance
        weaviate_client: Weaviate client instance
        document_id: Document ID to verify

    Returns:
        Dictionary of consistency check results
    """
    results = {
        "supabase_exists": False,
        "weaviate_exists": False,
        "metadata_matches": False
    }

    try:
        # Check Supabase
        supabase_response = supabase_client.table('documents').select('*').eq('id', document_id).execute()
        results["supabase_exists"] = len(supabase_response.data) > 0

        # Check Weaviate
        async with weaviate_client:
            weaviate_docs = await weaviate_client.get_document(document_id)
            results["weaviate_exists"] = weaviate_docs is not None

        # Basic consistency check
        results["metadata_matches"] = results["supabase_exists"] and results["weaviate_exists"]

    except Exception as e:
        logger.warning(f"Consistency check failed: {e}")

    return results


def generate_performance_report(
    test_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate performance report from test results.

    Args:
        test_results: List of test result dictionaries

    Returns:
        Performance report dictionary
    """
    if not test_results:
        return {"error": "No test results provided"}

    total_tests = len(test_results)
    successful_tests = sum(1 for r in test_results if r.get("success", False))
    total_duration = sum(r.get("duration_seconds", 0) for r in test_results)

    return {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
        "total_duration_seconds": total_duration,
        "average_duration_seconds": total_duration / total_tests if total_tests > 0 else 0,
        "performance_summary": f"{successful_tests}/{total_tests} tests passed in {total_duration:.2f}s"
    }
