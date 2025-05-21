import os
from openai import OpenAI
from config import settings

class OpenAIClient:
    """
    Wrapper around OpenAI API for generating flashcards.
    """
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_flashcards(self, prompt: str, model: str=settings.OPENAI_MODEL):
        response = self.client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": "You are a data-science tutor generating flashcards."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.2,
        )
        # response.output_text contains JSON array
        return response.output_text
