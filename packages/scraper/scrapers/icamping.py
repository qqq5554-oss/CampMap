"""愛露營 (icamping.app) 爬蟲。"""

import logging
import re
from datetime import date

from bs4 import BeautifulSoup

from .base import BaseScraper
from models.campsite import Campsite, Availability

logger = logging.getLogger(__name__)


class ICampingScraper(BaseScraper):
    """愛露營爬蟲。"""

    platform = "icamping"
    base_url = "https://www.icamping.app"

    async def scrape_campsites(self) -> list[dict]:
        """爬取營地列表，回傳原始字典列表。"""
        results: list[dict] = []
        page = await self.goto_with_retry(f"{self.base_url}/camps")
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        for card in soup.select(".campsite-card"):
            name_el = card.select_one(".name")
            location_el = card.select_one(".area")
            price_el = card.select_one(".price")
            link_el = card.select_one("a")

            if not name_el:
                continue

            href = link_el["href"] if link_el else ""
            source_id_match = re.search(r"/campsite/(\w+)", href) if href else None

            results.append({
                "name": name_el.get_text(strip=True),
                "location": location_el.get_text(strip=True) if location_el else "",
                "price_text": price_el.get_text(strip=True) if price_el else "",
                "url": f"{self.base_url}{href}" if href else self.base_url,
                "source_id": source_id_match.group(1) if source_id_match else "",
            })

            await self.random_delay()

        logger.info("[%s] Scraped %d campsites", self.platform, len(results))
        return results

    async def scrape_availability(
        self, date_start: date, date_end: date
    ) -> list[Availability]:
        """愛露營空位爬取（尚未實作完整）。"""
        logger.info("[%s] Availability scraping not yet implemented", self.platform)
        return []

    def normalize_campsite(self, raw: dict) -> Campsite:
        """將原始資料轉為統一 Campsite。"""
        price_min = None
        if raw.get("price_text"):
            digits = re.sub(r"[^\d]", "", raw["price_text"])
            if digits:
                price_min = int(digits)

        location = raw.get("location", "")
        city = ""
        district = ""
        if location:
            parts = re.match(r"^(.{2,3}[市縣])(.{2,3}[鄉鎮市區])?", location)
            if parts:
                city = parts.group(1) or ""
                district = parts.group(2) or ""

        name = raw["name"]
        slug = re.sub(r"\s+", "-", name.lower().strip())

        return Campsite(
            name=name,
            slug=slug,
            source_platform=self.platform,
            source_id=raw.get("source_id", ""),
            source_url=raw.get("url", ""),
            city=city,
            district=district,
            address=location,
            min_price=price_min,
        )
