#!/usr/bin/env python3
"""
Integration Test Runner for StudyWise AI

This script provides a convenient way to run integration tests with proper
setup and configuration. It handles environment validation, test execution,
and result reporting.

Usage:
    python run_integration_tests.py --help
    python run_integration_tests.py --check-env
    python run_integration_tests.py --unit-only
    python run_integration_tests.py --integration-only
    python run_integration_tests.py --performance
    python run_integration_tests.py --all
"""

import argparse
import asyncio
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_environment() -> Dict[str, bool]:
    """Check if the integration test environment is properly configured."""
    checks = {
        "env_file_exists": Path(".env.test").exists(),
        "integration_test_env": bool(os.getenv("INTEGRATION_TEST_ENV")),
        "supabase_url": bool(os.getenv("SUPABASE_URL_TEST")),
        "supabase_key": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY_TEST")),
        "weaviate_url": bool(os.getenv("WEAVIATE_URL_TEST")),
        "openai_key": bool(os.getenv("OPENAI_API_KEY_TEST")),
        "python_packages": True  # Will check below
    }

    # Check Python packages
    try:
        import pytest
        import openai
        import supabase
        checks["python_packages"] = True
    except ImportError as e:
        logger.error(f"Missing required packages: {e}")
        checks["python_packages"] = False

    return checks


def print_environment_status():
    """Print the current environment configuration status."""
    print("\n🔍 Environment Check Results:")
    print("=" * 50)

    checks = check_environment()

    for check, status in checks.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {check.replace('_', ' ').title()}: {status}")

    if not all(checks.values()):
        print("\n⚠️  Some environment checks failed. Please review the setup:")
        print("   1. Copy env.test.example to .env.test")
        print("   2. Fill in your test service credentials")
        print("   3. Set INTEGRATION_TEST_ENV=local_test")
        print("   4. Install required packages: pip install -r requirements.txt")
        return False

    print("\n✅ Environment is ready for integration testing!")
    return True


def load_test_environment():
    """Load test environment variables from .env.test file."""
    env_file = Path(".env.test")
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            logger.info("Loaded environment variables from .env.test")
        except ImportError:
            logger.warning("python-dotenv not available, using system environment variables")
    else:
        logger.warning(".env.test file not found, using system environment variables")


def run_command(cmd: List[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🚀 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def run_unit_tests() -> bool:
    """Run unit tests for the integration testing framework."""
    cmd = [
        "python", "-m", "pytest",
        "tests/test_integration_test_manager.py",
        "-v",
        "--tb=short",
        "--strict-markers"
    ]
    return run_command(cmd, "Running Unit Tests for Integration Framework")


def run_integration_tests(category: Optional[str] = None) -> bool:
    """Run integration tests with optional category filter."""
    cmd = [
        "python", "-m", "pytest",
        "tests/integration_tests.py",
        "-v",
        "--tb=short",
        "--strict-markers"
    ]

    if category:
        cmd.extend(["-m", f"integration and {category}"])
    else:
        cmd.extend(["-m", "integration"])

    description = f"Running Integration Tests{f' ({category})' if category else ''}"
    return run_command(cmd, description)


def run_performance_tests() -> bool:
    """Run performance tests."""
    cmd = [
        "python", "-m", "pytest",
        "tests/integration_tests.py",
        "-v",
        "--tb=short",
        "--strict-markers",
        "-m", "integration and performance"
    ]
    return run_command(cmd, "Running Performance Tests")


def run_all_tests() -> bool:
    """Run all tests in the project."""
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--strict-markers"
    ]
    return run_command(cmd, "Running All Tests")


def run_specific_test_class(test_class: str) -> bool:
    """Run a specific test class."""
    cmd = [
        "python", "-m", "pytest",
        f"tests/integration_tests.py::{test_class}",
        "-v",
        "--tb=short",
        "--strict-markers",
        "-m", "integration"
    ]
    return run_command(cmd, f"Running {test_class}")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Integration Test Runner for StudyWise AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_integration_tests.py --check-env
    python run_integration_tests.py --unit-only
    python run_integration_tests.py --integration-only
    python run_integration_tests.py --performance
    python run_integration_tests.py --connectivity
    python run_integration_tests.py --pipeline
    python run_integration_tests.py --all
        """
    )

    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Check environment configuration and exit"
    )

    parser.add_argument(
        "--unit-only",
        action="store_true",
        help="Run only unit tests for the integration framework"
    )

    parser.add_argument(
        "--integration-only",
        action="store_true",
        help="Run only integration tests (requires real services)"
    )

    parser.add_argument(
        "--performance",
        action="store_true",
        help="Run performance tests"
    )

    parser.add_argument(
        "--connectivity",
        action="store_true",
        help="Run service connectivity tests"
    )

    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Run document processing pipeline tests"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests in the project"
    )

    parser.add_argument(
        "--class",
        dest="test_class",
        help="Run a specific test class (e.g., TestServiceConnectivity)"
    )

    args = parser.parse_args()

    # Load environment
    load_test_environment()

    # Check environment if requested
    if args.check_env:
        success = print_environment_status()
        sys.exit(0 if success else 1)

    # If no specific test type specified, check environment first
    if not any([args.unit_only, args.integration_only, args.performance,
               args.connectivity, args.pipeline, args.all, args.test_class]):
        print("No test type specified. Checking environment first...")
        if not print_environment_status():
            print("\nRun with --unit-only to test framework without real services")
            sys.exit(1)

    success = True

    # Run requested tests
    if args.unit_only:
        success = run_unit_tests()

    elif args.integration_only:
        if not print_environment_status():
            print("❌ Environment not ready for integration tests")
            sys.exit(1)
        success = run_integration_tests()

    elif args.performance:
        if not print_environment_status():
            print("❌ Environment not ready for performance tests")
            sys.exit(1)
        success = run_performance_tests()

    elif args.connectivity:
        if not print_environment_status():
            print("❌ Environment not ready for connectivity tests")
            sys.exit(1)
        success = run_specific_test_class("TestServiceConnectivity")

    elif args.pipeline:
        if not print_environment_status():
            print("❌ Environment not ready for pipeline tests")
            sys.exit(1)
        success = run_specific_test_class("TestDocumentProcessingPipeline")

    elif args.all:
        success = run_all_tests()

    elif args.test_class:
        if not print_environment_status():
            print("❌ Environment not ready for integration tests")
            sys.exit(1)
        success = run_specific_test_class(args.test_class)

    else:
        # Default: run unit tests first, then integration if environment is ready
        print("🧪 Running comprehensive test suite...\n")

        # Always run unit tests
        unit_success = run_unit_tests()

        # Run integration tests if environment is ready
        if print_environment_status():
            integration_success = run_integration_tests()
            success = unit_success and integration_success
        else:
            print("\n⚠️  Skipping integration tests due to environment issues")
            print("   Run with --unit-only to test framework only")
            success = unit_success

    # Final result
    if success:
        print("\n🎉 All tests completed successfully!")
    else:
        print("\n❌ Some tests failed. Please review the output above.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
