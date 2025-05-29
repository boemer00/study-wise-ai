import os
from openai import OpenAI
from .config import settings

class OpenAIClient:
    """
    Wrapper around OpenAI API for generating flashcards.
    """
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_flashcards(self, prompt: str, model: str=None):
        if model is None:
            model = settings.OPENAI_MODEL or "gpt-4"

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a data-science tutor generating flashcards."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.2,
        )
        # Extract the content from the response
        return response.choices[0].message.content
