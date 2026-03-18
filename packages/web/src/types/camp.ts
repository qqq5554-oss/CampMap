// ============================================================
// 資料庫型別定義 — 對應 supabase/migrations/001_init.sql
// ============================================================

export type SourcePlatform = "easycamp" | "camptrip" | "icamping" | "official";
export type ZoneType = "散帳" | "包區";
export type AvailabilityStatus = "available" | "full" | "limited" | "unknown";
export type ScrapeStatus = "success" | "partial" | "failed";

/** campsites 營地主表 */
export interface Campsite {
  id: string;
  name: string;
  slug: string;
  source_platform: SourcePlatform;
  source_url: string;
  source_id: string;
  description: string;
  city: string;
  district: string;
  address: string;
  lat: number | null;
  lng: number | null;
  altitude: number | null;
  phone: string;
  website: string;
  images: string[];
  facilities: string[];
  tags: string[];
  ground_type: string;
  min_price: number | null;
  max_price: number | null;
  rating: number | null;
  review_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** campsite_zones 營位區域 */
export interface CampsiteZone {
  id: string;
  campsite_id: string;
  zone_name: string;
  zone_type: ZoneType;
  max_tents: number | null;
  has_power: boolean;
  has_roof: boolean;
  ground_type: string;
  price_weekday: number | null;
  price_weekend: number | null;
  price_holiday: number | null;
}

/** availability 空位快照 */
export interface Availability {
  id: string;
  zone_id: string;
  date: string;
  status: AvailabilityStatus;
  remaining_spots: number | null;
  price: number | null;
  scraped_at: string;
}

/** scrape_logs 爬蟲日誌 */
export interface ScrapeLog {
  id: string;
  platform: string;
  started_at: string;
  finished_at: string | null;
  status: ScrapeStatus;
  campsites_updated: number;
  availability_updated: number;
  error_message: string | null;
}

/** search_available_camps VIEW 回傳型別 */
export interface SearchAvailableCamp {
  campsite_id: string;
  name: string;
  slug: string;
  source_platform: SourcePlatform;
  source_url: string;
  city: string;
  district: string;
  address: string;
  lat: number | null;
  lng: number | null;
  altitude: number | null;
  images: string[];
  facilities: string[];
  tags: string[];
  min_price: number | null;
  max_price: number | null;
  rating: number | null;
  review_count: number;
  zone_id: string;
  zone_name: string;
  zone_type: ZoneType;
  max_tents: number | null;
  has_power: boolean;
  has_roof: boolean;
  ground_type: string;
  price_weekday: number | null;
  price_weekend: number | null;
  price_holiday: number | null;
  date: string;
  status: AvailabilityStatus;
  remaining_spots: number | null;
  date_price: number | null;
  scraped_at: string;
}
