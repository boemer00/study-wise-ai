import os
from openai import OpenAI
from .config import settings

class OpenAIClient:
    """
    Wrapper around OpenAI API for generating flashcards.
    """
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # Default model if not specified in settings
        self.default_model = settings.OPENAI_MODEL or "gpt-4o-mini"

    def generate_flashcards(self, prompt: str, model: str = None):
        # Use the provided model or the default model
        model_to_use = model or self.default_model

        response = self.client.responses.create(
            model=model_to_use,
            input=[
                {"role": "system", "content": "You are a data-science tutor generating flashcards."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.2,
        )
        # response.output_text contains JSON array
        return response.output_text
