import { useCampStore } from "../../store/useCampStore";

const SOURCES = [
  { value: "", label: "全部平台" },
  { value: "easycamp", label: "露營樂" },
  { value: "camptrip", label: "玩露趣" },
  { value: "icamping", label: "愛露營" },
];

export default function SourceFilter() {
  const { source, setSource, fetchCampsites } = useCampStore();

  return (
    <div className="flex gap-2 flex-wrap">
      {SOURCES.map((s) => (
        <button
          key={s.value}
          onClick={() => {
            setSource(s.value);
            fetchCampsites();
          }}
          className={`px-4 py-1.5 rounded-full text-sm transition ${
            source === s.value
              ? "bg-green-600 text-white"
              : "bg-gray-200 text-gray-700 hover:bg-gray-300"
          }`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
