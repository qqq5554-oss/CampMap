import { useEffect } from "react";
import { useCampStore } from "../store/useCampStore";
import CampCard from "../components/Camp/CampCard";
import { Heart } from "lucide-react";

export default function FavoritesPage() {
  const { campsites, favorites, fetchCampsites, loading } = useCampStore();

  useEffect(() => {
    fetchCampsites();
  }, []);

  const favCamps = campsites.filter((c) => favorites.has(c.id));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
        <Heart size={24} className="text-red-500" /> 我的收藏
      </h1>

      {loading ? (
        <p className="text-gray-500">載入中...</p>
      ) : favCamps.length === 0 ? (
        <p className="text-gray-500 py-12 text-center">
          尚未收藏任何營地，前往搜尋頁面探索吧！
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {favCamps.map((camp) => (
            <CampCard key={camp.id} camp={camp} />
          ))}
        </div>
      )}
    </div>
  );
}
