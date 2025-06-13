"""
Modern FlashcardGenerator for StudyWise AI.

Generates high-quality flashcards from document chunks using OpenAI.
"""
import json
import os
import re
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class FlashcardGenerator:
    """
    Modern flashcard generator using OpenAI to create study cards from text content.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """
        Initialize the flashcard generator.

        Args:
            api_key: OpenAI API key (defaults to environment variable)
            model: OpenAI model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.level = "intermediate"  # Default difficulty level

        if not self.api_key:
            logger.warning("No OpenAI API key provided - flashcard generation will be simulated")
            self.client = None
        else:
            try:
                # Initialize OpenAI client with minimal parameters to avoid conflicts
                self.client = OpenAI(
                    api_key=self.api_key
                    # Remove any proxy or additional parameters that might cause issues
                )
                logger.info("FlashcardGenerator initialized with OpenAI client")
            except TypeError as e:
                if "proxies" in str(e):
                    logger.warning(f"OpenAI client initialization failed due to proxies parameter: {e}")
                    logger.info("Attempting fallback initialization without additional parameters")
                    try:
                        # Fallback: try with just the API key
                        import openai
                        openai.api_key = self.api_key
                        self.client = OpenAI(api_key=self.api_key)
                        logger.info("FlashcardGenerator initialized with fallback method")
                    except Exception as fallback_error:
                        logger.error(f"Fallback OpenAI initialization also failed: {fallback_error}")
                        self.client = None
                else:
                    logger.error(f"OpenAI client initialization failed with TypeError: {e}")
                    self.client = None
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None

    def set_difficulty_level(self, level: str) -> None:
        """Set the difficulty level for generated flashcards."""
        valid_levels = ["beginner", "intermediate", "advanced", "expert"]
        if level.lower() in valid_levels:
            self.level = level.lower()
        else:
            logger.warning(f"Invalid difficulty level: {level}. Using 'intermediate'")

    def build_prompt(self, chunks: List[str]) -> str:
        """
        Build a prompt for flashcard generation from text chunks.

        Args:
            chunks: List of text chunks to generate flashcards from

        Returns:
            Formatted prompt for OpenAI
        """
        # Join first 3 chunks with context markers
        combined_text = "\n\n---\n\n".join(chunks[:3])

        return f"""
You are an expert educational tutor generating flashcards for a {self.level} student.

Study Material:
```
{combined_text}
```

Create 5-8 high-quality flashcards based on the most important concepts from the text.

Requirements:
- Each flashcard should have a clear, specific question
- Answers should be comprehensive but concise
- Focus on key concepts, definitions, and relationships
- Use appropriate difficulty level for {self.level} students
- Include relevant tags for categorization

Output a valid JSON array of objects with "question", "answer", and "tags" fields.

Example format:
[
    {{
        "question": "What is the key contribution of the Transformer architecture?",
        "answer": "The Transformer introduced a purely attention-based model that eliminated the need for recurrent or convolutional layers, enabling better parallelization and handling of long-range dependencies in sequences.",
        "tags": ["transformers", "attention", "neural networks", "deep learning"]
    }}
]
        """.strip()

    def parse_response(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse OpenAI response into flashcard data.

        Args:
            text: Raw response text from OpenAI

        Returns:
            List of flashcard dictionaries
        """
        try:
            # Try direct JSON parsing first
            flashcards = json.loads(text)
            if isinstance(flashcards, list):
                return flashcards
        except json.JSONDecodeError:
            pass

        # Try to extract JSON array using regex
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
        if json_match:
            try:
                flashcards = json.loads(json_match.group(0))
                if isinstance(flashcards, list):
                    return flashcards
            except json.JSONDecodeError:
                pass

        # Fallback: create error flashcard
        logger.warning("Could not parse OpenAI response for flashcard generation")
        return [{
            "question": "Error: Could not generate flashcards",
            "answer": "There was an error processing the content. Please try again with different text.",
            "tags": ["error", "system"]
        }]

    def generate_with_openai(self, chunks: List[str]) -> List[Dict[str, Any]]:
        """
        Generate flashcards using OpenAI API.

        Args:
            chunks: Text chunks to process

        Returns:
            List of generated flashcards
        """
        if not self.client:
            logger.warning("OpenAI client not available - using demo flashcards")
            return self._generate_demo_flashcards(chunks)

        all_cards = []
        batch_size = 3

        # Process chunks in batches to avoid context limits
        for i in range(0, min(len(chunks), 15), batch_size):
            batch_chunks = chunks[i:i+batch_size]

            try:
                prompt = self.build_prompt(batch_chunks)

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert educational tutor who creates clear, effective flashcards."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=2000
                )

                raw_response = response.choices[0].message.content
                cards = self.parse_response(raw_response)

                # Add metadata to cards
                for card in cards:
                    card.setdefault("tags", [])
                    card.setdefault("level", self.level)
                    card.setdefault("source", "ai_generated")

                all_cards.extend(cards)
                logger.info(f"Generated {len(cards)} flashcards from batch {i//batch_size + 1}")

            except Exception as e:
                logger.error(f"Error generating flashcards for batch {i//batch_size + 1}: {e}")
                # Continue with other batches
                continue

        return all_cards

    def _generate_demo_flashcards(self, chunks: List[str]) -> List[Dict[str, Any]]:
        """
        Generate demo flashcards when OpenAI is not available.

        Args:
            chunks: Text chunks (for context)

        Returns:
            Demo flashcards
        """
        # Extract some keywords from the chunks for context
        text_sample = " ".join(chunks[:2])[:200] if chunks else "sample content"

        return [
            {
                "question": f"What is the main topic discussed in this {self.level}-level content?",
                "answer": f"Based on the content preview: '{text_sample[:100]}...', this appears to be educational material suitable for {self.level} students.",
                "tags": [self.level, "demo", "overview"],
                "level": self.level,
                "source": "demo_generated"
            },
            {
                "question": f"How can this content be used for {self.level} study?",
                "answer": f"This {self.level}-level content can be studied systematically using spaced repetition with flashcards, review sessions, and practice questions.",
                "tags": [self.level, "study_methods", "demo"],
                "level": self.level,
                "source": "demo_generated"
            }
        ]

    def generate(self, chunks: List[str], difficulty: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate flashcards from text chunks.

        Args:
            chunks: List of text chunks to process
            difficulty: Optional difficulty level override

        Returns:
            List of generated flashcard dictionaries
        """
        if not chunks:
            logger.warning("No chunks provided for flashcard generation")
            return []

        # Set difficulty if provided
        if difficulty:
            self.set_difficulty_level(difficulty)

        logger.info(f"Generating flashcards from {len(chunks)} chunks at {self.level} level")

        # Generate flashcards
        flashcards = self.generate_with_openai(chunks)

        logger.info(f"Successfully generated {len(flashcards)} flashcards")
        return flashcards

    def is_available(self) -> bool:
        """Check if flashcard generation is available."""
        return self.client is not None
