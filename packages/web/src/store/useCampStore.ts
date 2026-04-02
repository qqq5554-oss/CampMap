import { create } from "zustand";
import type { Campsite } from "../types/campsite";
import { supabase } from "../services/supabase";

interface CampState {
  campsites: Campsite[];
  favorites: Set<string>;
  loading: boolean;
  error: string | null;
  keyword: string;
  source: string;
  setKeyword: (keyword: string) => void;
  setSource: (source: string) => void;
  fetchCampsites: () => Promise<void>;
  toggleFavorite: (id: string) => void;
}

export const useCampStore = create<CampState>((set, get) => ({
  campsites: [],
  favorites: new Set(
    JSON.parse(localStorage.getItem("campmap_favs") ?? "[]"),
  ),
  loading: false,
  error: null,
  keyword: "",
  source: "",

  setKeyword: (keyword) => set({ keyword }),
  setSource: (source) => set({ source }),

  fetchCampsites: async () => {
    set({ loading: true, error: null });
    try {
      let query = supabase.from("campsites").select("*");
      const { keyword, source } = get();
      if (keyword) query = query.ilike("name", `%${keyword}%`);
      if (source) query = query.eq("source", source);

      const { data, error } = await query.order("updated_at", {
        ascending: false,
      });
      if (error) {
        set({ error: error.message, loading: false });
        return;
      }
      set({ campsites: (data as Campsite[]) ?? [], loading: false });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Failed to fetch campsites",
        loading: false,
      });
    }
  },

  toggleFavorite: (id) => {
    const favs = new Set(get().favorites);
    if (favs.has(id)) favs.delete(id);
    else favs.add(id);
    localStorage.setItem("campmap_favs", JSON.stringify([...favs]));
    set({ favorites: favs });
  },
}));
