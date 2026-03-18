from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Campsite:
    """統一營地資料結構。"""

    name: str
    source: str  # easycamp | camptrip | icamping
    location: str = ""
    lat: float | None = None
    lng: float | None = None
    price_min: int | None = None
    price_max: int | None = None
    altitude: int | None = None
    facilities: list[str] = field(default_factory=list)
    image_url: str = ""
    url: str = ""
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)
