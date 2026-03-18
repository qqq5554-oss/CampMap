import { useEffect } from "react";
import { useCampStore } from "../store/useCampStore";
import SearchBar from "../components/Search/SearchBar";
import SourceFilter from "../components/Filter/SourceFilter";
import CampCard from "../components/Camp/CampCard";
import CampMap from "../components/Map/CampMap";
import { Loader2 } from "lucide-react";

export default function SearchPage() {
  const { campsites, loading, fetchCampsites } = useCampStore();

  useEffect(() => {
    fetchCampsites();
  }, []);

  return (
    <div className="space-y-6">
      <SearchBar />
      <SourceFilter />

      <CampMap campsites={campsites} />

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="animate-spin text-green-600" size={32} />
        </div>
      ) : campsites.length === 0 ? (
        <p className="text-center text-gray-500 py-12">
          尚無營地資料，請先執行爬蟲或調整搜尋條件。
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {campsites.map((camp) => (
            <CampCard key={camp.id} camp={camp} />
          ))}
        </div>
      )}
    </div>
  );
}
