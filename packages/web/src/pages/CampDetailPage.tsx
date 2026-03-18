import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, ExternalLink, MapPin, Heart } from "lucide-react";
import type { Campsite } from "../types/campsite";
import { supabase } from "../services/supabase";
import { useCampStore } from "../store/useCampStore";
import CampMap from "../components/Map/CampMap";

export default function CampDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [camp, setCamp] = useState<Campsite | null>(null);
  const { favorites, toggleFavorite } = useCampStore();

  useEffect(() => {
    if (!id) return;
    supabase
      .from("campsites")
      .select("*")
      .eq("id", id)
      .single()
      .then(({ data }) => setCamp(data as Campsite | null));
  }, [id]);

  if (!camp) {
    return <p className="text-center py-12 text-gray-500">載入中...</p>;
  }

  const isFav = favorites.has(camp.id);

  return (
    <div className="space-y-6">
      <Link to="/search" className="inline-flex items-center gap-1 text-green-600 hover:underline">
        <ArrowLeft size={16} /> 回到搜尋
      </Link>

      <div className="bg-white rounded-xl shadow-sm border p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{camp.name}</h1>
            <p className="text-gray-500 flex items-center gap-1 mt-1">
              <MapPin size={16} /> {camp.location || "未提供位置"}
            </p>
          </div>
          <button onClick={() => toggleFavorite(camp.id)} className="p-2">
            <Heart
              size={24}
              className={isFav ? "fill-red-500 text-red-500" : "text-gray-400"}
            />
          </button>
        </div>

        {camp.price_min != null && (
          <p className="text-xl text-green-700 font-bold mt-4">
            NT$ {camp.price_min.toLocaleString()}
            {camp.price_max != null && ` ~ ${camp.price_max.toLocaleString()}`}
          </p>
        )}

        {camp.altitude != null && (
          <p className="text-sm text-gray-500 mt-2">海拔 {camp.altitude} 公尺</p>
        )}

        {camp.facilities.length > 0 && (
          <div className="mt-4 flex gap-2 flex-wrap">
            {camp.facilities.map((f) => (
              <span key={f} className="bg-green-50 text-green-700 text-xs px-3 py-1 rounded-full">
                {f}
              </span>
            ))}
          </div>
        )}

        <a
          href={camp.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-6 inline-flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
        >
          前往原站訂位 <ExternalLink size={16} />
        </a>
      </div>

      {camp.lat != null && camp.lng != null && <CampMap campsites={[camp]} />}
    </div>
  );
}
