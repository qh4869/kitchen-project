import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";

type Supplier = {
  id: string;
  name: string;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  business_hours: string[] | null;
  contact_info: string | null;
  preferences: string[] | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

const QK = ["suppliers"] as const;

export default function SuppliersPage() {
  const [query, setQuery] = useState("");
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery<Supplier[]>({
    queryKey: [...QK, query],
    queryFn: () =>
      api.get<Supplier[]>(
        query ? `/api/v1/suppliers?q=${encodeURIComponent(query)}` : "/api/v1/suppliers"
      ),
  });

  const createMut = useMutation({
    mutationFn: (body: Partial<Supplier>) => api.post<Supplier>("/api/v1/suppliers", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK }),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/suppliers/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK }),
  });

  const [draft, setDraft] = useState({ name: "", address: "", preferences: "", notes: "" });

  const submit = () => {
    if (!draft.name.trim()) return;
    createMut.mutate({
      name: draft.name.trim(),
      address: draft.address.trim() || null,
      preferences: draft.preferences
        .split(/[，,]/)
        .map((s) => s.trim())
        .filter(Boolean),
      notes: draft.notes.trim() || null,
    });
    setDraft({ name: "", address: "", preferences: "", notes: "" });
  };

  return (
    <div className="max-w-5xl">
      <header className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-bold">供应商</h2>
        <input
          className="rounded border border-slate-300 px-3 py-1.5 text-sm"
          placeholder="搜索名称 / 地址 / 备注"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </header>

      <section className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">新建供应商</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <Input label="名称 *" value={draft.name} onChange={(v) => setDraft({ ...draft, name: v })} />
          <Input label="地址" value={draft.address} onChange={(v) => setDraft({ ...draft, address: v })} />
          <Input
            label="偏好标签 (逗号分隔)"
            value={draft.preferences}
            onChange={(v) => setDraft({ ...draft, preferences: v })}
            placeholder="蔬菜便宜, 海鲜新鲜"
          />
          <Input label="备注" value={draft.notes} onChange={(v) => setDraft({ ...draft, notes: v })} />
        </div>
        <div className="mt-3">
          <button
            className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            onClick={submit}
            disabled={!draft.name.trim() || createMut.isPending}
          >
            {createMut.isPending ? "保存中…" : "保存"}
          </button>
          {createMut.isError && (
            <p className="mt-2 text-sm text-red-600">保存失败：{(createMut.error as ApiError).detail}</p>
          )}
        </div>
      </section>

      {isLoading && <p className="text-slate-500">加载中…</p>}
      {error && <p className="text-red-600">加载失败：{(error as ApiError).detail}</p>}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {data?.map((s) => (
          <article key={s.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex items-start justify-between">
              <h4 className="font-semibold">{s.name}</h4>
              <button
                className="text-xs text-red-500 hover:underline"
                onClick={() => deleteMut.mutate(s.id)}
              >
                删除
              </button>
            </div>
            {s.address && <p className="mt-1 text-sm text-slate-600">{s.address}</p>}
            {s.preferences && s.preferences.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {s.preferences.map((tag) => (
                  <span key={tag} className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                    {tag}
                  </span>
                ))}
              </div>
            )}
            {s.notes && <p className="mt-2 text-xs text-slate-500">{s.notes}</p>}
          </article>
        ))}
        {data && data.length === 0 && (
          <p className="col-span-full text-slate-500">暂无供应商，请先新建。</p>
        )}
      </div>
    </div>
  );
}

function Input({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-600">{label}</span>
      <input
        className="rounded border border-slate-300 px-2 py-1"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
