"""露營樂爬蟲可行性測試。

用法：
    cd packages/scraper
    python test_easycamp.py

測試流程：
    1. 啟動 Playwright browser
    2. 爬取 1 個縣市（新竹縣）的營地列表
    3. 進入前 2 個營地的詳情頁
    4. 查詢 1 天的空位
    5. 印出所有抓到的資料

不需要 Supabase，純粹測試爬蟲邏輯是否能正確解析 HTML。
"""

import asyncio
import json
import logging
import sys
from datetime import date, timedelta

# 加入 parent path 以便 import
sys.path.insert(0, ".")

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("test_easycamp")

BASE_URL = "https://www.easycamp.com.tw"

# 只測一個區域，減少請求量
TEST_REGION = "north"
TEST_CITY_CODE = "hsinchu_county"
TEST_CITY_NAME = "新竹縣"
MAX_DETAIL_PAGES = 2  # 最多進入幾個詳情頁


async def test_listing_page(page):
    """測試營地列表頁。"""
    url = f"{BASE_URL}/Push_Camp_{TEST_REGION}_{TEST_CITY_CODE}_0.html"
    logger.info("=" * 60)
    logger.info("Step 1: Fetching listing page")
    logger.info("  URL: %s", url)

    await page.goto(url, wait_until="networkidle", timeout=30000)
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    # 印出頁面基本資訊
    title = soup.title.get_text(strip=True) if soup.title else "(no title)"
    logger.info("  Title: %s", title)
    logger.info("  HTML length: %d chars", len(html))

    # 找所有連結
    all_links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = a_tag.get_text(strip=True)[:40]
        if "Store_" in href or "/store/" in href.lower():
            full_url = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"
            all_links.append({"url": full_url, "text": text})

    logger.info("  Found %d campsite links (Store_*)", len(all_links))
    for i, link in enumerate(all_links[:5]):
        logger.info("    [%d] %s → %s", i, link["text"], link["url"])

    if not all_links:
        # 印出所有 <a> href 幫助 debug
        logger.warning("  No Store_ links found. Showing all links:")
        for a_tag in soup.find_all("a", href=True)[:20]:
            logger.info("    href=%s  text=%s", a_tag["href"], a_tag.get_text(strip=True)[:30])

    return all_links


async def test_detail_page(page, url: str):
    """測試營地詳情頁。"""
    logger.info("-" * 60)
    logger.info("Step 2: Fetching detail page")
    logger.info("  URL: %s", url)

    await page.goto(url, wait_until="networkidle", timeout=30000)
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    result = {}

    # 名稱
    for sel in ["h1", "h2", ".camp-name", ".store-name"]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            result["name"] = el.get_text(strip=True)
            break
    if "name" not in result and soup.title:
        result["name"] = soup.title.get_text(strip=True)

    logger.info("  Name: %s", result.get("name", "(not found)"))

    # 掃描所有文字，找關鍵欄位
    page_text = soup.get_text()
    import re

    # 地址
    addr_match = re.search(r"(?:地址|位置)[：:\s]*(.+?)(?:\n|$)", page_text)
    result["address"] = addr_match.group(1).strip()[:100] if addr_match else ""
    logger.info("  Address: %s", result["address"] or "(not found)")

    # 電話
    phone_match = re.search(r"(?:電話|聯絡)[：:\s]*([\d\-()+ ]+)", page_text)
    result["phone"] = phone_match.group(1).strip() if phone_match else ""
    logger.info("  Phone: %s", result["phone"] or "(not found)")

    # 海拔
    alt_match = re.search(r"(?:海拔|高度)[：:\s]*(\d+)", page_text)
    result["altitude"] = int(alt_match.group(1)) if alt_match else None
    logger.info("  Altitude: %s", result["altitude"] or "(not found)")

    # 圖片
    images = []
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if any(skip in src.lower() for skip in ["icon", "logo", "avatar", "pixel", "1x1"]):
            continue
        if src.startswith("/"):
            src = f"{BASE_URL}{src}"
        elif not src.startswith("http"):
            src = f"{BASE_URL}/{src}"
        if src not in images:
            images.append(src)
        if len(images) >= 5:
            break
    result["images"] = images
    logger.info("  Images: %d found", len(images))
    for img in images[:3]:
        logger.info("    %s", img)

    # 表格（營位區域）
    tables = soup.find_all("table")
    logger.info("  Tables found: %d", len(tables))
    for i, table in enumerate(tables):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows = table.find_all("tr")
        logger.info("    Table %d: %d rows, headers=%s", i, len(rows), headers[:6])
        for row in rows[:4]:
            cells = [td.get_text(strip=True)[:20] for td in row.find_all(["td", "th"])]
            if cells:
                logger.info("      %s", cells)

    # 設施相關文字
    facility_keywords = ["衛浴", "淋浴", "電源", "插座", "WiFi", "戲水池", "雨棚"]
    found_facilities = [kw for kw in facility_keywords if kw in page_text]
    result["facilities"] = found_facilities
    logger.info("  Facilities: %s", found_facilities)

    # 頁面結構概覽（幫助理解 DOM）
    logger.info("  DOM structure (main sections):")
    for tag in ["header", "main", "article", "section", "footer"]:
        els = soup.find_all(tag)
        if els:
            for el in els[:3]:
                classes = el.get("class", [])
                logger.info("    <%s class='%s'> %d children",
                            tag, " ".join(classes) if classes else "", len(el.find_all(recursive=False)))

    # CSS class 清單（前 20 個出現的 class）
    all_classes = set()
    for el in soup.find_all(class_=True):
        for cls in el.get("class", []):
            all_classes.add(cls)
    logger.info("  Unique CSS classes: %d", len(all_classes))
    logger.info("  Sample classes: %s", sorted(all_classes)[:20])

    return result


