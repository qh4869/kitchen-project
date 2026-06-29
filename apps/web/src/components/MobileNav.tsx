import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { navItems } from "../nav-items";

type Props = { currentPath: string };

const TITLE_MAP: Record<string, string> = {
  "/": "价格查询",
  "/entry": "记账",
  "/suppliers": "供应商管理",
};

export default function MobileNav({ currentPath }: Props) {
  const [open, setOpen] = useState(false);
  const title = TITLE_MAP[currentPath] ?? "";

  // Close drawer whenever the route changes (covers browser back/forward
  // and any programmatic navigation that doesn't go through NavLink onClick).
  useEffect(() => {
    setOpen(false);
  }, [currentPath]);

  // ESC to close + lock body scroll while drawer is open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      {/* Top app bar — only on mobile */}
      <header className="md:hidden sticky top-0 z-30 flex h-[42px] items-center gap-2 border-b border-slate-200 bg-white px-3.5">
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="打开菜单"
          className="px-1 text-xl leading-none"
        >
          ☰
        </button>
        <span className="flex-1 text-[13px] font-semibold text-slate-900">
          {title}
        </span>
      </header>

      {/* Drawer + overlay — only rendered when open */}
      {open && (
        <div className="md:hidden fixed inset-0 z-50">
          {/* Dimmed backdrop; click closes */}
          <div
            className="absolute inset-0 bg-black/45"
            onClick={() => setOpen(false)}
          />

          {/* Drawer panel */}
          <aside className="absolute left-0 top-0 flex h-full w-3/4 max-w-[320px] animate-[slideIn_.2s_ease-out] flex-col bg-white p-3.5 shadow-xl">
            {/* Brand block — visually mirrors the PC sidebar */}
            <div className="mb-4 border-b border-slate-100 px-1 pb-3">
              <h1 className="text-base font-bold">烹饪助手</h1>
              <p className="text-xs text-slate-500">智慧采购 · v0.1</p>
            </div>

            {/* Nav links — emerald active state matches PC sidebar */}
            <nav className="flex flex-col gap-0.5">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={() => setOpen(false)}
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

            <div className="mt-auto px-1 py-2 text-[10px] text-slate-400">
              v0.1 · 2026
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
