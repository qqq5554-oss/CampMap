from abc import ABC, abstractmethod
import asyncio
import logging
import random
from datetime import datetime, date

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from models.campsite import Campsite, CampsiteZone, Availability, ScrapeLog
from utils.db import SupabaseClient

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]


class BaseScraper(ABC):
    """所有平台爬蟲的基底類別。

    提供：
    - Playwright browser 管理（啟動、關閉、重試）
    - 反爬蟲策略：隨機 User-Agent、請求間隔隨機延遲、失敗重試（指數退避）
    - Supabase 寫入邏輯（upsert 營地、upsert 空位）
    - 日誌記錄（寫入 scrape_logs 表）

    子類別需實作：
    - scrape_campsites()
    - scrape_availability(date_range)
    - normalize_campsite(raw_data)
    """

    platform: str = "base"
    base_url: str = ""
    max_retries: int = 3
    delay_min: float = 2.0
    delay_max: float = 5.0

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._db = SupabaseClient()

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    async def _start_browser(self):
        """啟動 Playwright browser，使用隨機 User-Agent。"""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 720},
            locale="zh-TW",
        )
        self._page = await self._context.new_page()
        logger.info("[%s] Browser started", self.platform)

    async def _stop_browser(self):
        """關閉 browser 並釋放資源。"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        logger.info("[%s] Browser stopped", self.platform)

    async def _ensure_page(self) -> Page:
        """確保 page 存在，不存在則重新啟動 browser。"""
        if self._page is None or self._page.is_closed():
            await self._stop_browser()
            await self._start_browser()
        assert self._page is not None
        return self._page

    # ------------------------------------------------------------------
    # Anti-bot helpers
    # ------------------------------------------------------------------

    async def random_delay(self):
        """隨機延遲 2-5 秒，模擬人類行為。"""
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug("[%s] Sleeping %.1fs", self.platform, delay)
        await asyncio.sleep(delay)

    async def goto_with_retry(self, url: str, **kwargs) -> Page:
        """帶重試的頁面導航。失敗時指數退避重試最多 max_retries 次。"""
        page = await self._ensure_page()
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000, **kwargs)
                return page
            except Exception as e:
                last_error = e
                wait = 2 ** attempt + random.uniform(0, 1)
                logger.warning(
                    "[%s] goto failed (attempt %d/%d): %s — retrying in %.1fs",
                    self.platform, attempt, self.max_retries, e, wait,
                )
                await asyncio.sleep(wait)
                # Restart browser on retry to get fresh UA / state
                await self._stop_browser()
                await self._start_browser()
                page = self._page  # type: ignore[assignment]

        raise RuntimeError(
            f"[{self.platform}] Failed to load {url} after {self.max_retries} attempts"
        ) from last_error

    # ------------------------------------------------------------------
    # Abstract methods — 子類別實作
    # ------------------------------------------------------------------

    @abstractmethod
    async def scrape_campsites(self) -> list[dict]:
        """爬取營地基本資料，回傳原始資料字典列表。"""
        ...

    @abstractmethod
    async def scrape_availability(
        self, date_start: date, date_end: date
    ) -> list[Availability]:
        """爬取指定日期範圍的空位資訊。"""
        ...

    @abstractmethod
    def normalize_campsite(self, raw: dict) -> Campsite:
        """將平台原始資料轉成統一 Campsite dataclass。"""
        ...

    # ------------------------------------------------------------------
    # Supabase persistence
    # ------------------------------------------------------------------

    def upsert_campsites(self, campsites: list[Campsite]) -> int:
        """批次 upsert 營地到 Supabase，回傳成功筆數。"""
        if not campsites:
            return 0
        records = [c.to_dict() for c in campsites]
        self._db.upsert("campsites", records, on_conflict="source_platform,source_id")
        logger.info("[%s] Upserted %d campsites", self.platform, len(records))
        return len(records)

    def upsert_zones(self, zones: list[CampsiteZone]) -> int:
        """批次 upsert 營位區域。"""
        if not zones:
            return 0
        records = [z.to_dict() for z in zones]
        self._db.upsert("campsite_zones", records, on_conflict="campsite_id,zone_name")
        logger.info("[%s] Upserted %d zones", self.platform, len(records))
        return len(records)

    def upsert_availability(self, items: list[Availability]) -> int:
        """批次 upsert 空位快照（zone_id + date 為 unique key）。"""
        if not items:
            return 0
        records = [a.to_dict() for a in items]
        self._db.upsert("availability", records, on_conflict="zone_id,date")
        logger.info("[%s] Upserted %d availability records", self.platform, len(records))
        return len(records)

    def _write_scrape_log(self, log: ScrapeLog):
        """寫入爬蟲日誌到 scrape_logs 表。"""
        self._db.insert("scrape_logs", log.to_dict())

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run(
        self,
        date_start: date | None = None,
        date_end: date | None = None,
    ):
        """執行完整爬蟲流程：營地 → 空位 → 寫入 DB → 記錄日誌。

        單一營地失敗不會中斷整個流程。
        """
        log = ScrapeLog(platform=self.platform)
        campsites_count = 0
        availability_count = 0
        errors: list[str] = []

        try:
            await self._start_browser()

            # --- Phase 1: 爬取營地 ---
            logger.info("[%s] Phase 1: Scraping campsites...", self.platform)
            raw_list = await self.scrape_campsites()
            logger.info("[%s] Got %d raw campsite records", self.platform, len(raw_list))

            normalized: list[Campsite] = []
            for raw in raw_list:
                try:
                    camp = self.normalize_campsite(raw)
                    normalized.append(camp)
                except Exception as e:
                    msg = f"normalize failed for {raw.get('name', '?')}: {e}"
                    logger.error("[%s] %s", self.platform, msg)
                    errors.append(msg)

            campsites_count = self.upsert_campsites(normalized)

            # --- Phase 2: 爬取空位 ---
            if date_start and date_end:
                logger.info(
                    "[%s] Phase 2: Scraping availability %s ~ %s...",
                    self.platform, date_start, date_end,
                )
                try:
                    avail = await self.scrape_availability(date_start, date_end)
                    availability_count = self.upsert_availability(avail)
                except Exception as e:
                    msg = f"availability scrape failed: {e}"
                    logger.error("[%s] %s", self.platform, msg)
                    errors.append(msg)
            else:
                logger.info("[%s] Phase 2: Skipped (no date range provided)", self.platform)

            # --- Log result ---
            log.status = "partial" if errors else "success"

        except Exception as e:
            logger.exception("[%s] Fatal error", self.platform)
            log.status = "failed"
            errors.append(str(e))

        finally:
            await self._stop_browser()

            log.finished_at = datetime.utcnow().isoformat()
            log.campsites_updated = campsites_count
            log.availability_updated = availability_count
            log.error_message = "\n".join(errors) if errors else None

            try:
                self._write_scrape_log(log)
            except Exception as e:
                logger.error("[%s] Failed to write scrape log: %s", self.platform, e)

            logger.info(
                "[%s] Done — status=%s, campsites=%d, availability=%d",
                self.platform, log.status, campsites_count, availability_count,
            )

        return log
