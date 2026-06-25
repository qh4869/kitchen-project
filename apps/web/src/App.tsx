import { NavLink, Route, Routes } from "react-router-dom";
import SuppliersPage from "./pages/SuppliersPage";
import PurchasesPage from "./pages/PurchasesPage";
import EntryPage from "./pages/EntryPage";
import DashboardPage from "./pages/DashboardPage";

const navItems = [
  { to: "/", label: "采购记录", icon: "📋", end: true, page: "purchases" },
  { to: "/entry", label: "记账", icon: "📷", end: false, page: "entry" },
  { to: "/suppliers", label: "供应商", icon: "🏪", end: false, page: "suppliers" },
  { to: "/dashboard", label: "价格仪表盘", icon: "💰", end: false, page: "dashboard" },
];

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-16 shrink-0 border-r border-slate-200 bg-white p-2">
        <div
          className="mb-4 px-2 py-2 text-center text-2xl"
          title="烹饪助手 · 智慧采购"
        >
          🍳
        </div>
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              title={item.label}
              className={({ isActive }) =>
                `flex justify-center rounded-md px-2 py-3 text-xl ${
                  isActive
                    ? "bg-emerald-50 text-emerald-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {item.icon}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-x-auto p-3 md:p-6">
        <Routes>
          <Route path="/" element={<PurchasesPage />} />
          <Route path="/entry" element={<EntryPage />} />
          <Route path="/suppliers" element={<SuppliersPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </div>
  );
}
