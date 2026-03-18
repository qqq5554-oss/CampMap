create table if not exists campsites (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  source text not null,  -- easycamp | camptrip | icamping
  location text default '',
  lat double precision,
  lng double precision,
  price_min integer,
  price_max integer,
  altitude integer,
  facilities jsonb default '[]'::jsonb,
  image_url text default '',
  url text default '',
  updated_at timestamptz default now(),

  unique (source, name)
);

create index if not exists idx_campsites_source on campsites (source);
create index if not exists idx_campsites_location on campsites using gin (to_tsvector('simple', location));

-- Enable Row Level Security
alter table campsites enable row level security;

-- Allow anonymous reads
create policy "Allow public read" on campsites
  for select using (true);
