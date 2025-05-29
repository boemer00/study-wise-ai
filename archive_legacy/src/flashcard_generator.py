import json
from .model import OpenAIClient

class FlashcardGenerator:
    """
    High-level class to chunk text, call OpenAI, and parse cards.
    """
    def __init__(self):
        self.openai = OpenAIClient()
        self.level = "intermediate"  # Default level

    def build_prompt(self, chunks: list[str]) -> str:
        # Join first 3 chunks with context marker
        combined_text = "\n\n---\n\n".join(chunks[:3])
        return f"""
        You are a data science, AI, and ML tutor generating flashcards for a {self.level} student.

        Context:
        ```
        {combined_text}
        ```

        Create 5-8 high-quality flashcards based on the most important concepts from the text.
        Each flashcard should have a clear question and comprehensive answer.

        Output a JSON array of objects with "question", "answer", and "tags" fields.
        Example:
        [
            {{
                "question": "What is the key contribution of the paper 'Attention Is All You Need'?",
                "answer": "The introduction of the Transformer architecture, which relies entirely on attention mechanisms without using recurrence or convolution.",
                "tags": ["transformers", "attention", "deep learning"]
            }}
        ]
        """

    def parse_response(self, text: str) -> list[dict]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from the text using regex
            import re
            json_match = re.search(r'\[\s*{.*}\s*\]', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            # Fallback to a default structure
            print("Warning: Could not parse JSON response")
            return [{
                "question": "Error parsing response",
                "answer": "There was an error parsing the model's response. Please try again.",
                "tags": ["error"]
            }]

    def generate(self, chunks: list[str]) -> list[dict]:
        # Process chunks in batches of 3 to avoid overloading the context
        all_cards = []
        batch_size = 3

        for i in range(0, min(len(chunks), 15), batch_size):
            batch_chunks = chunks[i:i+batch_size]
            prompt = self.build_prompt(batch_chunks)
            raw = self.openai.generate_flashcards(prompt)

            try:
                cards = self.parse_response(raw)
                # Add default metadata
                for c in cards:
                    c.setdefault("tags", [])
                    c.setdefault("level", self.level)

                all_cards.extend(cards)
            except Exception as e:
                print(f"Error processing batch {i//batch_size}: {str(e)}")

        return all_cards
