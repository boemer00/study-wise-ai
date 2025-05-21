import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """
    Configuration settings loaded from environment.
    """
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # or ANON_KEY
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL")

settings = Settings()
