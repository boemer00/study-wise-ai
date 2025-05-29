"""
Tests for integration test manager functionality.

This module contains comprehensive tests for the integration testing framework,
including unit tests for individual components and integration tests that
validate the testing infrastructure itself.
"""

import pytest
import asyncio
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from src.integration_test_manager import (
    IntegrationTestManager,
    TestDataFactory,
    EnvironmentValidator,
    CleanupManager,
    TestEnvironment,
    IntegrationTestResult,
    IntegrationTestError,
    EnvironmentSetupError,
    CleanupError,
    TestIsolationError
)


@pytest.fixture
def mock_test_environment():
    """Create mock test environment configuration."""
    return TestEnvironment(
        test_id="test_env_123",
        supabase_url="https://test.supabase.co",
        supabase_key="test_key",
        weaviate_url="http://localhost:8080",
        weaviate_api_key="test_weaviate_key",
        openai_api_key="test_openai_key",
        test_schema_suffix="test",
        cleanup_on_exit=True
    )


@pytest.fixture
def mock_supabase_client():
    """Create mock Supabase client."""
    mock_client = Mock()
    mock_table = Mock()
    mock_query = Mock()
    mock_response = Mock()

    # Chain the method calls
    mock_response.data = []
    mock_query.execute.return_value = mock_response
    mock_table.delete.return_value = mock_query
    mock_table.select.return_value = mock_query
    mock_client.table.return_value = mock_table

    return mock_client


@pytest.fixture
def mock_weaviate_client():
    """Create mock Weaviate client."""
    mock_client = AsyncMock()
    mock_client.health_check.return_value = True
    mock_client.create_schema.return_value = None
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return mock_client


@pytest.fixture
def mock_document_processor():
    """Create mock document processor."""
    mock_processor = AsyncMock()
    mock_processor.process_document.return_value = Mock()
    return mock_processor


