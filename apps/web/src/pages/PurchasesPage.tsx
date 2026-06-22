import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";

type PurchaseList = {
  id: string;
  supplier_id: string | null;
  total_amount: string | null;
  purchase_time: string;
  manual_adjustment: boolean;
  item_count: number;
  created_at: string;
};

type Supplier = { id: string; name: string };

function formatDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate()
  ).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(
    d.getMinutes()
  ).padStart(2, "0")}`;
}

export default function PurchasesPage() {
  const { data: purchases, isLoading, error } = useQuery<PurchaseList[]>({
    queryKey: ["purchases"],
    queryFn: () => api.get<PurchaseList[]>("/api/v1/purchases"),
  });

  const { data: suppliers } = useQuery<Supplier[]>({
    queryKey: ["suppliers"],
    queryFn: () => api.get<Supplier[]>("/api/v1/suppliers"),
  });

  const supplierName = (id: string | null) =>
    id ? suppliers?.find((s) => s.id === id)?.name ?? "—" : "—";

  return (
    <div className="max-w-5xl">
      <header className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-bold">采购记录</h2>
      </header>

      {isLoading && <p className="text-slate-500">加载中…</p>}
      {error && <p className="text-red-600">加载失败：{(error as ApiError).detail}</p>}

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-600">
            <tr>
              <th className="px-4 py-2 font-medium">时间</th>
              <th className="px-4 py-2 font-medium">供应商</th>
              <th className="px-4 py-2 text-right font-medium">明细数</th>
              <th className="px-4 py-2 text-right font-medium">总额</th>
              <th className="px-4 py-2 font-medium">标记</th>
            </tr>
          </thead>
          <tbody>
            {purchases?.map((p) => (
              <tr key={p.id} className="border-t border-slate-100">
                <td className="px-4 py-2">{formatDate(p.purchase_time)}</td>
                <td className="px-4 py-2">{supplierName(p.supplier_id)}</td>
                <td className="px-4 py-2 text-right">{p.item_count}</td>
                <td className="px-4 py-2 text-right">
                  {p.total_amount ? `¥${p.total_amount}` : "—"}
                </td>
                <td className="px-4 py-2">
                  {p.manual_adjustment && (
                    <span className="rounded bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                      人工修正
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {purchases && purchases.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                  暂无采购记录。点击左侧"记账"添加第一条。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
