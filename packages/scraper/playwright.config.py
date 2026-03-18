"""Playwright configuration for CampMap scrapers."""

BROWSER = "chromium"
HEADLESS = True
TIMEOUT = 30000  # 30 seconds
VIEWPORT = {"width": 1280, "height": 720}
