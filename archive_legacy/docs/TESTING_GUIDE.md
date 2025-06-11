# Testing Guide for StudyWise AI Integration Framework

This guide provides comprehensive instructions for testing the StudyWise AI document processing pipeline, including both unit tests and real integration tests with actual services.

## Overview

The testing framework consists of multiple layers:

- **Unit Tests**: Test individual components in isolation using mocks
- **Integration Tests**: Test complete workflows with real Supabase/Weaviate instances
- **Performance Tests**: Measure system performance under various conditions
- **Framework Tests**: Validate the testing infrastructure itself

## Quick Start

### 1. Test the Integration Framework (No Services Required)

```bash
# Test the integration testing framework itself
python run_integration_tests.py --unit-only
```

This runs 64 comprehensive unit tests that validate all integration testing components without requiring real services.

### 2. Check Environment for Real Integration Tests

```bash
# Check if environment is configured for integration testing
python run_integration_tests.py --check-env
```

### 3. Run All Project Tests

```bash
# Run all tests in the project (185 tests total)
python run_integration_tests.py --all
```

## Test Categories

### Unit Tests (64 tests)

Tests the integration testing framework components in isolation:

```bash
# Run unit tests for integration framework
pytest tests/test_integration_test_manager.py -v

# Or use the test runner
python run_integration_tests.py --unit-only
```

**Test Coverage:**
- ✅ IntegrationTestManager (15 tests)
- ✅ TestDataFactory (15 tests)
- ✅ EnvironmentValidator (12 tests)
- ✅ CleanupManager (10 tests)
- ✅ Data Models (5 tests)
- ✅ Exception Handling (4 tests)
- ✅ Framework Self-Validation (3 tests)

### Integration Tests (15 tests)

Tests complete workflows with real services:

```bash
# Run integration tests (requires service configuration)
pytest tests/integration_tests.py -m integration -v

# Or use the test runner
python run_integration_tests.py --integration-only
```

**Test Categories:**
- 🔗 **Service Connectivity** (4 tests): Supabase, Weaviate, OpenAI connection validation
- 📄 **Document Processing Pipeline** (5 tests): End-to-end document processing workflows
- 🔄 **Data Consistency** (1 test): Cross-system data synchronization validation
- 🔍 **Search Functionality** (1 test): Semantic search with real embeddings
- ⚠️ **Error Handling** (1 test): Recovery from various failure scenarios
- 🏠 **Data Isolation** (2 tests): Test space isolation and cleanup effectiveness
- ⚡ **Performance Metrics** (1 test): Performance measurement and validation

### Performance Tests

```bash
# Run performance tests
pytest tests/integration_tests.py -m "integration and performance" -v

# Or use the test runner
python run_integration_tests.py --performance
```

### Specific Test Classes

```bash
# Test service connectivity only
python run_integration_tests.py --connectivity

# Test document processing pipeline only
python run_integration_tests.py --pipeline

# Test specific class
python run_integration_tests.py --class TestServiceConnectivity
```

## Setting Up Real Integration Tests

### 1. Environment Configuration

Create `.env.test` from the template:

```bash
cp env.test.example .env.test
```

Edit `.env.test` with your test service credentials:

```bash
# Test Environment
INTEGRATION_TEST_ENV=local_test

# Supabase Test Instance
SUPABASE_URL_TEST=https://your-test-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY_TEST=your_test_service_role_key

# Weaviate Test Instance
WEAVIATE_URL_TEST=http://localhost:8080
WEAVIATE_API_KEY_TEST=your_test_api_key_if_needed

# OpenAI Test Configuration
OPENAI_API_KEY_TEST=your_test_openai_key
```

### 2. Service Setup

**Supabase Test Instance:**
1. Create a separate Supabase project for testing
2. Set up the database schema (documents, flashcards tables)
3. Get the service role key for full access

**Weaviate Test Instance:**
```bash
# Start local Weaviate with Docker
docker run -d \
  --name weaviate-test \
  -p 8080:8080 \
  -e QUERY_DEFAULTS_LIMIT=25 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  semitechnologies/weaviate:1.21.3
```

**OpenAI API:**
- Use a test API key with appropriate quotas
- Consider lower rate limits for testing

### 3. Environment Validation

```bash
# Validate environment setup
python run_integration_tests.py --check-env
```

Should show all green checkmarks:
```
🔍 Environment Check Results:
==================================================
✅ Env File Exists: True
✅ Integration Test Env: True
✅ Supabase Url: True
✅ Supabase Key: True
✅ Weaviate Url: True
✅ Openai Key: True
✅ Python Packages: True

✅ Environment is ready for integration testing!
```

## Test Commands Reference

### Basic Commands

```bash
# Test runner help
python run_integration_tests.py --help

# Check environment only
python run_integration_tests.py --check-env

# Unit tests only (no services required)
python run_integration_tests.py --unit-only

# Integration tests only (requires services)
python run_integration_tests.py --integration-only

# All tests in project
python run_integration_tests.py --all
```

