# Integration Testing Guide

This guide covers setting up and running integration tests for the StudyWise AI document processing pipeline using real Supabase and Weaviate instances.

## Overview

The integration testing framework validates the complete document processing pipeline from end-to-end, including:

- Document processing and chunking
- Vector embedding generation and storage
- Flashcard generation
- Cross-system data synchronization
- Search functionality
- Error recovery mechanisms
- Performance characteristics

## Prerequisites

### Required Services

1. **Supabase Test Instance**
   - Separate Supabase project for testing
   - Database with appropriate schemas
   - Service role key for full access

2. **Weaviate Test Instance**
   - Local Weaviate instance (Docker recommended)
   - Or cloud Weaviate cluster for testing
   - API key if authentication is enabled

3. **OpenAI API Access**
   - Test API key with appropriate quotas
   - Consider using a separate key with lower limits for testing

### Environment Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   ```bash
   # Copy the example environment file
   cp env.test.example .env.test

   # Edit .env.test with your test service credentials
   nano .env.test
   ```

3. **Start Local Weaviate (if using Docker)**
   ```bash
   docker run -d \
     --name weaviate-test \
     -p 8080:8080 \
     -e QUERY_DEFAULTS_LIMIT=25 \
     -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
     -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
     -e DEFAULT_VECTORIZER_MODULE='none' \
     -e ENABLE_MODULES='' \
     -e CLUSTER_HOSTNAME='node1' \
     semitechnologies/weaviate:1.21.3
   ```

## Configuration

### Environment Variables

Required variables in `.env.test`:

```bash
# Test Environment
INTEGRATION_TEST_ENV=local_test

# Supabase Test Instance
SUPABASE_URL_TEST=https://your-test-project.supabase.co
SUPABASE_ANON_KEY_TEST=your_test_anon_key
SUPABASE_SERVICE_ROLE_KEY_TEST=your_test_service_role_key

# Weaviate Test Instance
WEAVIATE_URL_TEST=http://localhost:8080
WEAVIATE_API_KEY_TEST=your_test_api_key_if_needed

# OpenAI Test Configuration
OPENAI_API_KEY_TEST=your_test_openai_key

# Test Configuration
TEST_DOCUMENT_BATCH_SIZE=5
TEST_CLEANUP_ON_EXIT=true
```

### Safety Features

The integration testing framework includes several safety features:

- **Environment Isolation**: Tests only run against designated test environments
- **Automatic Cleanup**: Test data is automatically cleaned up after tests
- **Schema Isolation**: Test schemas are separate from production
- **Data Validation**: Prevents accidental production data access

## Running Tests

### Basic Usage

```bash
# Run all integration tests
pytest tests/integration_tests.py -m integration

# Run integration tests excluding performance tests
pytest tests/integration_tests.py -m "integration and not performance"

# Run only performance tests
pytest tests/integration_tests.py -m "integration and performance"

# Run specific test class
pytest tests/integration_tests.py::TestDocumentProcessingPipeline -m integration
```

### Parallel Execution

```bash
# Run tests in parallel (careful with shared resources)
pytest tests/integration_tests.py -m integration -n auto

# Run with specific number of workers
pytest tests/integration_tests.py -m integration -n 4
```

### Verbose Output

```bash
# Run with detailed output
pytest tests/integration_tests.py -m integration -v -s

