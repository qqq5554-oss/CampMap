from bs4 import BeautifulSoup
from .base import BaseScraper
from models.campsite import Campsite


class ICampingScraper(BaseScraper):
    """愛露營爬蟲。"""

    name = "icamping"
    base_url = "https://www.icamping.app"

    async def scrape(self) -> list[Campsite]:
        results: list[Campsite] = []
        assert self._page is not None

        await self._page.goto(f"{self.base_url}/camps", wait_until="networkidle")
        html = await self._page.content()
        soup = BeautifulSoup(html, "html.parser")

        for card in soup.select(".campsite-card"):
            name = card.select_one(".name")
            location = card.select_one(".area")
            price = card.select_one(".price")
            link = card.select_one("a")

            if not name:
                continue

            results.append(
                Campsite(
                    name=name.get_text(strip=True),
                    source=self.name,
                    location=location.get_text(strip=True) if location else "",
                    price_min=int(price.get_text(strip=True).replace(",", "").replace("$", "")) if price else None,
                    url=f"{self.base_url}{link['href']}" if link else self.base_url,
                )
            )

        return results
