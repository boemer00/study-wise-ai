"""
Test script for the integration module.
"""
import os
import sys
import tempfile
import json
from pathlib import Path

# Add the project root to the path so we can import the src module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.integration import StudyWiseAI


def test_process_text():
    """Test processing text directly to flashcards."""
    app = StudyWiseAI()
    sample_text = """
    # Transformer Neural Networks

    Transformers are a type of neural network architecture that was introduced in the paper
    "Attention Is All You Need" by Vaswani et al. in 2017. They have revolutionized natural
    language processing and are now used in many state-of-the-art models like BERT, GPT, and T5.

    ## Key Components

    1. **Self-Attention Mechanism**: Allows the model to weigh the importance of different words
       in a sentence regardless of their position.
    2. **Multi-Head Attention**: Runs multiple attention mechanisms in parallel for better performance.
    3. **Positional Encoding**: Since the model has no recurrence or convolution, positional
       information is added to the embeddings.
    4. **Feed-Forward Networks**: Applied to each position separately and identically.

    Transformers have several advantages over previous architectures:
    - They can process all words in parallel, making them more efficient.
    - They can capture long-range dependencies better than RNNs.
    - They scale well to very large datasets and model sizes.
    """

    flashcards = app.process_text(sample_text, "transformer_notes.txt")

    print(f"Generated {len(flashcards)} flashcards from text:")
    for i, card in enumerate(flashcards, 1):
        print(f"\nFlashcard #{i}:")
        print(f"Q: {card['question']}")
        print(f"A: {card['answer']}")

    assert len(flashcards) > 0, "No flashcards were generated"
    assert "source_document" in flashcards[0], "Source document metadata is missing"
    assert flashcards[0]["source_document"] == "transformer_notes.txt", "Incorrect document name"

    return flashcards


def test_process_file():
    """Test processing a file to generate flashcards."""
    app = StudyWiseAI()

    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        sample_content = """
        # Support Vector Machines

        Support Vector Machines (SVMs) are a powerful supervised learning algorithm used for
        classification and regression. They were developed by Vladimir Vapnik in the 1990s.

        ## How SVMs Work

        SVMs work by finding the hyperplane that best separates the data into different classes.
        The best hyperplane is the one that maximizes the margin between the closest points
        (support vectors) of different classes.

        For non-linearly separable data, SVMs use a kernel trick to transform the data into a
        higher-dimensional space where it becomes linearly separable. Common kernels include:
        - Linear kernel
        - Polynomial kernel
        - Radial Basis Function (RBF) kernel
        - Sigmoid kernel
        """
        temp_file.write(sample_content.encode('utf-8'))
        temp_path = temp_file.name

    try:
        flashcards = app.process_file(temp_path)

        print(f"\nGenerated {len(flashcards)} flashcards from file:")
        for i, card in enumerate(flashcards, 1):
            print(f"\nFlashcard #{i}:")
            print(f"Q: {card['question']}")
            print(f"A: {card['answer']}")

        assert len(flashcards) > 0, "No flashcards were generated"
        assert "source_document" in flashcards[0], "Source document metadata is missing"
        assert os.path.basename(temp_path) == flashcards[0]["source_document"], "Incorrect document name"

        return flashcards
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


if __name__ == "__main__":
    print("Testing text processing...")
    text_cards = test_process_text()

    print("\nTesting file processing...")
    file_cards = test_process_file()

    print("\nAll tests passed successfully!")
