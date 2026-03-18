import { Outlet, Link, useLocation } from "react-router-dom";
import { MapPin, Search, Heart } from "lucide-react";

export default function Layout() {
  const { pathname } = useLocation();

  const navItems = [
    { to: "/", icon: MapPin, label: "首頁" },
    { to: "/search", icon: Search, label: "搜尋" },
    { to: "/favorites", icon: Heart, label: "收藏" },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-green-700 text-white shadow-md">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold flex items-center gap-2">
            <MapPin size={24} />
            CampMap
          </Link>
          <nav className="flex gap-4">
            {navItems.map(({ to, icon: Icon, label }) => (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-1 px-3 py-1 rounded-md transition ${
                  pathname === to
                    ? "bg-green-600"
                    : "hover:bg-green-600/50"
                }`}
              >
                <Icon size={16} />
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>

      <footer className="bg-gray-800 text-gray-400 text-center py-4 text-sm">
        CampMap &copy; 2026 — 露營版 Trivago
      </footer>
    </div>
  );
}
