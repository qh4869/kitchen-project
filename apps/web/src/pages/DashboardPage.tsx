import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
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
  purchase_item_id: string;
  purchase_time: string;
  receipt_image_path: string | null;
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
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);

  const { data, isFetching, error } = useQuery<SearchResult>({
    queryKey: ["prices", submittedQ],
    queryFn: () =>
      api.get<SearchResult>(
        `/api/v1/prices/search?q=${encodeURIComponent(submittedQ)}`
      ),
  });

  const qc = useQueryClient();

  const navigate = useNavigate();

  const handleEdit = (purchaseId: string) => {
    if (window.confirm("编辑将打开该记录所属采购单的全部内容，是否继续？")) {
      navigate(`/entry?edit=${purchaseId}`);
    }
  };

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/purchase-items/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prices"] });
    },
    onError: (err: ApiError) => {
      alert(err.detail || "删除失败，请稍后再试");
    },
  });

  const handleDelete = (id: string, name: string) => {
    if (window.confirm(`确定删除「${name}」这条记录？`)) {
      deleteMut.mutate(id);
    }
  };

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
            : `未找到 "${submittedQ}" 的采购记录。可以换个关键词，或去「记账」补录。`}
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
                  <th className="px-3 py-2 text-right font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={it.purchase_item_id} className="border-t border-slate-100">
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
                    <td className="px-3 py-1.5 text-right whitespace-nowrap">
                      {it.receipt_image_path && (
                        <button
                          type="button"
                          title="查看照片"
                          className="text-xs text-slate-500 hover:text-slate-700 disabled:opacity-50 mr-2"
                          onClick={() => setPhotoUrl(`/static/${it.receipt_image_path}`)}
                          disabled={deleteMut.isPending}
                        >
                          📷
                        </button>
                      )}
                      <button
                        type="button"
                        title="编辑"
                        className="text-xs text-slate-500 hover:text-slate-700 disabled:opacity-50 mr-2"
                        onClick={() => handleEdit(it.purchase_id)}
                        disabled={deleteMut.isPending}
                      >
                        ✎
                      </button>
                      <button
                        type="button"
                        title="删除"
                        className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
                        onClick={() => handleDelete(it.purchase_item_id, it.name)}
                        disabled={deleteMut.isPending}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {photoUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
          onClick={() => setPhotoUrl(null)}
        >
          <button
            type="button"
            className="absolute right-4 top-4 text-3xl text-white/80 hover:text-white"
            onClick={() => setPhotoUrl(null)}
            aria-label="关闭"
          >
            ×
          </button>
          <img
            src={photoUrl}
            alt="原始照片"
            className="max-h-[90vh] max-w-[90vw] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
