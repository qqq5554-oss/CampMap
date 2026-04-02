import { Heart, ExternalLink, MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import type { Campsite } from "../../types/campsite";
import { useCampStore } from "../../store/useCampStore";

interface Props {
  camp: Campsite;
}

const SOURCE_LABELS: Record<string, string> = {
  easycamp: "露營樂",
  camptrip: "玩露趣",
  icamping: "愛露營",
};

export default function CampCard({ camp }: Props) {
  const { favorites, toggleFavorite } = useCampStore();
  const isFav = favorites.has(camp.id);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition">
      <div className="h-40 bg-gray-200 relative">
        {camp.images.length > 0 ? (
          <img
            src={camp.images[0]}
            alt={camp.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <MapPin size={48} />
          </div>
        )}
        <span className="absolute top-2 left-2 bg-green-600 text-white text-xs px-2 py-0.5 rounded">
          {SOURCE_LABELS[camp.source_platform] ?? camp.source_platform}
        </span>
        <button
          onClick={() => toggleFavorite(camp.id)}
          className="absolute top-2 right-2 p-1.5 bg-white/80 rounded-full hover:bg-white transition"
        >
          <Heart
            size={18}
            className={isFav ? "fill-red-500 text-red-500" : "text-gray-400"}
          />
        </button>
      </div>
      <div className="p-4">
        <Link to={`/camp/${camp.id}`} className="font-semibold text-gray-800 hover:text-green-700">
          {camp.name}
        </Link>
        <p className="text-sm text-gray-500 mt-1 flex items-center gap-1">
          <MapPin size={14} /> {camp.address || `${camp.city}${camp.district}` || "未提供位置"}
        </p>
        {camp.min_price != null && (
          <p className="text-green-700 font-bold mt-2">
            NT$ {camp.min_price.toLocaleString()}
            {camp.max_price != null && ` ~ ${camp.max_price.toLocaleString()}`}
          </p>
        )}
        <a
          href={camp.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-flex items-center gap-1 text-sm text-green-600 hover:underline"
        >
          前往訂位 <ExternalLink size={14} />
        </a>
      </div>
    </div>
  );
}
