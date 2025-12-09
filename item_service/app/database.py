# app/database.py
import os
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Create and return a Supabase client instance."""
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    return create_client(supabase_url, supabase_key)
