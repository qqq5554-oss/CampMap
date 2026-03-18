import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def get_supabase_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def upsert_campsites(campsites: list[dict]):
    client = get_supabase_client()
    client.table("campsites").upsert(
        campsites, on_conflict="source,name"
    ).execute()
