import json
import re
from .model import OpenAIClient

class FlashcardGenerator:
    """
    High-level class to chunk text, call OpenAI, and parse cards.
    """
    def __init__(self, level: str = "beginner"):
        """
        Initialize the flashcard generator with a specific difficulty level.

        Args:
            level: Difficulty level for flashcards (beginner, intermediate, advanced, expert)
        """
        self.openai = OpenAIClient()
        self.level = level

    def build_prompt(self, chunks: list[str]) -> str:
        return f"""
        You are a data science, AI, and ML tutor generating flashcards for a {self.level} student.
        Context:
        ```
        {''.join(chunks[:5])}
        ```
        Create exactly 10 high-quality flashcards based on the content.
        These should cover the most important concepts from the text.

        Output MUST be a valid JSON array of objects with "question" and "answer" fields only.
        Example format:
        [
            {{"question": "What is X?", "answer": "X is Y."}},
            {{"question": "How does Z work?", "answer": "Z works by..."}}
        ]

        Do not include any explanations or text outside of the JSON array.
        """

    def parse_response(self, text: str) -> list[dict]:
        """Parse the response from OpenAI to extract flashcards"""
        try:
            # Try direct JSON parsing first
            return json.loads(text)
        except json.JSONDecodeError:
            # If that fails, try to find JSON in the text using regex
            json_match = re.search(r'\[\s*{.*}\s*\]', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            # If we still can't parse, look for question-answer patterns
            cards = []
            # Look for patterns like "Q: ... A: ..."
            qa_matches = re.findall(r'Q: (.*?)\nA: (.*?)(?=\n\n|\n?$)', text, re.DOTALL)
            if qa_matches:
                for q, a in qa_matches:
                    cards.append({"question": q.strip(), "answer": a.strip()})
                return cards

            # If all else fails
            print("Failed to parse response. Raw response:")
            print(text[:500] + "..." if len(text) > 500 else text)
            return [{"question": "Error parsing response", "answer": "The model did not return valid JSON", "tags": ["error"]}]

    def generate(self, chunks: list[str]) -> list[dict]:
        prompt = self.build_prompt(chunks)
        raw = self.openai.generate_flashcards(prompt)
        cards = self.parse_response(raw)
        # Default metadata
        for c in cards:
            c.setdefault("tags", [])
            c.setdefault("level", self.level)
        return cards