# Run with logging output
pytest tests/integration_tests.py -m integration -v -s --log-cli-level=INFO
```

## Test Categories

### Service Connectivity Tests
- Validate connections to all external services
- Check authentication and permissions
- Verify service versions and compatibility

### Document Processing Pipeline Tests
- End-to-end document processing
- Batch processing functionality
- PDF and various file format support
- Chunking and embedding generation
- Flashcard generation

### Data Consistency Tests
- Cross-system data synchronization
- Metadata consistency between Supabase and Weaviate
- Vector embedding storage validation
- Cascade deletion verification

### Search Functionality Tests
- Semantic search with real embeddings
- Hybrid search capabilities
- Search with metadata filters
- Relevance scoring accuracy

### Error Handling Tests
- Service connection failure recovery
- API rate limiting handling
- Partial processing failure recovery
- Data corruption scenarios

### Performance Tests
- Document processing benchmarks
- Search performance metrics
- Concurrent processing capabilities
- Large document handling
- Memory usage profiling

## Development Workflow

### Adding New Integration Tests

1. **Create Test Function**
   ```python
   @pytest.mark.integration
   @pytest.mark.asyncio
   async def test_new_functionality(integration_test_manager, test_data_factory):
       """Test description."""
       # Test implementation
       pass
   ```

2. **Use Test Fixtures**
   - `integration_test_manager`: Main test orchestration
   - `test_data_factory`: Generate test documents
   - `test_environment`: Environment configuration

3. **Follow Test Isolation**
   - Each test should be independent
   - Use unique test spaces
   - Clean up test data

### Best Practices

1. **Test Data Management**
   - Use the TestDataFactory for consistent test data
   - Generate realistic document content
   - Vary metadata to test different scenarios

2. **Error Handling**
   - Test both success and failure scenarios
   - Validate error messages and recovery
   - Use appropriate timeouts

3. **Performance Considerations**
   - Monitor test execution time
   - Use smaller datasets for regular tests
   - Separate performance tests from functional tests

4. **Resource Management**
   - Clean up resources in finally blocks
   - Use context managers where possible
   - Monitor memory usage in long-running tests

## Troubleshooting

### Common Issues

1. **Connection Failures**
   ```bash
   # Check service availability
   curl http://localhost:8080/v1/meta

   # Verify environment variables
   python -c "import os; print(os.getenv('SUPABASE_URL_TEST'))"
   ```

2. **Authentication Errors**
   - Verify API keys are correct
   - Check service role permissions
   - Ensure test environment has proper access

3. **Test Data Cleanup Issues**
   - Run emergency cleanup manually
   - Check for orphaned test data
   - Verify cleanup permissions

4. **Performance Test Failures**
   - Check system resources
   - Verify network connectivity
   - Adjust timeout values

### Debugging

```bash
# Run single test with full debugging
pytest tests/integration_tests.py::TestDocumentProcessingPipeline::test_single_document_processing -m integration -v -s --pdb

# Check test environment setup
python -c "from src.integration_test_manager import EnvironmentValidator; import asyncio; asyncio.run(EnvironmentValidator().validate_all())"
```

## Monitoring and Reporting

### Test Metrics

The integration tests collect various metrics:

- Processing time per document
- Memory usage during operations
- API call counts and latencies
- Search accuracy metrics
- System resource utilization

### Performance Reports

Generate performance reports:

```bash
# Run performance tests with reporting
pytest tests/integration_tests.py -m "integration and performance" --benchmark-json=performance_report.json
```

### Continuous Integration

For CI/CD pipelines:

```bash
# Run tests with JUnit XML output
pytest tests/integration_tests.py -m integration --junitxml=integration_test_results.xml

# Generate coverage report
pytest tests/integration_tests.py -m integration --cov=src --cov-report=xml
```

## Safety and Cleanup

### Automatic Cleanup

The framework automatically cleans up:
- Test documents and metadata
- Vector embeddings
- Temporary files
- Test schemas and collections

### Manual Cleanup

If needed, run manual cleanup:

```python
from src.integration_test_manager import CleanupManager, TestEnvironment

# Emergency cleanup
cleanup_manager = CleanupManager(test_env)
await cleanup_manager.emergency_cleanup()
```

### Data Protection

- Tests never access production data
- All test data is clearly marked
- Automatic safety checks prevent mistakes
- Regular cleanup prevents data accumulation

## Contributing

When adding integration tests:

1. Follow the existing test structure
2. Add appropriate test marks (`@pytest.mark.integration`)
3. Include both positive and negative test cases
4. Document any new test requirements
5. Update this README if needed

For questions or issues, please refer to the main project documentation or create an issue.
