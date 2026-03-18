export interface Campsite {
  id: string;
  name: string;
  source: "easycamp" | "camptrip" | "icamping";
  location: string;
  lat: number | null;
  lng: number | null;
  price_min: number | null;
  price_max: number | null;
  altitude: number | null;
  facilities: string[];
  image_url: string;
  url: string;
  updated_at: string;
}
