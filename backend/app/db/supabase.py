from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

from app.core.config import get_settings


def get_supabase_client(access_token: str | None = None) -> Client:
    settings = get_settings()

    options = None
    if access_token:
        options = ClientOptions(
            headers={"Authorization": f"Bearer {access_token}"},
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
        options=options,
    )
