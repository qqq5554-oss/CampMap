import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
logger = logging.getLogger(__name__)

_client: Client | None = None


def get_supabase_client() -> Client:
    """取得 Supabase client（單例）。"""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
        logger.info("Supabase client initialized: %s", url)
    return _client


class SupabaseClient:
    """封裝 Supabase 操作，提供 upsert / insert / query 方法。"""

    def __init__(self):
        self._client = get_supabase_client()

    def upsert(self, table: str, records: list[dict], on_conflict: str):
        """批次 upsert，依 on_conflict 欄位進行增量更新。"""
        if not records:
            return
        # Supabase Python client 支援批次 upsert
        self._client.table(table).upsert(
            records, on_conflict=on_conflict
        ).execute()
        logger.debug("Upserted %d records into %s", len(records), table)

    def insert(self, table: str, record: dict):
        """插入單筆記錄。"""
        self._client.table(table).insert(record).execute()
        logger.debug("Inserted 1 record into %s", table)

    def query(self, table: str):
        """回傳 table query builder，供自訂查詢。"""
        return self._client.table(table)
