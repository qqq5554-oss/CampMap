import asyncio
import sys
from scrapers import EasyCampScraper, CampTripScraper, ICampingScraper
from utils.db import upsert_campsites

SCRAPERS = [EasyCampScraper, CampTripScraper, ICampingScraper]


async def main():
    all_campsites = []

    for scraper_cls in SCRAPERS:
        scraper = scraper_cls()
        print(f"[*] Running {scraper.name}...")
        try:
            sites = await scraper.run()
            print(f"    Found {len(sites)} campsites")
            all_campsites.extend(sites)
        except Exception as e:
            print(f"    Error: {e}", file=sys.stderr)

    if all_campsites:
        print(f"[*] Upserting {len(all_campsites)} campsites to Supabase...")
        upsert_campsites([s.to_dict() for s in all_campsites])
        print("[*] Done!")
    else:
        print("[*] No campsites found.")


if __name__ == "__main__":
    asyncio.run(main())
