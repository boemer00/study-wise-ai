"""
Supabase client configuration and utilities for the StudyWise AI application.
This module provides functions to connect to Supabase and perform database operations.
"""
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_supabase_client() -> Client:
    """
    Initialize and return a Supabase client.

    Returns:
        Client: Authenticated Supabase client

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY environment variables are not set
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in the .env file"
        )

    return create_client(SUPABASE_URL, SUPABASE_KEY)
