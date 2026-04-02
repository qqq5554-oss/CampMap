"""CampMap 爬蟲入口。

用法：
    python main.py                                    # 預設：all + availability-only + 60 天
    python main.py --platform easycamp --mode full    # 只跑露營樂，完整爬取
    python main.py --platform all --days 30           # 全平台，未來 30 天空位
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import date, timedelta

from scrapers import EasyCampScraper, CampTripScraper, ICampingScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("campmap")

SCRAPER_MAP = {
    "easycamp": EasyCampScraper,
    "camptrip": CampTripScraper,
    "icamping": ICampingScraper,
}

DEFAULT_DAYS_AHEAD = 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CampMap scraper")
    parser.add_argument(
        "--platform",
        choices=["easycamp", "camptrip", "icamping", "all"],
        default="all",
        help="要跑哪個平台的爬蟲（預設 all）",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "availability-only"],
        default="availability-only",
        help="full = 營地資料 + 空位；availability-only = 只更新空位（預設）",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS_AHEAD,
        help=f"查詢未來幾天的空位（預設 {DEFAULT_DAYS_AHEAD}）",
    )
    return parser.parse_args()


async def run_scraper(scraper_cls, mode: str, days: int) -> dict:
    """執行單一平台的爬蟲，回傳結果摘要 dict。"""
    scraper = scraper_cls()
    platform = scraper.platform
    t0 = time.monotonic()

    date_start = date.today()
    date_end = date_start + timedelta(days=days)

    try:
        if mode == "full":
            log = await scraper.run(date_start=date_start, date_end=date_end)
        else:
            # availability-only: 跳過 scrape_campsites，只跑空位
            log = await scraper.run(date_start=date_start, date_end=date_end)
            # BaseScraper.run() 總是會先跑 scrape_campsites，
            # 但 availability-only 模式下我們仍保留完整流程，
            # 未來可在 BaseScraper 加 skip_campsites 旗標。

        elapsed = time.monotonic() - t0
        return {
            "platform": platform,
            "status": log.status,
            "campsites": log.campsites_updated,
            "availability": log.availability_updated,
            "errors": log.error_message,
            "elapsed_s": round(elapsed, 1),
        }
    except Exception as e:
        elapsed = time.monotonic() - t0
        logger.exception("[%s] Fatal error", platform)
        return {
            "platform": platform,
            "status": "failed",
            "campsites": 0,
            "availability": 0,
            "errors": str(e),
            "elapsed_s": round(elapsed, 1),
        }


async def main():
    args = parse_args()

    # 決定要跑哪些平台
    if args.platform == "all":
        platforms = list(SCRAPER_MAP.keys())
    else:
        platforms = [args.platform]

    logger.info(
        "CampMap scraper — platforms=%s mode=%s days=%d",
        ",".join(platforms), args.mode, args.days,
    )

    t_total = time.monotonic()
    results = []

    for platform in platforms:
        scraper_cls = SCRAPER_MAP[platform]
        result = await run_scraper(scraper_cls, args.mode, args.days)
        results.append(result)

    total_elapsed = round(time.monotonic() - t_total, 1)

    # ── 摘要輸出 ──
    logger.info("=" * 60)
    logger.info("SCRAPE SUMMARY")
    logger.info("=" * 60)

    total_campsites = 0
    total_availability = 0
    any_failed = False

    for r in results:
        status_icon = "OK" if r["status"] == "success" else (
            "PARTIAL" if r["status"] == "partial" else "FAIL"
        )
        logger.info(
            "  [%s] %s — campsites=%d, availability=%d, time=%.1fs%s",
            r["platform"],
            status_icon,
            r["campsites"],
            r["availability"],
            r["elapsed_s"],
            f"\n    errors: {r['errors']}" if r["errors"] else "",
        )
        total_campsites += r["campsites"]
        total_availability += r["availability"]
        if r["status"] == "failed":
            any_failed = True

    logger.info("-" * 60)
    logger.info(
        "  TOTAL: campsites=%d, availability=%d, time=%.1fs",
        total_campsites, total_availability, total_elapsed,
    )
    logger.info("=" * 60)

    # 寫出摘要到檔案（供 CI artifact 上傳）
    try:
        with open("scrape_output.log", "w") as f:
            f.write(f"date: {date.today().isoformat()}\n")
            f.write(f"mode: {args.mode}\n")
            f.write(f"platforms: {','.join(platforms)}\n")
            f.write(f"total_campsites: {total_campsites}\n")
            f.write(f"total_availability: {total_availability}\n")
            f.write(f"elapsed_seconds: {total_elapsed}\n")
            for r in results:
                f.write(f"\n[{r['platform']}]\n")
                f.write(f"  status: {r['status']}\n")
                f.write(f"  campsites: {r['campsites']}\n")
                f.write(f"  availability: {r['availability']}\n")
                f.write(f"  elapsed: {r['elapsed_s']}s\n")
                if r["errors"]:
                    f.write(f"  errors: {r['errors']}\n")
    except Exception as e:
        logger.warning("Could not write scrape_output.log: %s", e)

    # 爬蟲失敗不讓 process exit(1)，因為錯誤已記錄到 scrape_logs
    # CI workflow 不會因此失敗
    if any_failed:
        logger.warning("Some scrapers failed — see scrape_logs table for details")
    else:
        logger.info("All scrapers completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
