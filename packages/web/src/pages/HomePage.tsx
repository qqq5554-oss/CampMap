import { useNavigate } from "react-router-dom";
import { MapPin, Search, Tent } from "lucide-react";
import { useState } from "react";
import { useCampStore } from "../store/useCampStore";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const setKeyword = useCampStore((s) => s.setKeyword);
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setKeyword(query);
    navigate("/search");
  };

  return (
    <div className="flex flex-col items-center justify-center py-20 gap-8">
      <div className="text-center">
        <Tent size={64} className="mx-auto text-green-600 mb-4" />
        <h1 className="text-4xl font-bold text-gray-800">CampMap</h1>
        <p className="text-lg text-gray-500 mt-2">
          一站搜尋全台露營地 — 比價、選位、出發！
        </p>
      </div>

      <form onSubmit={handleSearch} className="w-full max-w-lg flex gap-2">
        <div className="relative flex-1">
          <Search
            size={18}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="搜尋營地名稱或地區..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500 text-lg"
          />
        </div>
        <button
          type="submit"
          className="px-8 py-3 bg-green-600 text-white rounded-xl hover:bg-green-700 transition text-lg"
        >
          搜尋
        </button>
      </form>

      <div className="flex gap-6 text-sm text-gray-500 mt-4">
        <span className="flex items-center gap-1">
          <MapPin size={14} /> 聚合三大平台
        </span>
        <span>露營樂 / 玩露趣 / 愛露營</span>
      </div>
    </div>
  );
}
