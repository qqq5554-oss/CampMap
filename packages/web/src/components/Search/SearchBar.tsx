import { Search } from "lucide-react";
import { useCampStore } from "../../store/useCampStore";

export default function SearchBar() {
  const { keyword, setKeyword, fetchCampsites } = useCampStore();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchCampsites();
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="relative flex-1">
        <Search
          size={18}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
        />
        <input
          type="text"
          placeholder="搜尋營地名稱..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
        />
      </div>
      <button
        type="submit"
        className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
      >
        搜尋
      </button>
    </form>
  );
}
