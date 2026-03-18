import asyncio
import logging
import sys
from datetime import date, timedelta

from scrapers import EasyCampScraper, CampTripScraper, ICampingScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("campmap")

SCRAPERS = [EasyCampScraper, CampTripScraper, ICampingScraper]

# 預設爬取未來 14 天的空位
DEFAULT_DAYS_AHEAD = 14


async def main():
    date_start = date.today()
    date_end = date_start + timedelta(days=DEFAULT_DAYS_AHEAD)

    logger.info("CampMap scraper starting — dates: %s ~ %s", date_start, date_end)

    results = []
    for scraper_cls in SCRAPERS:
        scraper = scraper_cls()
        log = await scraper.run(date_start=date_start, date_end=date_end)
        results.append(log)

    # Summary
    for log in results:
        logger.info(
            "  [%s] status=%s campsites=%d availability=%d%s",
            log.platform,
            log.status,
            log.campsites_updated,
            log.availability_updated,
            f" errors={log.error_message}" if log.error_message else "",
        )

    failed = [r for r in results if r.status == "failed"]
    if failed:
        logger.warning("%d scraper(s) failed", len(failed))
        sys.exit(1)

    logger.info("All scrapers completed.")


if __name__ == "__main__":
    asyncio.run(main())
