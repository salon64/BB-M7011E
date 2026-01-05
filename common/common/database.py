# common/database.py
# Shared Supabase database client for BB microservices

import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """Create and return a singleton Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            logger.warning("SUPABASE_URL or SUPABASE_KEY not set")
        _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client


def get_supabase() -> Client:
    """Alias for get_supabase_client for dependency injection."""
    return get_supabase_client()
