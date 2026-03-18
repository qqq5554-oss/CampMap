from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Browser, Page
from models.campsite import Campsite


class BaseScraper(ABC):
    """爬蟲基底類別，提供共用的瀏覽器管理與介面定義。"""

    name: str = "base"
    base_url: str = ""

    def __init__(self):
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def start(self):
        pw = await async_playwright().start()
        self._browser = await pw.chromium.launch(headless=True)
        self._page = await self._browser.new_page()

    async def stop(self):
        if self._browser:
            await self._browser.close()

    @abstractmethod
    async def scrape(self) -> list[Campsite]:
        """執行爬取，回傳統一的 Campsite 列表。"""
        ...

    async def run(self) -> list[Campsite]:
        try:
            await self.start()
            return await self.scrape()
        finally:
            await self.stop()