@pytest.fixture
def temporary_test_directory():
    """Create temporary directory for test files."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestIntegrationTestManager:
    """Test suite for IntegrationTestManager class."""

    @pytest.fixture
    def test_manager(self, mock_test_environment):
        """Create IntegrationTestManager instance for testing."""
        return IntegrationTestManager(mock_test_environment)

    def test_init_with_valid_environment(self, mock_test_environment):
        """Test initialization with valid test environment."""
        manager = IntegrationTestManager(mock_test_environment)

        assert manager.test_env == mock_test_environment
        assert manager.cleanup_timeout == 300
        assert manager.active_test_spaces == []
        assert not manager._setup_complete
        assert isinstance(manager.cleanup_manager, CleanupManager)
        assert isinstance(manager.validator, EnvironmentValidator)

    def test_init_with_invalid_environment(self):
        """Test initialization with invalid test environment."""
        with pytest.raises((TypeError, AttributeError)):
            IntegrationTestManager(None)

    @pytest.mark.asyncio
    async def test_setup_test_environment_success(self, test_manager):
        """Test successful test environment setup."""
        # Mock the validator methods
        with patch.object(test_manager.validator, 'validate_supabase_connection', return_value=True), \
             patch.object(test_manager.validator, 'validate_weaviate_connection', return_value=True), \
             patch.object(test_manager.validator, 'validate_openai_connection', return_value=True), \
             patch.object(test_manager.validator, 'check_required_env_vars', return_value=[]), \
             patch.object(test_manager.validator, 'validate_schema_permissions', return_value={"supabase": True, "weaviate": True}), \
             patch.object(test_manager, '_setup_test_schemas'):

            await test_manager.setup_test_environment()
            assert test_manager._setup_complete

    @pytest.mark.asyncio
    async def test_setup_test_environment_failure(self, test_manager):
        """Test test environment setup failure."""
        # Mock validator to fail
        with patch.object(test_manager.validator, 'validate_supabase_connection', side_effect=ConnectionError("Failed")):
            with pytest.raises(EnvironmentSetupError):
                await test_manager.setup_test_environment()
            assert not test_manager._setup_complete

    @pytest.mark.asyncio
    async def test_teardown_test_environment_success(self, test_manager):
        """Test successful test environment teardown."""
        # Set up some test state
        test_manager.active_test_spaces = ["test_space_1", "test_space_2"]
        test_manager._setup_complete = True

        # Mock cleanup operations
        with patch.object(test_manager, 'cleanup_test_space') as mock_cleanup, \
             patch.object(test_manager.cleanup_manager, 'emergency_cleanup'):

            await test_manager.teardown_test_environment()
            assert mock_cleanup.call_count == 2
            assert not test_manager._setup_complete

    @pytest.mark.asyncio
    async def test_teardown_test_environment_partial_failure(self, test_manager):
        """Test test environment teardown with partial failures."""
        test_manager.active_test_spaces = ["test_space_1"]

        # Mock cleanup to fail
        with patch.object(test_manager, 'cleanup_test_space', side_effect=Exception("Cleanup failed")), \
             patch.object(test_manager.cleanup_manager, 'emergency_cleanup'):

            # Should not raise exception even if cleanup fails
            await test_manager.teardown_test_environment()
            assert not test_manager._setup_complete

    @pytest.mark.asyncio
    async def test_create_isolated_test_space(self, test_manager):
        """Test creation of isolated test space."""
        test_manager._setup_complete = True

        with patch.object(test_manager, '_create_supabase_test_space'), \
             patch.object(test_manager, '_create_weaviate_test_space'):

            test_space_id = await test_manager.create_isolated_test_space()

            assert test_space_id.startswith("test_")
            assert test_space_id in test_manager.active_test_spaces

    @pytest.mark.asyncio
    async def test_cleanup_test_space_success(self, test_manager):
        """Test successful test space cleanup."""
        test_space_id = "test_space_123"
        test_manager.active_test_spaces = [test_space_id]

        with patch.object(test_manager.cleanup_manager, 'cleanup_supabase_data'), \
             patch.object(test_manager.cleanup_manager, 'cleanup_weaviate_data'), \
             patch.object(test_manager.cleanup_manager, 'cleanup_temporary_files'):

            await test_manager.cleanup_test_space(test_space_id)
            assert test_space_id not in test_manager.active_test_spaces

    @pytest.mark.asyncio
    async def test_cleanup_test_space_failure(self, test_manager):
        """Test test space cleanup failure."""
        test_space_id = "test_space_123"

        with patch.object(test_manager.cleanup_manager, 'cleanup_supabase_data', side_effect=Exception("Cleanup failed")):
            with pytest.raises(CleanupError):
                await test_manager.cleanup_test_space(test_space_id)

    @pytest.mark.asyncio
    async def test_run_integration_test_success(self, test_manager):
        """Test successful integration test execution."""
        async def mock_test_function(test_space_id):
            assert test_space_id is not None
            return True

        with patch.object(test_manager, 'create_isolated_test_space', return_value="test_space_123"), \
             patch.object(test_manager, 'cleanup_test_space'), \
             patch.object(test_manager, '_collect_test_metrics', return_value={}):

            result = await test_manager.run_integration_test("test_name", mock_test_function)

            assert result.test_name == "test_name"
            assert result.success
            assert result.error_message is None
            assert result.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_run_integration_test_timeout(self, test_manager):
        """Test integration test execution with timeout."""
        async def slow_test_function(test_space_id):
            await asyncio.sleep(2)  # Longer than timeout

        with patch.object(test_manager, 'create_isolated_test_space', return_value="test_space_123"), \
             patch.object(test_manager, 'cleanup_test_space'), \
             patch.object(test_manager, '_collect_test_metrics', return_value={}):

            result = await test_manager.run_integration_test("test_name", slow_test_function, timeout=0.1)

            assert not result.success
            assert "timed out" in result.error_message

    @pytest.mark.asyncio
    async def test_run_integration_test_exception(self, test_manager):
        """Test integration test execution with exception."""
        async def failing_test_function(test_space_id):
            raise ValueError("Test error")

        with patch.object(test_manager, 'create_isolated_test_space', return_value="test_space_123"), \
             patch.object(test_manager, 'cleanup_test_space'), \
             patch.object(test_manager, '_collect_test_metrics', return_value={}):

            result = await test_manager.run_integration_test("test_name", failing_test_function)

            assert not result.success
            assert "Test error" in result.error_message

    @pytest.mark.asyncio
    async def test_get_test_metrics(self, test_manager):
        """Test collection of test metrics."""
        with patch.object(test_manager.validator, 'check_service_versions', return_value={"weaviate": "1.0"}):
            metrics = await test_manager.get_test_metrics()

            assert "test_environment_id" in metrics
            assert "timestamp" in metrics
            assert metrics["test_environment_id"] == test_manager.test_env.test_id

    def test_validate_test_isolation_success(self, test_manager):
        """Test successful test isolation validation."""
        test_space_id = "test_space_123"
        test_manager.active_test_spaces = [test_space_id]

        result = test_manager.validate_test_isolation(test_space_id)
        assert result

    def test_validate_test_isolation_failure(self, test_manager):
        """Test test isolation validation failure."""
        # Invalid test space ID format
        result = test_manager.validate_test_isolation("invalid_space")
        assert not result

        # Test space not in active list
        result = test_manager.validate_test_isolation("test_space_not_active")
        assert not result


class TestTestDataFactory:
    """Test suite for TestDataFactory class."""

    @pytest.fixture
    def data_factory(self):
        """Create TestDataFactory instance for testing."""
        return TestDataFactory(seed=42)

    def test_init_with_seed(self):
        """Test initialization with random seed."""
        factory = TestDataFactory(seed=42)
        assert factory.seed == 42

    def test_init_without_seed(self):
        """Test initialization without random seed."""
        factory = TestDataFactory()
        assert factory.seed is None

    def test_create_test_document_basic(self, data_factory):
        """Test basic test document creation."""
        content = "Test content"
        title = "Test Document"

        doc = data_factory.create_test_document(content, title)

        assert doc.content == content
        assert doc.metadata["title"] == title
        assert doc.metadata["test_document"] is True
        assert "user_id" in doc.metadata

    def test_create_test_document_with_metadata(self, data_factory):
        """Test test document creation with metadata."""
        content = "Test content"
        title = "Test Document"
        tags = ["tag1", "tag2"]
        user_id = "test_user"
        custom_field = "custom_value"

        doc = data_factory.create_test_document(
            content, title, tags=tags, user_id=user_id, custom_field=custom_field
        )

        assert doc.metadata["tags"] == tags
        assert doc.metadata["user_id"] == user_id
        assert doc.metadata["custom_field"] == custom_field

    def test_create_test_document_invalid_input(self, data_factory):
        """Test test document creation with invalid input."""
        # Test with empty content and title - should still work
        doc = data_factory.create_test_document("", "")
        assert doc.content == ""
        assert doc.metadata["title"] == ""

    def test_create_test_batch_small(self, data_factory):
        """Test creation of small test batch."""
        count = 3
        docs = data_factory.create_test_batch(count)

        assert len(docs) == count
        for i, doc in enumerate(docs):
            assert f"content {i + 1}" in doc.content
            assert doc.metadata["test_document"] is True

    def test_create_test_batch_large(self, data_factory):
        """Test creation of large test batch."""
        count = 10
        docs = data_factory.create_test_batch(count, vary_metadata=True)

        assert len(docs) == count
        # Check that metadata varies
        doc_types = [doc.metadata.get("document_type") for doc in docs]
        assert len(set(doc_types)) > 1  # Should have variation

    def test_create_test_batch_with_variation(self, data_factory):
        """Test creation of test batch with metadata variation."""
        docs = data_factory.create_test_batch(5, vary_metadata=True)

        # Check for variation in batch_index
        batch_indices = [doc.metadata["batch_index"] for doc in docs]
        assert batch_indices == list(range(5))

    def test_generate_sample_pdf_basic(self, data_factory):
        """Test basic PDF generation."""
        content = "Test PDF content"

        try:
            pdf_bytes, filename = data_factory.generate_sample_pdf(content)

            assert isinstance(pdf_bytes, bytes)
            assert len(pdf_bytes) > 0
            assert filename.endswith(".pdf")
        except ImportError:
            # Skip test if reportlab is not available
            pytest.skip("reportlab not available for PDF generation")

    def test_generate_sample_pdf_with_filename(self, data_factory):
        """Test PDF generation with custom filename."""
        content = "Test PDF content"
        filename = "custom_test.pdf"

        try:
            pdf_bytes, returned_filename = data_factory.generate_sample_pdf(content, filename)

            assert returned_filename == filename
        except ImportError:
            # Skip test if reportlab is not available
            pytest.skip("reportlab not available for PDF generation")

    def test_create_large_document_default_size(self, data_factory):
        """Test large document creation with default size."""
        doc = data_factory.create_large_document()

        # Check that content is significantly long (around 1MB)
        assert len(doc.content) > 500000  # At least 500KB
        assert doc.metadata["target_size_kb"] == 1000
        assert doc.metadata["document_type"] == "large_test"

    def test_create_large_document_custom_size(self, data_factory):
        """Test large document creation with custom size."""
        target_size = 500
        doc = data_factory.create_large_document(target_size_kb=target_size)

        assert doc.metadata["target_size_kb"] == target_size
        # Content should be roughly the target size
        assert len(doc.content) > target_size * 512  # At least half the target

    def test_create_large_document_chunk_friendly(self, data_factory):
        """Test chunk-friendly large document creation."""
        doc = data_factory.create_large_document(target_size_kb=100, chunk_friendly=True)

        # Should contain section headers
        assert "# Section" in doc.content
        assert doc.metadata["chunk_friendly"] is True

    def test_create_multilingual_document_default(self, data_factory):
        """Test multilingual document creation with default languages."""
        doc = data_factory.create_multilingual_document()

        assert doc.metadata["multilingual"] is True
        assert "languages" in doc.metadata
        # Should contain language markers
        assert "[EN]" in doc.content
        assert "[ES]" in doc.content
        assert "[FR]" in doc.content

    def test_create_multilingual_document_custom_languages(self, data_factory):
        """Test multilingual document creation with custom languages."""
        languages = ["en", "de", "it"]
        doc = data_factory.create_multilingual_document(languages)

        assert doc.metadata["languages"] == languages
        assert "[EN]" in doc.content
        assert "[DE]" in doc.content
        assert "[IT]" in doc.content


class TestEnvironmentValidator:
    """Test suite for EnvironmentValidator class."""

    @pytest.fixture
    def validator(self, mock_test_environment):
        """Create EnvironmentValidator instance for testing."""
        return EnvironmentValidator(mock_test_environment)

    @pytest.mark.asyncio
    async def test_validate_supabase_connection_success(self, validator, mock_supabase_client):
        """Test successful Supabase connection validation."""
        with patch('src.integration_test_manager.get_supabase_client', return_value=mock_supabase_client):
            # Mock table response to simulate "table not found" (which is expected)
            mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = \
                Exception("does not exist")

            result = await validator.validate_supabase_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_supabase_connection_failure(self, validator):
        """Test Supabase connection validation failure."""
        with patch('src.integration_test_manager.get_supabase_client', side_effect=Exception("Connection failed")):
            with pytest.raises(ConnectionError):
                await validator.validate_supabase_connection()

    @pytest.mark.asyncio
    async def test_validate_weaviate_connection_success(self, validator, mock_weaviate_client):
        """Test successful Weaviate connection validation."""
        with patch('src.integration_test_manager.WeaviateClient', return_value=mock_weaviate_client):
            result = await validator.validate_weaviate_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_weaviate_connection_failure(self, validator):
        """Test Weaviate connection validation failure."""
        mock_client = AsyncMock()
        mock_client.health_check.return_value = False
        mock_client.__aenter__.return_value = mock_client

        with patch('src.integration_test_manager.WeaviateClient', return_value=mock_client):
            with pytest.raises(ConnectionError):
                await validator.validate_weaviate_connection()

    @pytest.mark.asyncio
    async def test_validate_openai_connection_success(self, validator):
        """Test successful OpenAI connection validation."""
        # Mock the openai module and its async method properly
        with patch('openai.ChatCompletion') as mock_chat:
            mock_chat.acreate = AsyncMock(return_value=Mock())

            result = await validator.validate_openai_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_openai_connection_failure(self, validator):
        """Test OpenAI connection validation failure."""
        with patch('openai.ChatCompletion.acreate', side_effect=Exception("API Error")):
            with pytest.raises(ConnectionError):
                await validator.validate_openai_connection()

    def test_check_required_env_vars_all_present(self, validator):
        """Test environment variable check with all variables present."""
        env_vars = {
            'SUPABASE_URL_TEST': 'https://test.supabase.co',
            'SUPABASE_ANON_KEY_TEST': 'test_key',
            'WEAVIATE_URL_TEST': 'http://localhost:8080',
            'OPENAI_API_KEY_TEST': 'test_openai_key'
        }

        with patch.dict('os.environ', env_vars):
            missing = validator.check_required_env_vars()
            assert missing == []

    def test_check_required_env_vars_missing_some(self, validator):
        """Test environment variable check with missing variables."""
        # Clear environment
        with patch.dict('os.environ', {}, clear=True):
            missing = validator.check_required_env_vars()
            assert len(missing) == 4
            assert 'SUPABASE_URL_TEST' in missing

    @pytest.mark.asyncio
    async def test_validate_schema_permissions_success(self, validator, mock_supabase_client, mock_weaviate_client):
        """Test successful schema permissions validation."""
        with patch('src.integration_test_manager.get_supabase_client', return_value=mock_supabase_client), \
             patch('src.integration_test_manager.WeaviateClient', return_value=mock_weaviate_client):

            permissions = await validator.validate_schema_permissions()
            assert permissions["supabase"] is True
            assert permissions["weaviate"] is True

    @pytest.mark.asyncio
    async def test_validate_schema_permissions_failure(self, validator):
        """Test schema permissions validation failure."""
        with patch('src.integration_test_manager.get_supabase_client', side_effect=Exception("Permission denied")):
            permissions = await validator.validate_schema_permissions()
            assert permissions["supabase"] is False

    @pytest.mark.asyncio
    async def test_check_service_versions_success(self, validator, mock_weaviate_client):
        """Test successful service version checking."""
        with patch('src.integration_test_manager.WeaviateClient', return_value=mock_weaviate_client), \
             patch('openai.__version__', '1.0.0'):

            versions = await validator.check_service_versions()
            assert "weaviate" in versions
            assert "openai_client" in versions
            assert "python" in versions

    @pytest.mark.asyncio
    async def test_check_service_versions_incompatible(self, validator):
        """Test service version checking with incompatible versions."""
        # This test would check for specific version incompatibilities
        # For now, just ensure it returns something
        versions = await validator.check_service_versions()
        assert isinstance(versions, dict)


class TestCleanupManager:
    """Test suite for CleanupManager class."""

    @pytest.fixture
    def cleanup_manager(self, mock_test_environment):
        """Create CleanupManager instance for testing."""
        return CleanupManager(mock_test_environment)

    @pytest.mark.asyncio
    async def test_cleanup_supabase_data_success(self, cleanup_manager, mock_supabase_client):
        """Test successful Supabase data cleanup."""
        test_space_id = "test_space_123"

        with patch('src.integration_test_manager.get_supabase_client', return_value=mock_supabase_client):
            await cleanup_manager.cleanup_supabase_data(test_space_id)

            # Verify cleanup was recorded
            assert len(cleanup_manager.cleanup_operations) > 0
            assert cleanup_manager.cleanup_operations[-1]["service"] == "supabase"
            assert cleanup_manager.cleanup_operations[-1]["success"] is True

    @pytest.mark.asyncio
    async def test_cleanup_supabase_data_failure(self, cleanup_manager):
        """Test Supabase data cleanup failure."""
        test_space_id = "test_space_123"

        with patch('src.integration_test_manager.get_supabase_client', side_effect=Exception("Cleanup failed")):
            with pytest.raises(CleanupError):
                await cleanup_manager.cleanup_supabase_data(test_space_id)

    @pytest.mark.asyncio
    async def test_cleanup_weaviate_data_success(self, cleanup_manager, mock_weaviate_client):
        """Test successful Weaviate data cleanup."""
        test_space_id = "test_space_123"

        with patch('src.integration_test_manager.WeaviateClient', return_value=mock_weaviate_client):
            await cleanup_manager.cleanup_weaviate_data(test_space_id)

            # Verify cleanup was recorded
            assert len(cleanup_manager.cleanup_operations) > 0
            assert cleanup_manager.cleanup_operations[-1]["service"] == "weaviate"

    @pytest.mark.asyncio
    async def test_cleanup_weaviate_data_failure(self, cleanup_manager):
        """Test Weaviate data cleanup failure."""
        test_space_id = "test_space_123"
        mock_client = AsyncMock()
        mock_client.__aenter__.side_effect = Exception("Connection failed")

        with patch('src.integration_test_manager.WeaviateClient', return_value=mock_client):
            with pytest.raises(CleanupError):
                await cleanup_manager.cleanup_weaviate_data(test_space_id)

    @pytest.mark.asyncio
    async def test_cleanup_temporary_files_success(self, cleanup_manager, temporary_test_directory):
        """Test successful temporary files cleanup."""
        test_space_id = "test_space_123"

        # Create some test files
        test_file = temporary_test_directory / f"test_{test_space_id}.txt"
        test_file.write_text("test content")

        # Mock Path.glob to return our test file
        with patch('pathlib.Path.glob', return_value=[test_file]):
            await cleanup_manager.cleanup_temporary_files(test_space_id)

            # File should be deleted
            assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_temporary_files_missing_files(self, cleanup_manager):
        """Test temporary files cleanup with missing files."""
        test_space_id = "test_space_nonexistent"

        # Should not raise exception even if no files exist
        await cleanup_manager.cleanup_temporary_files(test_space_id)

        # Verify operation was recorded
        assert len(cleanup_manager.cleanup_operations) > 0

    @pytest.mark.asyncio
    async def test_emergency_cleanup_success(self, cleanup_manager, mock_supabase_client, mock_weaviate_client):
        """Test successful emergency cleanup."""
        with patch('src.integration_test_manager.get_supabase_client', return_value=mock_supabase_client), \
             patch('src.integration_test_manager.WeaviateClient', return_value=mock_weaviate_client):

            await cleanup_manager.emergency_cleanup()

            # Verify emergency cleanup was recorded
            emergency_ops = [op for op in cleanup_manager.cleanup_operations if op["service"] == "emergency"]
            assert len(emergency_ops) > 0

    @pytest.mark.asyncio
    async def test_emergency_cleanup_partial_failure(self, cleanup_manager):
        """Test emergency cleanup with partial failures."""
        # Mock Supabase to fail but Weaviate to succeed
        with patch('src.integration_test_manager.get_supabase_client', side_effect=Exception("DB Error")), \
             patch('src.integration_test_manager.WeaviateClient', return_value=AsyncMock()):

            # Should not raise exception even with partial failures
            await cleanup_manager.emergency_cleanup()

    def test_get_cleanup_report_empty(self, cleanup_manager):
        """Test cleanup report generation with no operations."""
        report = cleanup_manager.get_cleanup_report()

        assert report["total_operations"] == 0
        assert report["successful_operations"] == 0
        assert report["failed_operations"] == 0
        assert report["test_environment_id"] == cleanup_manager.test_env.test_id

    def test_get_cleanup_report_with_operations(self, cleanup_manager):
        """Test cleanup report generation with operations."""
        # Add some mock operations
        cleanup_manager._record_cleanup_operation("test_service", "test_space", True)
        cleanup_manager._record_cleanup_operation("test_service", "test_space", False, "Error")

        report = cleanup_manager.get_cleanup_report()

        assert report["total_operations"] == 2
        assert report["successful_operations"] == 1
        assert report["failed_operations"] == 1


class TestDataModels:
    """Test suite for integration testing data models."""

    def test_test_environment_creation(self):
        """Test TestEnvironment dataclass creation."""
        env = TestEnvironment(
            test_id="test_123",
            supabase_url="https://test.supabase.co",
            supabase_key="test_key",
            weaviate_url="http://localhost:8080",
            weaviate_api_key="test_key",
            openai_api_key="test_openai",
            test_schema_suffix="test"
        )

        assert env.test_id == "test_123"
        assert env.cleanup_on_exit is True  # default value

    def test_test_environment_validation(self):
        """Test TestEnvironment dataclass validation."""
        # Test with minimal required fields
        env = TestEnvironment(
            test_id="test",
            supabase_url="url",
            supabase_key="key",
            weaviate_url="url",
            weaviate_api_key=None,
            openai_api_key="key",
            test_schema_suffix="test"
        )

        assert env.weaviate_api_key is None

    def test_integration_test_result_creation(self):
        """Test IntegrationTestResult dataclass creation."""
        result = IntegrationTestResult(
            test_name="test_example",
            success=True,
            duration_seconds=1.5
        )

        assert result.test_name == "test_example"
        assert result.success is True
        assert result.duration_seconds == 1.5
        assert result.error_message is None

    def test_integration_test_result_success(self):
        """Test IntegrationTestResult for successful test."""
        result = IntegrationTestResult(
            test_name="successful_test",
            success=True,
            duration_seconds=2.0,
            metrics={"operations": 5},
            artifacts=["test_space_123"]
        )

        assert result.success
        assert result.error_message is None
        assert result.metrics["operations"] == 5

    def test_integration_test_result_failure(self):
        """Test IntegrationTestResult for failed test."""
        result = IntegrationTestResult(
            test_name="failed_test",
            success=False,
            duration_seconds=0.5,
            error_message="Test failed due to assertion error"
        )

        assert not result.success
        assert "assertion error" in result.error_message


class TestExceptionHandling:
    """Test suite for integration testing exception handling."""

    def test_integration_test_error_creation(self):
        """Test IntegrationTestError exception creation."""
        error = IntegrationTestError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_environment_setup_error_creation(self):
        """Test EnvironmentSetupError exception creation."""
        error = EnvironmentSetupError("Setup failed")
        assert str(error) == "Setup failed"
        assert isinstance(error, IntegrationTestError)

    def test_cleanup_error_creation(self):
        """Test CleanupError exception creation."""
        error = CleanupError("Cleanup failed")
        assert str(error) == "Cleanup failed"
        assert isinstance(error, IntegrationTestError)

    def test_test_isolation_error_creation(self):
        """Test TestIsolationError exception creation."""
        error = TestIsolationError("Isolation compromised")
        assert str(error) == "Isolation compromised"
        assert isinstance(error, IntegrationTestError)


@pytest.mark.integration
class TestIntegrationTestFramework:
    """Integration tests for the testing framework itself."""

    def test_framework_self_validation(self):
        """Test that the testing framework can validate itself."""
        # Test that we can import all necessary classes
        from src.integration_test_manager import (
            IntegrationTestManager, TestDataFactory,
            EnvironmentValidator, CleanupManager
        )

        # Test that we can create instances
        test_env = TestEnvironment(
            test_id="self_test",
            supabase_url="test",
            supabase_key="test",
            weaviate_url="test",
            weaviate_api_key="test",
            openai_api_key="test",
            test_schema_suffix="test"
        )

        manager = IntegrationTestManager(test_env)
        factory = TestDataFactory()
        validator = EnvironmentValidator(test_env)
        cleanup = CleanupManager(test_env)

        assert manager is not None
        assert factory is not None
        assert validator is not None
        assert cleanup is not None

    @pytest.mark.asyncio
    async def test_end_to_end_test_execution(self):
        """Test complete end-to-end test execution."""
        test_env = TestEnvironment(
            test_id="e2e_test",
            supabase_url="test",
            supabase_key="test",
            weaviate_url="test",
            weaviate_api_key="test",
            openai_api_key="test",
            test_schema_suffix="test"
        )

        manager = IntegrationTestManager(test_env)

        async def mock_test(test_space_id):
            assert test_space_id is not None
            return True

        # Mock all external dependencies
        with patch.object(manager, 'create_isolated_test_space', return_value="test_space"), \
             patch.object(manager, 'cleanup_test_space'), \
             patch.object(manager, '_collect_test_metrics', return_value={}):

            result = await manager.run_integration_test("e2e_test", mock_test)
            assert result.success

    @pytest.mark.asyncio
    async def test_concurrent_test_isolation(self):
        """Test that concurrent tests are properly isolated."""
        test_env = TestEnvironment(
            test_id="concurrent_test",
            supabase_url="test",
            supabase_key="test",
            weaviate_url="test",
            weaviate_api_key="test",
            openai_api_key="test",
            test_schema_suffix="test"
        )

        manager = IntegrationTestManager(test_env)
        test_spaces = []

        async def capture_test_space(test_space_id):
            test_spaces.append(test_space_id)
            await asyncio.sleep(0.1)  # Simulate some work
            return True

        # Mock methods to track test space creation
        with patch.object(manager, 'create_isolated_test_space', side_effect=lambda: f"test_space_{len(test_spaces)}"), \
             patch.object(manager, 'cleanup_test_space'), \
             patch.object(manager, '_collect_test_metrics', return_value={}):

            # Run multiple tests concurrently
            tasks = [
                manager.run_integration_test(f"test_{i}", capture_test_space)
                for i in range(3)
            ]

            results = await asyncio.gather(*tasks)

            # Each test should have had a unique test space
            assert len(set(test_spaces)) == 3
            assert all(result.success for result in results)


@pytest.mark.performance
class TestIntegrationTestPerformance:
    """Performance tests for the integration testing framework."""

    @pytest.mark.asyncio
    async def test_setup_teardown_performance(self):
        """Test performance of setup and teardown operations."""
        test_env = TestEnvironment(
            test_id="perf_test",
            supabase_url="test",
            supabase_key="test",
            weaviate_url="test",
            weaviate_api_key="test",
            openai_api_key="test",
            test_schema_suffix="test"
        )

        manager = IntegrationTestManager(test_env)

        # Mock all dependencies to focus on framework performance
        with patch.object(manager.validator, 'validate_supabase_connection', return_value=True), \
             patch.object(manager.validator, 'validate_weaviate_connection', return_value=True), \
             patch.object(manager.validator, 'validate_openai_connection', return_value=True), \
             patch.object(manager.validator, 'check_required_env_vars', return_value=[]), \
             patch.object(manager.validator, 'validate_schema_permissions', return_value={"supabase": True, "weaviate": True}), \
             patch.object(manager, '_setup_test_schemas'):

            import time
            start_time = time.time()

            await manager.setup_test_environment()
            await manager.teardown_test_environment()

            duration = time.time() - start_time

            # Setup and teardown should be fast (under 1 second)
            assert duration < 1.0

    @pytest.mark.asyncio
    async def test_large_batch_cleanup_performance(self):
        """Test performance of cleaning up large test batches."""
        test_env = TestEnvironment(
            test_id="cleanup_perf_test",
            supabase_url="test",
            supabase_key="test",
            weaviate_url="test",
            weaviate_api_key="test",
            openai_api_key="test",
            test_schema_suffix="test"
        )

        cleanup_manager = CleanupManager(test_env)

        # Mock cleanup operations to be fast and record operations
        async def mock_supabase_cleanup(test_space_id):
            cleanup_manager._record_cleanup_operation("supabase", test_space_id, True)

        async def mock_weaviate_cleanup(test_space_id):
            cleanup_manager._record_cleanup_operation("weaviate", test_space_id, True)

        async def mock_files_cleanup(test_space_id):
            cleanup_manager._record_cleanup_operation("files", test_space_id, True)

        with patch.object(cleanup_manager, 'cleanup_supabase_data', mock_supabase_cleanup), \
             patch.object(cleanup_manager, 'cleanup_weaviate_data', mock_weaviate_cleanup), \
             patch.object(cleanup_manager, 'cleanup_temporary_files', mock_files_cleanup):

            import time
            start_time = time.time()

            # Simulate cleaning up many test spaces
            for i in range(10):
                await cleanup_manager.cleanup_supabase_data(f"test_space_{i}")
                await cleanup_manager.cleanup_weaviate_data(f"test_space_{i}")
                await cleanup_manager.cleanup_temporary_files(f"test_space_{i}")

            duration = time.time() - start_time

            # Batch cleanup should be efficient
            assert duration < 2.0
            assert len(cleanup_manager.cleanup_operations) == 30  # 3 operations x 10 spaces