### Direct pytest Commands

```bash
# All integration framework unit tests
pytest tests/test_integration_test_manager.py -v

# All integration tests with real services
pytest tests/integration_tests.py -m integration -v

# Integration tests excluding performance
pytest tests/integration_tests.py -m "integration and not performance" -v

# Performance tests only
pytest tests/integration_tests.py -m "integration and performance" -v

# All project tests
pytest tests/ -v

# Specific test class
pytest tests/integration_tests.py::TestServiceConnectivity -v

# Specific test method
pytest tests/integration_tests.py::TestServiceConnectivity::test_supabase_connection -v
```

### Advanced Options

```bash
# Run tests in parallel
pytest tests/ -n auto

# Generate coverage report
pytest tests/ --cov=src --cov-report=html

# Run with specific log level
pytest tests/ --log-cli-level=INFO -s

# Run tests with JUnit XML output (for CI)
pytest tests/ --junitxml=test_results.xml
```

## Test Results Interpretation

### Unit Test Results

```
64 passed, 2 skipped, 3 warnings
```

- **64 passed**: All unit tests for integration framework working
- **2 skipped**: PDF tests skipped (reportlab not installed)
- **3 warnings**: Minor deprecation warnings (safe to ignore)

### Integration Test Results

When services are not configured, tests are automatically skipped:

```
15 skipped - Integration tests require INTEGRATION_TEST_ENV to be set
```

With proper configuration, you should see:

```
15 passed - All integration tests completed successfully
```

### Complete Project Test Results

```
185 passed, 2 skipped, 3 warnings
```

- **185 passed**: All tests across the entire project
- **Document Processor**: 64 tests
- **Weaviate Client**: 57 tests
- **Integration Framework**: 64 tests

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables Missing**
   ```bash
   # Check current environment
   python run_integration_tests.py --check-env

   # Copy and edit template
   cp env.test.example .env.test
   ```

3. **Service Connection Failures**
   ```bash
   # Test connectivity individually
   python run_integration_tests.py --connectivity
   ```

4. **Permission Issues**
   - Verify Supabase service role key has full permissions
   - Check Weaviate authentication settings
   - Validate OpenAI API key quotas

### Debug Mode

```bash
# Run with verbose output and logging
pytest tests/integration_tests.py -v -s --log-cli-level=INFO

# Run single test with debug info
pytest tests/integration_tests.py::TestServiceConnectivity::test_supabase_connection -v -s --pdb
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python run_integration_tests.py --unit-only

  integration-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    env:
      INTEGRATION_TEST_ENV: github_actions
      SUPABASE_URL_TEST: ${{ secrets.SUPABASE_URL_TEST }}
      SUPABASE_SERVICE_ROLE_KEY_TEST: ${{ secrets.SUPABASE_KEY_TEST }}
      WEAVIATE_URL_TEST: http://localhost:8080
      OPENAI_API_KEY_TEST: ${{ secrets.OPENAI_API_KEY_TEST }}
    services:
      weaviate:
        image: semitechnologies/weaviate:1.21.3
        ports:
          - 8080:8080
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python run_integration_tests.py --integration-only
```

## Test Development

### Adding New Unit Tests

1. Add test methods to appropriate test class in `tests/test_integration_test_manager.py`
2. Follow existing patterns with fixtures and mocking
3. Run tests: `pytest tests/test_integration_test_manager.py::YourTestClass -v`

### Adding New Integration Tests

1. Add test methods to appropriate test class in `tests/integration_tests.py`
2. Use `@pytest.mark.integration` decorator
3. Use `integration_test_manager.run_integration_test()` for test execution
4. Run tests: `pytest tests/integration_tests.py::YourTestClass -m integration -v`

### Test Data Generation

```python
# Use TestDataFactory for consistent test data
factory = TestDataFactory(seed=42)
doc = factory.create_test_document("content", "title")
batch = factory.create_test_batch(5)
large_doc = factory.create_large_document(target_size_kb=100)
multilingual_doc = factory.create_multilingual_document(["en", "es"])
```

## Performance Benchmarks

Expected performance characteristics:

- **Document Processing**: > 0.1 docs/second
- **Test Environment Setup**: < 5 seconds
- **Test Space Creation**: < 1 second
- **Cleanup Operations**: < 2 seconds per test space

Run performance tests to validate:

```bash
python run_integration_tests.py --performance
```

## Security Considerations

- Always use separate test environments/projects
- Never run integration tests against production data
- Use service role keys with minimal required permissions
- Regularly rotate test API keys
- Monitor test resource usage and costs

## Support

For issues with the testing framework:

1. Check this guide for common solutions
2. Run environment validation: `python run_integration_tests.py --check-env`
3. Review test logs with verbose output: `pytest -v -s`
4. Check service status and connectivity
5. Verify environment variable configuration

The testing framework is designed to be robust and provide clear error messages to help diagnose issues quickly.
