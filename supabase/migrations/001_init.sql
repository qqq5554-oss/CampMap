-- ============================================================
-- CampMap Database Schema
-- 露營聚合平台：搜尋日期+帳數+地區+設施 → 回傳各平台有空位營地
-- ============================================================

-- 1. campsites 營地主表
create table campsites (
  id              uuid primary key default gen_random_uuid(),
  name            text not null,
  slug            text not null,
  source_platform text not null check (source_platform in ('easycamp', 'camptrip', 'icamping', 'official')),
  source_url      text not null default '',
  source_id       text not null default '',
  description     text default '',
  city            text not null default '',
  district        text default '',
  address         text default '',
  lat             decimal(9,6),
  lng             decimal(9,6),
  altitude        integer,
  phone           text default '',
  website         text default '',
  images          text[] default '{}',
  facilities      text[] default '{}',
  tags            text[] default '{}',
  ground_type     text default '',
  min_price       integer,
  max_price       integer,
  rating          decimal(2,1),
  review_count    integer default 0,
  is_active       boolean default true,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now(),

  unique (source_platform, source_id)
);

-- 2. campsite_zones 營位區域
create table campsite_zones (
  id              uuid primary key default gen_random_uuid(),
  campsite_id     uuid not null references campsites(id) on delete cascade,
  zone_name       text not null,
  zone_type       text not null default '散帳' check (zone_type in ('散帳', '包區')),
  max_tents       integer,
  has_power       boolean default false,
  has_roof        boolean default false,
  ground_type     text default '',
  price_weekday   integer,
  price_weekend   integer,
  price_holiday   integer
);

-- 3. availability 空位快照
create table availability (
  id              uuid primary key default gen_random_uuid(),
  zone_id         uuid not null references campsite_zones(id) on delete cascade,
  date            date not null,
  status          text not null default 'unknown' check (status in ('available', 'full', 'limited', 'unknown')),
  remaining_spots integer,
  price           integer,
  scraped_at      timestamptz default now(),

  unique (zone_id, date)
);

-- 4. scrape_logs 爬蟲日誌
create table scrape_logs (
  id                    uuid primary key default gen_random_uuid(),
  platform              text not null,
  started_at            timestamptz not null default now(),
  finished_at           timestamptz,
  status                text not null default 'success' check (status in ('success', 'partial', 'failed')),
  campsites_updated     integer default 0,
  availability_updated  integer default 0,
  error_message         text
);

-- ============================================================
-- Indexes
-- ============================================================

create index idx_campsites_city            on campsites (city);
create index idx_campsites_source_platform on campsites (source_platform);
create index idx_campsites_is_active       on campsites (is_active);
create index idx_campsites_slug            on campsites (slug);

create index idx_availability_date         on availability (date);
create index idx_availability_status       on availability (status);
create index idx_availability_zone_date    on availability (zone_id, date);

create index idx_zones_campsite_id         on campsite_zones (campsite_id);

-- GIN indexes for array searching
create index idx_campsites_facilities      on campsites using gin (facilities);
create index idx_campsites_tags            on campsites using gin (tags);

-- ============================================================
-- VIEW: search_available_camps
-- 前端搜尋查詢用，JOIN 營地 + 區域 + 空位
-- ============================================================

create view search_available_camps as
select
  c.id              as campsite_id,
  c.name,
  c.slug,
  c.source_platform,
  c.source_url,
  c.city,
  c.district,
  c.address,
  c.lat,
  c.lng,
  c.altitude,
  c.images,
  c.facilities,
  c.tags,
  c.min_price,
  c.max_price,
  c.rating,
  c.review_count,
  z.id              as zone_id,
  z.zone_name,
  z.zone_type,
  z.max_tents,
  z.has_power,
  z.has_roof,
  z.ground_type,
  z.price_weekday,
  z.price_weekend,
  z.price_holiday,
  a.date,
  a.status,
  a.remaining_spots,
  a.price           as date_price,
  a.scraped_at
from campsites c
join campsite_zones z on z.campsite_id = c.id
join availability a   on a.zone_id = z.id
where c.is_active = true
  and a.status in ('available', 'limited');

-- ============================================================
-- Row Level Security
-- ============================================================

alter table campsites      enable row level security;
alter table campsite_zones enable row level security;
alter table availability   enable row level security;
alter table scrape_logs    enable row level security;

-- Public read access
create policy "Public read campsites"      on campsites      for select using (true);
create policy "Public read campsite_zones" on campsite_zones for select using (true);
create policy "Public read availability"   on availability   for select using (true);
create policy "Public read scrape_logs"    on scrape_logs    for select using (true);

-- ============================================================
-- Trigger: auto-update updated_at on campsites
-- ============================================================

create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_campsites_updated_at
  before update on campsites
  for each row execute function update_updated_at();
