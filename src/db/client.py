"""The one place a Supabase client is constructed.

Everything that touches the database takes a client from `get_client(config)`;
the URL and service key come only from the validated `Config`, never from a
direct environment read.
"""

from __future__ import annotations

from supabase import Client, create_client

from src.config import Config


def get_client(config: Config) -> Client:
    """Build a Supabase client from validated config."""
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
