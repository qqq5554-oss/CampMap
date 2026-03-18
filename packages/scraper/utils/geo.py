import urllib.request
import json


def geocode(address: str) -> tuple[float, float] | None:
    """使用 Nominatim 將地址轉為經緯度。"""
    encoded = urllib.parse.quote(address)
    url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1"
    req = urllib.request.Request(url, headers={"User-Agent": "CampMap/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None
