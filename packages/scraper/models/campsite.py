from dataclasses import dataclass, field, asdict
from datetime import datetime, date


@dataclass
class Campsite:
    """營地主表資料結構。"""

    name: str
    slug: str
    source_platform: str  # easycamp | camptrip | icamping | official
    source_url: str = ""
    source_id: str = ""
    description: str = ""
    city: str = ""
    district: str = ""
    address: str = ""
    lat: float | None = None
    lng: float | None = None
    altitude: int | None = None
    phone: str = ""
    website: str = ""
    images: list[str] = field(default_factory=list)
    facilities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    ground_type: str = ""
    min_price: int | None = None
    max_price: int | None = None
    rating: float | None = None
    review_count: int = 0
    is_active: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CampsiteZone:
    """營位區域資料結構。"""

    campsite_id: str
    zone_name: str
    zone_type: str = "散帳"  # 散帳 | 包區
    max_tents: int | None = None
    has_power: bool = False
    has_roof: bool = False
    ground_type: str = ""
    price_weekday: int | None = None
    price_weekend: int | None = None
    price_holiday: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Availability:
    """空位快照資料結構。"""

    zone_id: str
    date: str  # ISO format date string (YYYY-MM-DD)
    status: str = "unknown"  # available | full | limited | unknown
    remaining_spots: int | None = None
    price: int | None = None
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScrapeLog:
    """爬蟲日誌資料結構。"""

    platform: str
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: str | None = None
    status: str = "success"  # success | partial | failed
    campsites_updated: int = 0
    availability_updated: int = 0
    error_message: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
