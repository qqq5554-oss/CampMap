"""露營樂 (easycamp.com.tw) 爬蟲。

網站特性：
- Server-rendered HTML（非 SPA），但有嚴格 anti-bot（403 on raw requests）
- 營地列表：/Push_Camp_{region}_{city}_0.html
- 營地詳情：/Store_{source_id}.html
- 查空位頁面：/reserve（表單搜尋）
- 搜尋參數：縣市、行政區、入住日期、露營天數(2-6天)、帳數(1-55)
"""

import logging
import re
from datetime import date, timedelta

from bs4 import BeautifulSoup, Tag

from .base import BaseScraper
from models.campsite import Campsite, CampsiteZone, Availability

logger = logging.getLogger(__name__)

# 露營樂的地區→縣市對應表
REGIONS: dict[str, list[tuple[str, str]]] = {
    "north": [
        ("newtaipei", "新北市"),
        ("taoyuan", "桃園市"),
        ("hsinchu_county", "新竹縣"),
        ("hsinchu_city", "新竹市"),
        ("yilan", "宜蘭縣"),
    ],
    "central": [
        ("miaoli", "苗栗縣"),
        ("taichung", "台中市"),
        ("nantou", "南投縣"),
        ("changhua", "彰化縣"),
        ("yunlin", "雲林縣"),
    ],
    "south": [
        ("chiayi_county", "嘉義縣"),
        ("tainan", "台南市"),
        ("kaohsiung", "高雄市"),
        ("pingtung", "屏東縣"),
    ],
    "east": [
        ("hualien", "花蓮縣"),
        ("taitung", "台東縣"),
    ],
}


def _slugify(name: str) -> str:
    """將營地名稱轉為 URL-friendly slug。"""
    s = name.strip().lower()
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", s)
    return s.strip("-")


def _parse_int(text: str) -> int | None:
    """從文字中提取整數（去除逗號、$、元等）。"""
    if not text:
        return None
    cleaned = re.sub(r"[^\d]", "", text)
    return int(cleaned) if cleaned else None


