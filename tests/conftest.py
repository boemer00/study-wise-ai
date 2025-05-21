import pytest
import os
import tempfile
from pathlib import Path


@pytest.fixture
def test_files_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_text_file(test_files_dir):
    """Create a sample text file for testing."""
    file_path = test_files_dir / "sample.txt"
    with open(file_path, "w") as f:
        f.write("This is a sample text file for testing.\n" * 10)
    return file_path


@pytest.fixture
def sample_large_file(test_files_dir):
    """Create a sample large file exceeding the default size limit."""
    file_path = test_files_dir / "large_file.txt"
    # Create a file larger than 10MB (default limit)
    with open(file_path, "wb") as f:
        f.write(b"0" * (11 * 1024 * 1024))  # 11MB
    return file_path
