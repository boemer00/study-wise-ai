import json
from .model import OpenAIClient

class FlashcardGenerator:
    """
    High-level class to chunk text, call OpenAI, and parse cards.
    """
    def __init__(self):
        self.openai = OpenAIClient()

    def build_prompt(self, chunks: list[str]) -> str:
        return f"""
        You are a data science, AI, and ML tutor generating flashcards for a beginner student.
        Context:
        ```
        {chunks[:5]}
        ```
        Output a JSON array of objects with "question", "answer", and "tags" fields.
        """

    def parse_response(self, text: str) -> list[dict]:
        return json.loads(text)

    def generate(self, chunks: list[str]) -> list[dict]:
        prompt = self.build_prompt(chunks)
        raw = self.openai.generate_flashcards(prompt)
        cards = self.parse_response(raw)
        # Default metadata
        for c in cards:
            c.setdefault("tags", [])
            c.setdefault("level", self.level)
        return cards