class EasyCampScraper(BaseScraper):
    """露營樂爬蟲。"""

    platform = "easycamp"
    base_url = "https://www.easycamp.com.tw"

    # ------------------------------------------------------------------
    # Step 1: scrape_campsites — 爬各縣市營地列表 → 進入詳情頁
    # ------------------------------------------------------------------

    async def scrape_campsites(self) -> list[dict]:
        """爬取所有縣市的營地列表，再逐一進入詳情頁取得完整資料。"""
        all_raw: list[dict] = []

        for region, cities in REGIONS.items():
            for city_code, city_name in cities:
                try:
                    links = await self._scrape_listing_page(region, city_code, city_name)
                    logger.info(
                        "[easycamp] %s %s: found %d campsites",
                        region, city_name, len(links),
                    )
                    for link in links:
                        try:
                            raw = await self._scrape_detail_page(link, city_name)
                            if raw:
                                all_raw.append(raw)
                        except Exception as e:
                            logger.error("[easycamp] Detail page failed %s: %s", link, e)
                        await self.random_delay()
                except Exception as e:
                    logger.error("[easycamp] Listing page failed %s/%s: %s", region, city_code, e)
                await self.random_delay()

        return all_raw

    async def _scrape_listing_page(
        self, region: str, city_code: str, city_name: str
    ) -> list[str]:
        """爬取單一縣市的營地列表頁，回傳各營地詳情頁的 URL 路徑列表。"""
        url = f"{self.base_url}/Push_Camp_{region}_{city_code}_0.html"
        page = await self.goto_with_retry(url)
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        links: list[str] = []

        # 策略 1: 找 a[href] 含 Store_ 或 campsite detail 連結
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "Store_" in href or "/store/" in href.lower():
                full_url = href if href.startswith("http") else f"{self.base_url}/{href.lstrip('/')}"
                if full_url not in links:
                    links.append(full_url)

        # 策略 2: 如果沒找到 Store_ 連結，嘗試其他常見模式
        if not links:
            for a_tag in soup.select("a[href*='camp'], a[href*='Camp']"):
                href = a_tag["href"]
                # 排除列表頁自身的連結
                if "Push_Camp_" not in href:
                    full_url = href if href.startswith("http") else f"{self.base_url}/{href.lstrip('/')}"
                    if full_url not in links:
                        links.append(full_url)

        return links

    async def _scrape_detail_page(self, url: str, city_name: str) -> dict | None:
        """爬取單一營地詳情頁，回傳原始資料字典。"""
        page = await self.goto_with_retry(url)
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # 提取 source_id from URL (e.g. Store_123.html → "123")
        source_id_match = re.search(r"Store_(\w+)", url)
        source_id = source_id_match.group(1) if source_id_match else url.split("/")[-1]

        # --- 營地名稱 ---
        name = self._extract_text(soup, "h1, h2, .camp-name, .store-name, title")
        if not name or len(name) < 2:
            logger.warning("[easycamp] No name found at %s", url)
            return None

        # 若是 title tag，清理 " - 露營樂" 之類的後綴
        name = re.sub(r"\s*[-|｜].*露營樂.*$", "", name).strip()
        name = re.sub(r"\s*[-|｜]\s*EasyCamp.*$", "", name, flags=re.IGNORECASE).strip()

        # --- 地址 / 電話 / 海拔 ---
        address = self._extract_field(soup, ["地址", "address", "位置"])
        phone = self._extract_field(soup, ["電話", "phone", "聯絡"])
        altitude_text = self._extract_field(soup, ["海拔", "altitude", "高度"])
        altitude = _parse_int(altitude_text) if altitude_text else None

        # --- 設施 ---
        facilities = self._extract_facilities(soup)

        # --- 圖片 ---
        images = self._extract_images(soup)

        # --- 營位區域 & 價格 ---
        zones = self._extract_zones(soup)

        # --- 價格範圍 ---
        all_prices = []
        for z in zones:
            for p in [z.get("price_weekday"), z.get("price_weekend"), z.get("price_holiday")]:
                if p and p > 0:
                    all_prices.append(p)

        # 如果區域沒有價格，嘗試從頁面抓取
        if not all_prices:
            price_texts = soup.find_all(string=re.compile(r"\$?\d{3,5}"))
            for pt in price_texts:
                p = _parse_int(pt)
                if p and 100 <= p <= 50000:
                    all_prices.append(p)

        # --- 簡介 ---
        description = self._extract_description(soup)

        return {
            "source_id": source_id,
            "source_url": url,
            "name": name,
            "city": city_name,
            "district": self._extract_district(address, city_name) if address else "",
            "address": address or "",
            "phone": phone or "",
            "altitude": altitude,
            "facilities": facilities,
            "images": images,
            "zones": zones,
            "min_price": min(all_prices) if all_prices else None,
            "max_price": max(all_prices) if all_prices else None,
            "description": description,
        }

    # ------------------------------------------------------------------
    # Step 2: scrape_availability — 查空位
    # ------------------------------------------------------------------

    async def scrape_availability(
        self, date_start: date, date_end: date
    ) -> list[Availability]:
        """透過露營樂查空位頁面，爬取日期範圍內的空位狀態。

        露營樂的查空位頁 (/reserve) 使用表單搜尋：
        - 選擇縣市、入住日期、天數、帳數
        - 回傳有空位的營地列表

        我們對每一天發送搜尋，解析結果。
        """
        results: list[Availability] = []
        current = date_start

        while current <= date_end:
            try:
                day_results = await self._scrape_availability_for_date(current)
                results.extend(day_results)
                logger.info(
                    "[easycamp] Availability %s: %d records",
                    current.isoformat(), len(day_results),
                )
            except Exception as e:
                logger.error("[easycamp] Availability failed for %s: %s", current, e)
            await self.random_delay()
            current += timedelta(days=1)

        return results

    async def _scrape_availability_for_date(self, target_date: date) -> list[Availability]:
        """查詢特定日期的空位。

        嘗試兩種方式：
        1. 直接操作 /reserve 頁面上的表單
        2. 攔截網路請求找出 API endpoint（如果是 AJAX）
        """
        page = await self._ensure_page()
        results: list[Availability] = []

        # 記錄 XHR/Fetch 回應，偵測是否有 AJAX API
        api_responses: list[dict] = []

        async def capture_response(response):
            url = response.url
            if response.request.resource_type in ("xhr", "fetch"):
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct or "html" in ct:
                        api_responses.append({
                            "url": url,
                            "status": response.status,
                        })
                except Exception:
                    pass

        page.on("response", capture_response)

        try:
            await self.goto_with_retry(f"{self.base_url}/reserve")

            date_str = target_date.strftime("%Y-%m-%d")

            # 嘗試填寫表單並提交
            # 日期欄位
            date_input = await page.query_selector(
                "input[type='date'], input[name*='date'], input[name*='Date'], "
                "input.datepicker, input#checkin, input[placeholder*='日期']"
            )
            if date_input:
                await date_input.fill(date_str)

            # 帳數預設 1
            tent_input = await page.query_selector(
                "input[name*='tent'], input[name*='Tent'], "
                "select[name*='tent'], input[name*='qty'], input[name*='num']"
            )
            if tent_input:
                tag_name = await tent_input.evaluate("el => el.tagName.toLowerCase()")
                if tag_name == "select":
                    await tent_input.select_option("1")
                else:
                    await tent_input.fill("1")

            # 提交表單
            submit_btn = await page.query_selector(
                "button[type='submit'], input[type='submit'], "
                "button.search-btn, button.btn-search, a.search"
            )
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_load_state("networkidle")
            else:
                # 找 form 元素直接 submit
                form = await page.query_selector("form")
                if form:
                    await form.evaluate("f => f.submit()")
                    await page.wait_for_load_state("networkidle")

            # 解析結果頁面
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            results = self._parse_availability_results(soup, target_date)

        finally:
            page.remove_listener("response", capture_response)

        # 記錄偵測到的 API endpoints（供未來最佳化）
        if api_responses:
            logger.info(
                "[easycamp] Detected %d API calls during availability search: %s",
                len(api_responses),
                [r["url"] for r in api_responses[:5]],
            )

        return results

    def _parse_availability_results(
        self, soup: BeautifulSoup, target_date: date
    ) -> list[Availability]:
        """解析查空位結果頁面的 HTML。"""
        results: list[Availability] = []

        # 露營樂結果通常是營地列表，每個營地有區域資訊
        # 嘗試多種常見的 CSS class/結構
        camp_items = soup.select(
            ".search-result-item, .camp-result, .result-item, "
            ".reserve-item, .camp-card, .store-item, "
            "table.reserve-table tr, .list-item"
        )

        for item in camp_items:
            if not isinstance(item, Tag):
                continue

            # 找營地/區域辨識資訊
            zone_link = item.select_one("a[href*='Store_']")
            zone_name_el = item.select_one(
                ".zone-name, .area-name, .camp-zone, td:nth-child(2)"
            )

            # 找空位狀態
            status_el = item.select_one(
                ".status, .availability, .badge, .camp-status, .reserve-status"
            )
            status_text = status_el.get_text(strip=True) if status_el else ""
            status = self._parse_status_text(status_text or item.get_text())

            # 找剩餘數量
            remaining = None
            remaining_el = item.select_one(".remaining, .spots, .count")
            if remaining_el:
                remaining = _parse_int(remaining_el.get_text())

            # 找價格
            price = None
            price_el = item.select_one(".price, .cost, .amount")
            if price_el:
                price = _parse_int(price_el.get_text())

            # zone_id 需要從 DB 查對應，這裡先用 placeholder
            # 實際使用時，會在 BaseScraper.run() 後做 zone mapping
            zone_id_hint = ""
            if zone_link:
                zone_id_hint = zone_link.get("href", "")
            elif zone_name_el:
                zone_id_hint = zone_name_el.get_text(strip=True)

            if zone_id_hint:
                results.append(
                    Availability(
                        zone_id=zone_id_hint,  # placeholder — 實際寫入前需替換為真實 UUID
                        date=target_date.isoformat(),
                        status=status,
                        remaining_spots=remaining,
                        price=price,
                    )
                )

        return results

    def _parse_status_text(self, text: str) -> str:
        """將中文狀態文字轉為標準狀態碼。"""
        text = text.strip()
        if re.search(r"已滿|額滿|客滿|無空位|sold\s*out", text, re.IGNORECASE):
            return "full"
        if re.search(r"尚有|有空位|可預訂|available|剩餘|還有", text, re.IGNORECASE):
            return "available"
        if re.search(r"即將額滿|少量|limited|剩餘\s*[1-3]\s*帳", text, re.IGNORECASE):
            return "limited"
        if re.search(r"未開放|不開放|維護|closed", text, re.IGNORECASE):
            return "full"
        return "unknown"

    # ------------------------------------------------------------------
    # normalize_campsite — 原始資料 → Campsite dataclass
    # ------------------------------------------------------------------

    def normalize_campsite(self, raw: dict) -> Campsite:
        """將 _scrape_detail_page 回傳的 dict 轉成統一 Campsite。"""
        name = raw["name"]
        return Campsite(
            name=name,
            slug=_slugify(name),
            source_platform="easycamp",
            source_url=raw["source_url"],
            source_id=raw["source_id"],
            description=raw.get("description", ""),
            city=raw.get("city", ""),
            district=raw.get("district", ""),
            address=raw.get("address", ""),
            altitude=raw.get("altitude"),
            phone=raw.get("phone", ""),
            images=raw.get("images", []),
            facilities=raw.get("facilities", []),
            min_price=raw.get("min_price"),
            max_price=raw.get("max_price"),
        )

    def normalize_zones(self, raw: dict, campsite_id: str) -> list[CampsiteZone]:
        """將原始營位區域資料轉成 CampsiteZone 列表。"""
        zones: list[CampsiteZone] = []
        for z in raw.get("zones", []):
            zones.append(CampsiteZone(
                campsite_id=campsite_id,
                zone_name=z.get("name", ""),
                zone_type=z.get("type", "散帳"),
                max_tents=z.get("max_tents"),
                has_power=z.get("has_power", False),
                has_roof=z.get("has_roof", False),
                ground_type=z.get("ground_type", ""),
                price_weekday=z.get("price_weekday"),
                price_weekend=z.get("price_weekend"),
                price_holiday=z.get("price_holiday"),
            ))
        return zones

    # ------------------------------------------------------------------
    # HTML 解析輔助方法
    # ------------------------------------------------------------------

    def _extract_text(self, soup: BeautifulSoup, selectors: str) -> str:
        """依序嘗試多個 CSS selector，回傳第一個有文字的結果。"""
        for sel in selectors.split(","):
            el = soup.select_one(sel.strip())
            if el:
                text = el.get_text(strip=True)
                if text:
                    return text
        return ""

    def _extract_field(self, soup: BeautifulSoup, keywords: list[str]) -> str | None:
        """找包含特定關鍵字的欄位，回傳其值文字。

        常見結構：
        - <dt>地址</dt><dd>新竹縣...</dd>
        - <span class="label">地址：</span><span>新竹縣...</span>
        - <div>地址：新竹縣...</div>
        """
        for kw in keywords:
            # 嘗試 dt/dd 結構
            dt = soup.find(string=re.compile(kw))
            if dt:
                parent = dt.find_parent()
                if parent:
                    # dt → dd sibling
                    dd = parent.find_next_sibling("dd")
                    if dd:
                        return dd.get_text(strip=True)
                    # span.label → next sibling
                    sib = parent.find_next_sibling()
                    if sib:
                        return sib.get_text(strip=True)
                    # 同一元素內 "地址：xxx"
                    full = parent.get_text(strip=True)
                    match = re.search(rf"{kw}[：:\s]*(.+)", full)
                    if match:
                        return match.group(1).strip()
        return None

    def _extract_facilities(self, soup: BeautifulSoup) -> list[str]:
        """提取設施列表。"""
        facilities: list[str] = []

        # 方式 1: 設施列表標籤
        facility_section = soup.find(string=re.compile(r"設施|設備|Facilities"))
        if facility_section:
            parent = facility_section.find_parent()
            if parent:
                container = parent.find_next_sibling() or parent.parent
                if container:
                    for li in container.find_all(["li", "span", "div", "label"]):
                        text = li.get_text(strip=True)
                        if text and len(text) < 20:
                            facilities.append(text)

        # 方式 2: icon + label 結構
        if not facilities:
            for el in soup.select(".facility, .amenity, .icon-label, .feature-item"):
                text = el.get_text(strip=True)
                if text and len(text) < 20:
                    facilities.append(text)

        # 關鍵字比對（fallback）
        known = ["衛浴", "淋浴", "電源", "插座", "WiFi", "戲水池", "雨棚",
                  "冰箱", "飲水機", "洗衣機", "烘衣機", "吹風機", "脫水機",
                  "垃圾桶", "停車場", "沙坑", "遊樂設施", "小木屋"]
        if not facilities:
            page_text = soup.get_text()
            for kw in known:
                if kw in page_text:
                    facilities.append(kw)

        return list(dict.fromkeys(facilities))  # dedupe preserving order

    def _extract_images(self, soup: BeautifulSoup) -> list[str]:
        """提取營地圖片 URL（最多 10 張）。"""
        images: list[str] = []
        seen = set()

        for img in soup.find_all("img", src=True):
            src = img["src"]
            # 排除 icon、logo、avatar 等小圖
            if any(skip in src.lower() for skip in ["icon", "logo", "avatar", "pixel", "spacer", "1x1"]):
                continue
            # 補全相對路徑
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = f"{self.base_url}{src}"
            elif not src.startswith("http"):
                src = f"{self.base_url}/{src}"

            if src not in seen:
                seen.add(src)
                images.append(src)

            if len(images) >= 10:
                break

        return images

    def _extract_zones(self, soup: BeautifulSoup) -> list[dict]:
        """提取營位區域資訊（名稱、類型、價格）。"""
        zones: list[dict] = []

        # 尋找區域/營位相關的表格或列表
        # 常見結構: table 或 dl/div
        tables = soup.find_all("table")
        for table in tables:
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            header_lower = " ".join(headers).lower()
            # 確認是營位相關的表格（含有價格或區域相關字眼）
            if not any(kw in header_lower for kw in ["區", "營位", "價格", "價", "帳", "zone"]):
                continue

            for row in table.find_all("tr")[1:]:  # skip header
                cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                if len(cells) < 2:
                    continue

                zone: dict = {"name": cells[0]}

                # 解析各欄位
                for i, cell in enumerate(cells[1:], 1):
                    header = headers[i] if i < len(headers) else ""
                    price = _parse_int(cell)

                    if "平日" in header or "weekday" in header.lower():
                        zone["price_weekday"] = price
                    elif "假日" in header or "weekend" in header.lower():
                        zone["price_weekend"] = price
                    elif "連假" in header or "holiday" in header.lower():
                        zone["price_holiday"] = price
                    elif "價" in header and price:
                        zone.setdefault("price_weekday", price)
                    elif "包區" in cell or "包場" in cell:
                        zone["type"] = "包區"
                    elif "雨棚" in header or "雨棚" in cell:
                        zone["has_roof"] = True
                    elif "電" in header or "電源" in cell:
                        zone["has_power"] = True

                # 嘗試判斷地面類型
                row_text = " ".join(cells)
                for gt in ["草地", "碎石", "水泥", "棧板"]:
                    if gt in row_text:
                        zone["ground_type"] = gt
                        break

                zone.setdefault("type", "散帳")
                zones.append(zone)

        # Fallback: 非表格結構，找 div/section 列表
        if not zones:
            zone_sections = soup.select(
                ".zone, .area, .camp-area, .site-type, "
                ".product-item, .price-item"
            )
            for section in zone_sections:
                name = section.select_one(
                    ".zone-name, .area-name, .name, h3, h4, .title"
                )
                price_el = section.select_one(".price, .cost, .amount")
                if name:
                    zone = {
                        "name": name.get_text(strip=True),
                        "type": "散帳",
                    }
                    if price_el:
                        zone["price_weekday"] = _parse_int(price_el.get_text())
                    zones.append(zone)

        return zones

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """提取營地簡介。"""
        # 常見的簡介 selector
        for sel in [".description", ".intro", ".about", ".camp-intro",
                    "meta[name='description']", "meta[property='og:description']"]:
            el = soup.select_one(sel)
            if el:
                text = el.get("content") if el.name == "meta" else el.get_text(strip=True)
                if text and len(text) > 10:
                    return text[:500]  # truncate
        return ""

    def _extract_district(self, address: str, city: str) -> str:
        """從地址提取鄉鎮區名稱。"""
        if not address:
            return ""
        # 移除縣市，抓鄉/鎮/市/區
        addr = address.replace(city, "")
        match = re.search(r"([\u4e00-\u9fff]{1,3}(?:鄉|鎮|市|區))", addr)
        return match.group(1) if match else ""
