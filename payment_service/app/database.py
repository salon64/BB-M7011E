from supabase import create_client, Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

supabase_client: Client = create_client(
    settings.supabase_url,
    settings.supabase_key
)

def get_supabase() -> Client:
    return supabase_client