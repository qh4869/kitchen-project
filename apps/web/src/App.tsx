import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import EntryPage from "./pages/EntryPage";
import SuppliersPage from "./pages/SuppliersPage";
import DashboardPage from "./pages/DashboardPage";
import MobileNav from "./components/MobileNav";
import { navItems } from "./nav-items";

export default function App() {
  const location = useLocation();
  return (
    <>
      <MobileNav currentPath={location.pathname} />

      <div className="flex min-h-screen">
        <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white p-4 md:block">
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
                      ? "bg-emerald-50 font-medium text-emerald-700"
                      : "text-slate-600 hover:bg-slate-100"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="flex-1 overflow-x-hidden p-4 md:p-6">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/entry" element={<EntryPage />} />
            <Route path="/suppliers" element={<SuppliersPage />} />
          </Routes>
        </main>
      </div>
    </>
  );
}
