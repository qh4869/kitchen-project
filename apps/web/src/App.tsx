import { NavLink, Route, Routes } from "react-router-dom";
import SuppliersPage from "./pages/SuppliersPage";
import PurchasesPage from "./pages/PurchasesPage";
import UploadPage from "./pages/UploadPage";
import DashboardPage from "./pages/DashboardPage";

const navItems = [
  { to: "/", label: "采购记录", end: true, page: "purchases" },
  { to: "/upload", label: "拍照记账", end: false, page: "upload" },
  { to: "/suppliers", label: "供应商", end: false, page: "suppliers" },
  { to: "/dashboard", label: "价格仪表盘", end: false, page: "dashboard" },
];

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 border-r border-slate-200 bg-white p-4">
        <div className="mb-6 px-2">
          <h1 className="text-lg font-bold">烹饪助手</h1>
          <p className="text-xs text-slate-500">智慧采购 · v0.1</p>
        </div>
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm ${
                  isActive
                    ? "bg-emerald-50 text-emerald-700 font-medium"
                    : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-x-hidden p-6">
        <Routes>
          <Route path="/" element={<PurchasesPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/suppliers" element={<SuppliersPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </div>
  );
}
