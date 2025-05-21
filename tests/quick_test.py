"""
Quick test script for the document module.
This is used to verify basic functionality without running the full test suite.
"""
import os
import sys
import tempfile

# Add the project root to the path so we can import the src module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.document import DocumentUploader

def test_text_upload():
    """Test uploading text directly."""
    uploader = DocumentUploader()
    sample_text = "This is a sample text for testing the document uploader."

    # Test uploading text
    document = uploader.upload_from_text(sample_text)

    print("=== Text Upload Test ===")
    print(f"File name: {document.file_name}")
    print(f"File type: {document.file_type}")
    print(f"Upload date: {document.upload_date}")
    print(f"Content length: {len(document.content)} characters")
    print(f"Number of chunks: {len(document.chunks)}")
    print(f"First chunk: {document.chunks[0][:50]}...")

    return document

def test_file_creation_and_upload():
    """Test creating a file and uploading it."""
    uploader = DocumentUploader()

    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        temp_file.write(b"This is a sample text file for testing the document uploader.\n" * 10)
        temp_path = temp_file.name

    try:
        # Test uploading file
        document = uploader.upload_from_file(temp_path)

        print("\n=== File Upload Test ===")
        print(f"File name: {document.file_name}")
        print(f"File type: {document.file_type}")
        print(f"Upload date: {document.upload_date}")
        print(f"Content length: {len(document.content)} characters")
        print(f"Number of chunks: {len(document.chunks)}")
        print(f"First chunk: {document.chunks[0][:50]}...")

        return document
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    print("Running quick tests for the document module...")
    test_text_upload()
    test_file_creation_and_upload()
    print("\nAll tests completed successfully!")