async def test_availability_page(page):
    """測試查空位頁面。"""
    logger.info("=" * 60)
    logger.info("Step 3: Testing availability page (/reserve)")

    url = f"{BASE_URL}/reserve"
    logger.info("  URL: %s", url)

    # 攔截 XHR/Fetch 請求
    api_calls = []

    async def on_response(response):
        if response.request.resource_type in ("xhr", "fetch"):
            api_calls.append({
                "url": response.url,
                "status": response.status,
                "method": response.request.method,
            })

    page.on("response", on_response)

    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        title = soup.title.get_text(strip=True) if soup.title else "(no title)"
        logger.info("  Title: %s", title)

        # 找表單
        forms = soup.find_all("form")
        logger.info("  Forms found: %d", len(forms))
        for i, form in enumerate(forms):
            action = form.get("action", "(no action)")
            method = form.get("method", "GET")
            logger.info("    Form %d: action=%s method=%s", i, action, method)

            inputs = form.find_all(["input", "select", "textarea"])
            for inp in inputs:
                inp_type = inp.get("type", inp.name)
                inp_name = inp.get("name", "(no name)")
                inp_id = inp.get("id", "")
                placeholder = inp.get("placeholder", "")
                logger.info("      <%s> name=%s id=%s type=%s placeholder=%s",
                            inp.name, inp_name, inp_id, inp_type, placeholder)

                # 如果是 select，印出 options
                if inp.name == "select":
                    options = inp.find_all("option")
                    for opt in options[:5]:
                        logger.info("        option: value=%s text=%s",
                                    opt.get("value", ""), opt.get_text(strip=True))
                    if len(options) > 5:
                        logger.info("        ... and %d more options", len(options) - 5)

        # 找按鈕
        buttons = soup.find_all(["button", "input"], attrs={"type": ["submit", "button"]})
        logger.info("  Buttons: %d", len(buttons))
        for btn in buttons:
            logger.info("    <%s> text=%s class=%s",
                        btn.name, btn.get_text(strip=True)[:30], btn.get("class", []))

        # 找 JavaScript 中的 API endpoint
        scripts = soup.find_all("script")
        import re
        for script in scripts:
            text = script.string or ""
            # 找 URL 模式
            urls = re.findall(r'["\']/(api|ajax|search|reserve|query)[^"\']*["\']', text, re.IGNORECASE)
            if urls:
                logger.info("  JS API patterns found: %s", urls[:5])
            # 找 fetch/axios 呼叫
            fetches = re.findall(r'(?:fetch|axios|ajax)\s*\(\s*["\']([^"\']+)["\']', text, re.IGNORECASE)
            if fetches:
                logger.info("  JS fetch/axios calls: %s", fetches[:5])

        # 印出攔截到的 API 呼叫
        if api_calls:
            logger.info("  XHR/Fetch requests detected during page load:")
            for call in api_calls:
                logger.info("    %s %s → %d", call["method"], call["url"], call["status"])

    finally:
        page.remove_listener("response", on_response)


async def main():
    logger.info("=" * 60)
    logger.info("EasyCamp Scraper Feasibility Test")
    logger.info("=" * 60)

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 720},
        locale="zh-TW",
    )
    page = await context.new_page()

    try:
        # Step 1: 營地列表頁
        links = await test_listing_page(page)

        # Step 2: 營地詳情頁（最多 MAX_DETAIL_PAGES 個）
        detail_results = []
        for link in links[:MAX_DETAIL_PAGES]:
            await asyncio.sleep(3)  # 禮貌延遲
            result = await test_detail_page(page, link["url"])
            detail_results.append(result)

        # Step 3: 查空位頁面
        await asyncio.sleep(3)
        await test_availability_page(page)

        # 輸出 JSON 摘要
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info("Listing page links: %d", len(links))
        logger.info("Detail pages scraped: %d", len(detail_results))

        for i, r in enumerate(detail_results):
            logger.info("  Camp %d: %s", i + 1, json.dumps(r, ensure_ascii=False, indent=2)[:500])

    except Exception as e:
        logger.exception("Test failed: %s", e)
    finally:
        await context.close()
        await browser.close()
        await pw.stop()

    logger.info("Test complete.")


if __name__ == "__main__":
    asyncio.run(main())
