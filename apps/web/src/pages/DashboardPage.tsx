import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";

type SearchResultItem = {
  name: string;
  quantity: string;
  unit: string | null;
  unit_price: string;
  category: string | null;
  brand: string | null;
  supplier_id: string | null;
  supplier_name: string | null;
  purchase_id: string;
  purchase_time: string;
};

type SearchResult = {
  query: string;
  count: number;
  items: SearchResultItem[];
};

type Phase = "loading" | "empty" | "success" | "error";

function formatPrice(unitPrice: string, unit: string | null): string {
  return `¥${unitPrice}${unit ? ` / ${unit}` : ""}`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function DashboardPage() {
  const [input, setInput] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");

  const { data, isFetching, error } = useQuery<SearchResult>({
    queryKey: ["prices", submittedQ],
    queryFn: () =>
      api.get<SearchResult>(
        `/api/v1/prices/search?q=${encodeURIComponent(submittedQ)}`
      ),
  });

  const phase: Phase = isFetching
    ? "loading"
    : error
      ? "error"
      : data && data.count === 0
        ? "empty"
        : "success";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittedQ(input.trim());
  };

  return (
    <div className="max-w-4xl">
      <h2 className="mb-4 text-xl font-bold">价格查询</h2>

      <form onSubmit={handleSubmit} className="mb-4 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入食材名（留空 = 看最近 50 条），如 番茄 / 鸡蛋 / 五花肉"
          className="flex-1 rounded border border-slate-300 px-3 py-1.5 text-sm"
        />
        <button
          type="submit"
          disabled={isFetching}
          className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:bg-slate-400"
        >
          {isFetching ? "搜索中…" : "搜索"}
        </button>
      </form>

      {phase === "loading" && (
        <p className="text-sm text-slate-500">查询中…</p>
      )}

      {phase === "error" && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          查询失败：{(error as ApiError).detail || "网络异常，请稍后重试"}
        </div>
      )}

      {phase === "empty" && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          {submittedQ === ""
            ? "暂无采购记录。去「记账」添加第一条。"
            : `未找到 "${submittedQ}" 的采购记录。可以换个关键词，或先去「记账」/「采购记录」录入。`}
        </div>
      )}

      {phase === "success" && data && (
        <>
          <p className="mb-2 text-xs text-slate-500">
            {submittedQ === ""
              ? `最近 ${data.count} 条采购记录（按时间倒序）`
              : `找到 ${data.count} 条匹配记录（按采购时间倒序）`}
          </p>
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">商品名</th>
                  <th className="px-3 py-2 text-right font-medium">单价</th>
                  <th className="px-3 py-2 text-left font-medium">店铺</th>
                  <th className="px-3 py-2 text-left font-medium">采购时间</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it, idx) => (
                  <tr key={`${it.purchase_id}-${idx}`} className="border-t border-slate-100">
                    <td className="px-3 py-1.5">{it.name}</td>
                    <td className="px-3 py-1.5 text-right font-mono tabular-nums">
                      {formatPrice(it.unit_price, it.unit)}
                    </td>
                    <td className="px-3 py-1.5">
                      {it.supplier_name ?? (
                        <span className="text-slate-400">—（未绑店铺）</span>
                      )}
                    </td>
                    <td className="px-3 py-1.5 text-slate-600">
                      {formatTime(it.purchase_time)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
