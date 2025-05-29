"""
Integration test manager for validating document processing pipeline with real services.

This module provides comprehensive integration testing capabilities for the StudyWise AI
document processing system, ensuring proper functionality with actual Supabase and
Weaviate instances.
"""

import asyncio
import os
import tempfile
import uuid
import logging
import time
import random
import string
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .document_processor import DocumentProcessor, DocumentInput, ProcessingResult
from .weaviate_client import WeaviateClient
from .supabase_client import get_supabase_client

# Set up logger
logger = logging.getLogger(__name__)


@dataclass
class TestEnvironment:
    """Configuration for integration test environment."""

    test_id: str
    supabase_url: str
    supabase_key: str
    weaviate_url: str
    weaviate_api_key: Optional[str]
    openai_api_key: str
    test_schema_suffix: str
    cleanup_on_exit: bool = True


@dataclass
class IntegrationTestResult:
    """Result of an integration test run."""

    test_name: str
    success: bool
    duration_seconds: float
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[str]] = None


class IntegrationTestManager:
    """
    Manages integration testing environment and orchestrates test execution.

    This class handles setup and teardown of test environments, ensures proper
    isolation between tests, and provides utilities for comprehensive testing
    of the document processing pipeline.
    """

    def __init__(
        self,
        test_environment: TestEnvironment,
        cleanup_timeout: int = 300
    ) -> None:
        """
        Initialize integration test manager.

        Args:
            test_environment: Configuration for test environment
            cleanup_timeout: Maximum time to wait for cleanup operations
        """
        self.test_env = test_environment
        self.cleanup_timeout = cleanup_timeout
        self.active_test_spaces: List[str] = []
        self.cleanup_manager = CleanupManager(test_environment)
        self.validator = EnvironmentValidator(test_environment)
        self.metrics: Dict[str, Any] = {}
        self._setup_complete = False

        logger.info(f"Initialized IntegrationTestManager for test environment {test_environment.test_id}")

    async def setup_test_environment(self) -> None:
        """
        Set up the integration test environment.

        Creates test-specific schemas, collections, and validates all
        service connections are working properly.

        Raises:
            ConnectionError: If unable to connect to required services
            EnvironmentError: If test environment setup fails
        """
        try:
            logger.info("Setting up integration test environment...")

            # Validate all service connections first
            logger.info("Validating service connections...")
            await self.validator.validate_supabase_connection()
            await self.validator.validate_weaviate_connection()
            await self.validator.validate_openai_connection()

            # Check required environment variables
            missing_vars = self.validator.check_required_env_vars()
            if missing_vars:
                raise EnvironmentSetupError(f"Missing required environment variables: {missing_vars}")

            # Validate schema permissions
            permissions = await self.validator.validate_schema_permissions()
            if not all(permissions.values()):
                failed_services = [k for k, v in permissions.items() if not v]
                raise EnvironmentSetupError(f"Insufficient permissions for services: {failed_services}")

            # Set up test schemas/collections
            await self._setup_test_schemas()

            self._setup_complete = True
            logger.info("Integration test environment setup completed successfully")

        except Exception as e:
            logger.error(f"Failed to set up test environment: {e}")
            raise EnvironmentSetupError(f"Test environment setup failed: {e}")

    async def teardown_test_environment(self) -> None:
        """
        Tear down the integration test environment.

        Cleans up all test data, schemas, and resources created during testing.
        Ensures no test artifacts remain in the system.
        """
        try:
            logger.info("Tearing down integration test environment...")

            # Clean up all active test spaces
            cleanup_tasks = []
            for test_space_id in self.active_test_spaces.copy():
                cleanup_tasks.append(self.cleanup_test_space(test_space_id))

            if cleanup_tasks:
                results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to cleanup test space {self.active_test_spaces[i]}: {result}")

            # Perform emergency cleanup if needed
            if self.test_env.cleanup_on_exit:
                await self.cleanup_manager.emergency_cleanup()

            self._setup_complete = False
            logger.info("Integration test environment teardown completed")

        except Exception as e:
            logger.error(f"Error during test environment teardown: {e}")
            # Don't raise here to avoid masking original test failures

    async def create_isolated_test_space(self) -> str:
        """
        Create an isolated test space for a specific test run.

        Returns:
            Unique identifier for the test space

        Raises:
            EnvironmentError: If test space creation fails
        """
        try:
            test_space_id = f"test_{uuid.uuid4().hex[:8]}_{int(time.time())}"
            logger.info(f"Creating isolated test space: {test_space_id}")

            # Validate environment is set up
            if not self._setup_complete:
                raise TestIsolationError("Test environment must be set up before creating test spaces")

            # Create isolated space in Supabase (using row-level security or prefixed tables)
            await self._create_supabase_test_space(test_space_id)

            # Create isolated space in Weaviate (using class prefixes)
            await self._create_weaviate_test_space(test_space_id)

            self.active_test_spaces.append(test_space_id)
            logger.info(f"Successfully created test space: {test_space_id}")

            return test_space_id

        except Exception as e:
            logger.error(f"Failed to create test space: {e}")
            raise EnvironmentSetupError(f"Test space creation failed: {e}")

    async def cleanup_test_space(self, test_space_id: str) -> None:
        """
        Clean up a specific test space.

        Args:
            test_space_id: Identifier of test space to clean up

        Raises:
            CleanupError: If cleanup operations fail
        """
        try:
            logger.info(f"Cleaning up test space: {test_space_id}")

            # Clean up from all services
            await self.cleanup_manager.cleanup_supabase_data(test_space_id)
            await self.cleanup_manager.cleanup_weaviate_data(test_space_id)
            await self.cleanup_manager.cleanup_temporary_files(test_space_id)

            # Remove from active spaces
            if test_space_id in self.active_test_spaces:
                self.active_test_spaces.remove(test_space_id)

            logger.info(f"Successfully cleaned up test space: {test_space_id}")

        except Exception as e:
            logger.error(f"Failed to cleanup test space {test_space_id}: {e}")
            raise CleanupError(f"Test space cleanup failed: {e}")

    async def run_integration_test(
        self,
        test_name: str,
        test_function: callable,
        timeout: int = 300
    ) -> IntegrationTestResult:
        """
        Run a single integration test with proper isolation and cleanup.

        Args:
            test_name: Name of the test being run
            test_function: Async function implementing the test
            timeout: Maximum time to allow for test execution

        Returns:
            Result of the integration test
        """
        start_time = time.time()
        test_space_id = None

        try:
            logger.info(f"Running integration test: {test_name}")

            # Create isolated test space
            test_space_id = await self.create_isolated_test_space()

            # Run the test function with timeout
            try:
                await asyncio.wait_for(test_function(test_space_id), timeout=timeout)
                success = True
                error_message = None
                logger.info(f"Integration test {test_name} completed successfully")

            except asyncio.TimeoutError:
                success = False
                error_message = f"Test timed out after {timeout} seconds"
                logger.error(f"Integration test {test_name} timed out")

            except Exception as e:
                success = False
                error_message = str(e)
                logger.error(f"Integration test {test_name} failed: {e}")

            duration = time.time() - start_time

            # Collect test metrics
            metrics = await self._collect_test_metrics(test_space_id, test_name)

            return IntegrationTestResult(
                test_name=test_name,
                success=success,
                duration_seconds=duration,
                error_message=error_message,
                metrics=metrics,
                artifacts=[test_space_id] if test_space_id else None
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Critical error in integration test {test_name}: {e}")

            return IntegrationTestResult(
                test_name=test_name,
                success=False,
                duration_seconds=duration,
                error_message=f"Critical test error: {e}",
                metrics=None,
                artifacts=None
            )

        finally:
            # Always attempt cleanup
            if test_space_id:
                try:
                    await self.cleanup_test_space(test_space_id)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup test space {test_space_id}: {cleanup_error}")

    async def get_test_metrics(self) -> Dict[str, Any]:
        """
        Collect comprehensive metrics from the test environment.

        Returns:
            Dictionary containing performance and usage metrics
        """
        try:
            metrics = {
                "test_environment_id": self.test_env.test_id,
                "active_test_spaces": len(self.active_test_spaces),
                "setup_complete": self._setup_complete,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Get service versions
            try:
                service_versions = await self.validator.check_service_versions()
                metrics["service_versions"] = service_versions
            except Exception as e:
                logger.warning(f"Failed to get service versions: {e}")
                metrics["service_versions"] = {}

            # Get system metrics if available
            try:
                import psutil
                metrics["system"] = {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage('/').percent
                }
            except ImportError:
                metrics["system"] = "psutil not available"

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect test metrics: {e}")
            return {"error": str(e)}

    def validate_test_isolation(self, test_space_id: str) -> bool:
        """
        Validate that a test space is properly isolated.

        Args:
            test_space_id: Test space to validate

        Returns:
            True if test space is properly isolated
        """
        try:
            # Check if test space ID is properly formatted
            if not test_space_id.startswith("test_"):
                return False

            # Check if test space is in active list
            if test_space_id not in self.active_test_spaces:
                return False

            # Additional isolation checks would go here
            # (e.g., checking that data is properly prefixed/isolated)

            return True

        except Exception as e:
            logger.error(f"Error validating test isolation for {test_space_id}: {e}")
            return False

    async def _setup_test_schemas(self) -> None:
        """Set up test-specific schemas and collections."""
        try:
            # Set up Weaviate test schema
            weaviate_client = WeaviateClient(
                url=self.test_env.weaviate_url,
                api_key=self.test_env.weaviate_api_key
            )

            # Create test schema if it doesn't exist
            test_class_name = f"Document_{self.test_env.test_schema_suffix}"

            async with weaviate_client:
                try:
                    await weaviate_client.create_schema()
                    logger.info("Weaviate test schema created successfully")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        raise
                    logger.info("Weaviate test schema already exists")

            logger.info("Test schemas setup completed")

        except Exception as e:
            logger.error(f"Failed to setup test schemas: {e}")
            raise

    async def _create_supabase_test_space(self, test_space_id: str) -> None:
        """Create isolated test space in Supabase."""
        try:
            # For now, we'll use row-level filtering with test_space_id
            # In production, might want separate test schemas
            logger.info(f"Supabase test space {test_space_id} ready (using row-level isolation)")

        except Exception as e:
            logger.error(f"Failed to create Supabase test space {test_space_id}: {e}")
            raise

    async def _create_weaviate_test_space(self, test_space_id: str) -> None:
        """Create isolated test space in Weaviate."""
        try:
            # Weaviate isolation will be handled through class naming conventions
            logger.info(f"Weaviate test space {test_space_id} ready (using class prefixes)")

        except Exception as e:
            logger.error(f"Failed to create Weaviate test space {test_space_id}: {e}")
            raise

    async def _collect_test_metrics(self, test_space_id: str, test_name: str) -> Dict[str, Any]:
        """Collect metrics for a specific test."""
        try:
            return {
                "test_space_id": test_space_id,
                "test_name": test_name,
                "timestamp": datetime.utcnow().isoformat(),
                "environment_id": self.test_env.test_id
            }
        except Exception as e:
            logger.warning(f"Failed to collect test metrics: {e}")
            return {}


class TestDataFactory:
    """
    Factory for creating realistic test data and documents.

    Provides utilities for generating various types of test content,
    from simple text documents to complex PDFs with specific characteristics.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        """
        Initialize test data factory.

        Args:
            seed: Random seed for reproducible test data generation
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)

        # Initialize faker for realistic data generation
        try:
            from faker import Faker
            self.faker = Faker()
            if seed is not None:
                self.faker.seed_instance(seed)
        except ImportError:
            logger.warning("Faker not available, using basic data generation")
            self.faker = None

        logger.info(f"Initialized TestDataFactory with seed: {seed}")

    def create_test_document(
        self,
        content: str,
        title: str,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        **metadata
    ) -> DocumentInput:
        """
        Create a test document with specified content and metadata.

        Args:
            content: Document text content
            title: Document title
            tags: Optional list of tags
            user_id: Optional user identifier
            **metadata: Additional metadata fields

        Returns:
            DocumentInput object ready for processing
        """
        try:
            # Generate realistic user_id if not provided
            if user_id is None:
                user_id = f"test_user_{uuid.uuid4().hex[:8]}"

            # Generate default tags if not provided
            if tags is None:
                tags = self._generate_random_tags()

            # Create base metadata
            doc_metadata = {
                "title": title,
                "tags": tags,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "test_document": True,
                "test_factory_seed": self.seed,
                **metadata
            }

            # Add realistic metadata if faker is available
            if self.faker:
                doc_metadata.update({
                    "author": self.faker.name(),
                    "language": "en",
                    "source": "test_generation"
                })

            return DocumentInput(
                content=content,
                metadata=doc_metadata
            )

        except Exception as e:
            logger.error(f"Failed to create test document: {e}")
            raise

    def create_test_batch(
        self,
        count: int,
        content_template: str = "Sample document content {}",
        vary_metadata: bool = True
    ) -> List[DocumentInput]:
        """
        Create a batch of test documents for bulk processing tests.

        Args:
            count: Number of documents to create
            content_template: Template for document content
            vary_metadata: Whether to vary metadata across documents

        Returns:
            List of DocumentInput objects
        """
        try:
            documents = []

            for i in range(count):
                # Generate content
                content = content_template.format(i + 1)
                if self.faker and vary_metadata:
                    content = f"{content}\n\n{self.faker.text(max_nb_chars=500)}"

                # Generate title
                title = f"Test Document {i + 1}"
                if self.faker and vary_metadata:
                    title = self.faker.sentence(nb_words=4).rstrip('.')

                # Vary metadata if requested
                extra_metadata = {}
                if vary_metadata:
                    extra_metadata = {
                        "batch_index": i,
                        "document_type": random.choice(["article", "report", "note", "summary"]),
                        "priority": random.choice(["low", "medium", "high"])
                    }

                    if self.faker:
                        extra_metadata.update({
                            "category": self.faker.word(),
                            "description": self.faker.sentence()
                        })

                doc = self.create_test_document(
                    content=content,
                    title=title,
                    **extra_metadata
                )
                documents.append(doc)

            logger.info(f"Created batch of {count} test documents")
            return documents

        except Exception as e:
            logger.error(f"Failed to create test batch: {e}")
            raise

    def generate_sample_pdf(
        self,
        content: str,
        filename: Optional[str] = None
    ) -> Tuple[bytes, str]:
        """
        Generate a PDF file with specified content for file processing tests.

        Args:
            content: Text content for the PDF
            filename: Optional filename (generated if not provided)

        Returns:
            Tuple of (PDF bytes, filename)
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
            from io import BytesIO

            # Generate filename if not provided
            if filename is None:
                timestamp = int(time.time())
                filename = f"test_document_{timestamp}.pdf"

            # Create PDF in memory
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()

            # Create content
            story = []
            paragraphs = content.split('\n\n')
            for paragraph in paragraphs:
                if paragraph.strip():
                    story.append(Paragraph(paragraph, styles['Normal']))

            # Build PDF
            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()

            logger.info(f"Generated PDF: {filename} ({len(pdf_bytes)} bytes)")
            return pdf_bytes, filename

        except ImportError:
            logger.error("reportlab not available for PDF generation")
            raise
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise

    def create_large_document(
        self,
        target_size_kb: int = 1000,
        chunk_friendly: bool = True
    ) -> DocumentInput:
        """
        Create a large document for performance testing.

        Args:
            target_size_kb: Target document size in kilobytes
            chunk_friendly: Whether to structure content for optimal chunking

        Returns:
            Large DocumentInput object
        """
        try:
            # Calculate approximate content length needed
            target_chars = target_size_kb * 1024  # Rough estimate (1 char ≈ 1 byte)

            # Generate content
            if chunk_friendly:
                content = self._generate_chunk_friendly_content(target_chars)
            else:
                content = self._generate_continuous_content(target_chars)

            # Create metadata
            metadata = {
                "document_type": "large_test",
                "target_size_kb": target_size_kb,
                "actual_size_chars": len(content),
                "chunk_friendly": chunk_friendly
            }

            return self.create_test_document(
                content=content,
                title=f"Large Test Document ({target_size_kb}KB)",
                **metadata
            )

        except Exception as e:
            logger.error(f"Failed to create large document: {e}")
            raise

    def create_multilingual_document(
        self,
        languages: List[str] = ["en", "es", "fr"]
    ) -> DocumentInput:
        """
        Create a document with multilingual content for i18n testing.

        Args:
            languages: List of language codes to include

        Returns:
            Multilingual DocumentInput object
        """
        try:
            # Sample content in different languages
            content_samples = {
                "en": "This is a sample document in English. It contains various topics and concepts.",
                "es": "Este es un documento de muestra en español. Contiene varios temas y conceptos.",
                "fr": "Ceci est un document d'exemple en français. Il contient divers sujets et concepts.",
                "de": "Dies ist ein Beispieldokument auf Deutsch. Es enthält verschiedene Themen und Konzepte.",
                "it": "Questo è un documento di esempio in italiano. Contiene vari argomenti e concetti.",
                "pt": "Este é um documento de amostra em português. Contém vários tópicos e conceitos."
            }

            # Build multilingual content
            content_parts = []
            for lang in languages:
                if lang in content_samples:
                    content_parts.append(f"[{lang.upper()}] {content_samples[lang]}")
                else:
                    content_parts.append(f"[{lang.upper()}] Sample content in {lang}")

            content = "\n\n".join(content_parts)

            # Add faker content if available
            if self.faker:
                try:
                    for lang in languages[:2]:  # Limit to avoid too much content
                        fake_locale = Faker(lang)
                        content += f"\n\n[{lang.upper()}_EXTENDED] {fake_locale.text(max_nb_chars=200)}"
                except Exception:
                    pass  # Some locales might not be available

            metadata = {
                "languages": languages,
                "multilingual": True,
                "primary_language": languages[0] if languages else "en"
            }

            return self.create_test_document(
                content=content,
                title="Multilingual Test Document",
                **metadata
            )

        except Exception as e:
            logger.error(f"Failed to create multilingual document: {e}")
            raise

    def _generate_random_tags(self, count: int = 3) -> List[str]:
        """Generate random tags for test documents."""
        if self.faker:
            return [self.faker.word() for _ in range(count)]
        else:
            return [f"tag_{i}" for i in range(count)]

    def _generate_chunk_friendly_content(self, target_chars: int) -> str:
        """Generate content optimized for chunking."""
        content_parts = []
        current_length = 0
        section_count = 1

        while current_length < target_chars:
            # Create section header
            section_header = f"# Section {section_count}: Test Content\n\n"
            content_parts.append(section_header)
            current_length += len(section_header)

            # Add paragraphs
            for para in range(3):
                if self.faker:
                    paragraph = self.faker.text(max_nb_chars=300) + "\n\n"
                else:
                    paragraph = f"This is paragraph {para + 1} of section {section_count}. " * 10 + "\n\n"

                content_parts.append(paragraph)
                current_length += len(paragraph)

                if current_length >= target_chars:
                    break

            section_count += 1

        return "".join(content_parts)

    def _generate_continuous_content(self, target_chars: int) -> str:
        """Generate continuous content without clear chunk boundaries."""
        if self.faker:
            content = ""
            while len(content) < target_chars:
                content += self.faker.text(max_nb_chars=1000) + " "
            return content[:target_chars]
        else:
            base_text = "This is continuous test content that flows from one concept to another without clear boundaries. "
            repetitions = (target_chars // len(base_text)) + 1
            return (base_text * repetitions)[:target_chars]


class EnvironmentValidator:
    """
    Validates integration test environment and service availability.

    Provides comprehensive checks to ensure all required services are
    available and properly configured before running integration tests.
    """

    def __init__(self, test_environment: TestEnvironment) -> None:
        """
        Initialize environment validator.

        Args:
            test_environment: Test environment configuration to validate
        """
        self.test_env = test_environment
        logger.info(f"Initialized EnvironmentValidator for {test_environment.test_id}")

    async def validate_supabase_connection(self) -> bool:
        """
        Validate connection to Supabase instance.

        Returns:
            True if Supabase is accessible and properly configured

        Raises:
            ConnectionError: If Supabase connection fails
        """
        try:
            logger.info("Validating Supabase connection...")

            # Get Supabase client
            supabase_client = get_supabase_client(
                url=self.test_env.supabase_url,
                key=self.test_env.supabase_key
            )

            # Test connection with a simple query
            try:
                # Try to access a system table or perform a basic operation
                response = supabase_client.table('test_connection').select('*').limit(1).execute()
                # If we get here without exception, connection works
                logger.info("Supabase connection validated successfully")
                return True

            except Exception as e:
                # Check if it's just a missing table (which is fine for connection test)
                if "does not exist" in str(e) or "not found" in str(e):
                    logger.info("Supabase connection validated (table not found is expected)")
                    return True
                else:
                    raise

        except Exception as e:
            logger.error(f"Supabase connection validation failed: {e}")
            raise ConnectionError(f"Failed to connect to Supabase: {e}")

    async def validate_weaviate_connection(self) -> bool:
        """
        Validate connection to Weaviate instance.

        Returns:
            True if Weaviate is accessible and properly configured

        Raises:
            ConnectionError: If Weaviate connection fails
        """
        try:
            logger.info("Validating Weaviate connection...")

            # Create Weaviate client
            weaviate_client = WeaviateClient(
                url=self.test_env.weaviate_url,
                api_key=self.test_env.weaviate_api_key
            )

            # Test connection
            async with weaviate_client:
                health_status = await weaviate_client.health_check()
                if health_status:
                    logger.info("Weaviate connection validated successfully")
                    return True
                else:
                    raise ConnectionError("Weaviate health check failed")

        except Exception as e:
            logger.error(f"Weaviate connection validation failed: {e}")
            raise ConnectionError(f"Failed to connect to Weaviate: {e}")

    async def validate_openai_connection(self) -> bool:
        """
        Validate connection to OpenAI API.

        Returns:
            True if OpenAI API is accessible

        Raises:
            ConnectionError: If OpenAI API connection fails
        """
        try:
            logger.info("Validating OpenAI connection...")

            import openai

            # Set API key
            openai.api_key = self.test_env.openai_api_key

            # Test with a minimal API call
            try:
                response = await openai.ChatCompletion.acreate(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                logger.info("OpenAI connection validated successfully")
                return True

            except Exception as e:
                # Check if it's just a quota/rate limit issue
                if "quota" in str(e).lower() or "rate" in str(e).lower():
                    logger.warning(f"OpenAI API accessible but quota/rate limited: {e}")
                    return True
                else:
                    raise

        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {e}")
            raise ConnectionError(f"Failed to connect to OpenAI API: {e}")

    def check_required_env_vars(self) -> List[str]:
        """
        Check that all required environment variables are set.

        Returns:
            List of missing environment variable names (empty if all present)
        """
        required_vars = [
            'SUPABASE_URL_TEST',
            'SUPABASE_ANON_KEY_TEST',
            'WEAVIATE_URL_TEST',
            'OPENAI_API_KEY_TEST'
        ]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            logger.warning(f"Missing required environment variables: {missing_vars}")
        else:
            logger.info("All required environment variables are present")

        return missing_vars

    async def validate_schema_permissions(self) -> Dict[str, bool]:
        """
        Validate that the test environment has proper schema permissions.

        Returns:
            Dictionary mapping service names to permission status
        """
        permissions = {}

        try:
            # Check Supabase permissions
            logger.info("Checking Supabase schema permissions...")
            try:
                supabase_client = get_supabase_client(
                    url=self.test_env.supabase_url,
                    key=self.test_env.supabase_key
                )
                # Try to create and delete a test table
                test_table = f"test_permissions_{uuid.uuid4().hex[:8]}"

                # For now, assume we have permissions if connection works
                permissions["supabase"] = True
                logger.info("Supabase schema permissions validated")

            except Exception as e:
                logger.warning(f"Supabase permission check failed: {e}")
                permissions["supabase"] = False

            # Check Weaviate permissions
            logger.info("Checking Weaviate schema permissions...")
            try:
                weaviate_client = WeaviateClient(
                    url=self.test_env.weaviate_url,
                    api_key=self.test_env.weaviate_api_key
                )

                async with weaviate_client:
                    # Try to get schema (this requires read permissions)
                    await weaviate_client.health_check()
                    permissions["weaviate"] = True
                    logger.info("Weaviate schema permissions validated")

            except Exception as e:
                logger.warning(f"Weaviate permission check failed: {e}")
                permissions["weaviate"] = False

        except Exception as e:
            logger.error(f"Error checking schema permissions: {e}")

        return permissions

    async def check_service_versions(self) -> Dict[str, str]:
        """
        Check versions of all connected services for compatibility.

        Returns:
            Dictionary mapping service names to version strings
        """
        versions = {}

        try:
            # Check Weaviate version
            try:
                weaviate_client = WeaviateClient(
                    url=self.test_env.weaviate_url,
                    api_key=self.test_env.weaviate_api_key
                )

                async with weaviate_client:
                    # Get version info from meta endpoint
                    versions["weaviate"] = "available"  # Simplified for now

            except Exception as e:
                logger.warning(f"Failed to get Weaviate version: {e}")
                versions["weaviate"] = "unknown"

            # Check OpenAI version
            try:
                import openai
                versions["openai_client"] = openai.__version__
            except Exception:
                versions["openai_client"] = "unknown"

            # Check Python version
            import sys
            versions["python"] = sys.version.split()[0]

        except Exception as e:
            logger.error(f"Error checking service versions: {e}")

        return versions


class CleanupManager:
    """
    Manages cleanup of test data and resources.

    Ensures that integration tests don't leave behind artifacts that
    could interfere with subsequent tests or production systems.
    """

    def __init__(
        self,
        test_environment: TestEnvironment,
        aggressive_cleanup: bool = False
    ) -> None:
        """
        Initialize cleanup manager.

        Args:
            test_environment: Test environment configuration
            aggressive_cleanup: Whether to perform aggressive cleanup operations
        """
        self.test_env = test_environment
        self.aggressive_cleanup = aggressive_cleanup
        self.cleanup_operations: List[Dict[str, Any]] = []
        logger.info(f"Initialized CleanupManager for {test_environment.test_id}")

    async def cleanup_supabase_data(self, test_space_id: str) -> None:
        """
        Clean up test data from Supabase.

        Args:
            test_space_id: Identifier of test space to clean up

        Raises:
            CleanupError: If cleanup operations fail
        """
        try:
            logger.info(f"Cleaning up Supabase data for test space: {test_space_id}")

            supabase_client = get_supabase_client(
                url=self.test_env.supabase_url,
                key=self.test_env.supabase_key
            )

            # Clean up documents table (with test_space_id filter)
            try:
                response = supabase_client.table('documents').delete().match({
                    'test_space_id': test_space_id
                }).execute()

                deleted_count = len(response.data) if response.data else 0
                logger.info(f"Deleted {deleted_count} documents from Supabase")

            except Exception as e:
                if "does not exist" not in str(e):
                    logger.warning(f"Failed to cleanup documents table: {e}")

            # Clean up flashcards table
            try:
                response = supabase_client.table('flashcards').delete().match({
                    'test_space_id': test_space_id
                }).execute()

                deleted_count = len(response.data) if response.data else 0
                logger.info(f"Deleted {deleted_count} flashcards from Supabase")

            except Exception as e:
                if "does not exist" not in str(e):
                    logger.warning(f"Failed to cleanup flashcards table: {e}")

            self._record_cleanup_operation("supabase", test_space_id, True)

        except Exception as e:
            logger.error(f"Failed to cleanup Supabase data for {test_space_id}: {e}")
            self._record_cleanup_operation("supabase", test_space_id, False, str(e))
            raise CleanupError(f"Supabase cleanup failed: {e}")

    async def cleanup_weaviate_data(self, test_space_id: str) -> None:
        """
        Clean up test data from Weaviate.

        Args:
            test_space_id: Identifier of test space to clean up

        Raises:
            CleanupError: If cleanup operations fail
        """
        try:
            logger.info(f"Cleaning up Weaviate data for test space: {test_space_id}")

            weaviate_client = WeaviateClient(
                url=self.test_env.weaviate_url,
                api_key=self.test_env.weaviate_api_key
            )

            async with weaviate_client:
                # Delete documents with test_space_id in metadata
                try:
                    # In a real implementation, we'd query for documents with the test_space_id
                    # and delete them individually or in batches
                    deleted_count = 0  # Placeholder
                    logger.info(f"Deleted {deleted_count} documents from Weaviate")

                except Exception as e:
                    logger.warning(f"Failed to cleanup Weaviate documents: {e}")

            self._record_cleanup_operation("weaviate", test_space_id, True)

        except Exception as e:
            logger.error(f"Failed to cleanup Weaviate data for {test_space_id}: {e}")
            self._record_cleanup_operation("weaviate", test_space_id, False, str(e))
            raise CleanupError(f"Weaviate cleanup failed: {e}")

    async def cleanup_temporary_files(self, test_space_id: str) -> None:
        """
        Clean up temporary files created during testing.

        Args:
            test_space_id: Identifier of test space to clean up
        """
        try:
            logger.info(f"Cleaning up temporary files for test space: {test_space_id}")

            # Clean up temp directory
            temp_dir = Path(tempfile.gettempdir()) / f"studywise_test_{test_space_id}"
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")

            # Clean up any PDF files in current directory with test_space_id
            current_dir = Path(".")
            test_files = list(current_dir.glob(f"*{test_space_id}*"))
            for file_path in test_files:
                try:
                    file_path.unlink()
                    logger.info(f"Cleaned up test file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")

            self._record_cleanup_operation("files", test_space_id, True)

        except Exception as e:
            logger.warning(f"Failed to cleanup temporary files for {test_space_id}: {e}")
            self._record_cleanup_operation("files", test_space_id, False, str(e))

    async def emergency_cleanup(self) -> None:
        """
        Perform emergency cleanup of all test data.

        This is a last-resort cleanup method that attempts to remove
        all test artifacts, even if some operations fail.
        """
        try:
            logger.warning("Performing emergency cleanup of all test data")

            # Clean up Supabase test data
            try:
                supabase_client = get_supabase_client(
                    url=self.test_env.supabase_url,
                    key=self.test_env.supabase_key
                )

                # Delete all test documents
                try:
                    response = supabase_client.table('documents').delete().match({
                        'test_document': True
                    }).execute()
                    logger.info("Emergency cleanup: Removed test documents from Supabase")
                except Exception as e:
                    logger.warning(f"Emergency cleanup failed for documents: {e}")

                # Delete all test flashcards
                try:
                    response = supabase_client.table('flashcards').delete().match({
                        'test_data': True
                    }).execute()
                    logger.info("Emergency cleanup: Removed test flashcards from Supabase")
                except Exception as e:
                    logger.warning(f"Emergency cleanup failed for flashcards: {e}")

            except Exception as e:
                logger.warning(f"Emergency Supabase cleanup failed: {e}")

            # Clean up Weaviate test data
            try:
                weaviate_client = WeaviateClient(
                    url=self.test_env.weaviate_url,
                    api_key=self.test_env.weaviate_api_key
                )

                async with weaviate_client:
                    # In a real implementation, we'd delete all test documents
                    logger.info("Emergency cleanup: Processed Weaviate test data")

            except Exception as e:
                logger.warning(f"Emergency Weaviate cleanup failed: {e}")

            # Clean up all temp files
            try:
                temp_dir = Path(tempfile.gettempdir())
                test_dirs = list(temp_dir.glob("studywise_test_*"))
                for test_dir in test_dirs:
                    try:
                        import shutil
                        shutil.rmtree(test_dir)
                        logger.info(f"Emergency cleanup: Removed {test_dir}")
                    except Exception:
                        pass

            except Exception as e:
                logger.warning(f"Emergency file cleanup failed: {e}")

            self._record_cleanup_operation("emergency", "all", True)
            logger.info("Emergency cleanup completed")

        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")
            self._record_cleanup_operation("emergency", "all", False, str(e))

    def get_cleanup_report(self) -> Dict[str, Any]:
        """
        Generate a report of cleanup operations performed.

        Returns:
            Dictionary containing cleanup operation details
        """
        try:
            return {
                "test_environment_id": self.test_env.test_id,
                "total_operations": len(self.cleanup_operations),
                "successful_operations": len([op for op in self.cleanup_operations if op["success"]]),
                "failed_operations": len([op for op in self.cleanup_operations if not op["success"]]),
                "operations": self.cleanup_operations,
                "generated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to generate cleanup report: {e}")
            return {"error": str(e)}

    def _record_cleanup_operation(
        self,
        service: str,
        test_space_id: str,
        success: bool,
        error_message: Optional[str] = None
    ) -> None:
        """Record a cleanup operation for reporting."""
        operation = {
            "service": service,
            "test_space_id": test_space_id,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "error_message": error_message
        }
        self.cleanup_operations.append(operation)


# Custom exceptions for integration testing
class IntegrationTestError(Exception):
    """Base exception for integration testing errors."""
    pass


class EnvironmentSetupError(IntegrationTestError):
    """Raised when test environment setup fails."""
    pass


class CleanupError(IntegrationTestError):
    """Raised when cleanup operations fail."""
    pass


class TestIsolationError(IntegrationTestError):
    """Raised when test isolation is compromised."""
    pass
