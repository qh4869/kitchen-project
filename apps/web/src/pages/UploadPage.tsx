import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import ImageUploader from "../components/ImageUploader";
import ItemEditor, { type Item } from "../components/ItemEditor";

type Supplier = { id: string; name: string };
type OcrItem = {
  name: string;
  quantity?: string | number | null;
  unit?: string | null;
  unit_price?: string | number | null;
  category?: string | null;
  brand?: string | null;
};
type OcrResult = {
  image_key: string;
  supplier_name: string | null;
  purchase_time: string | null;
  total_amount: string | null;
  items: OcrItem[];
  raw_llm_output: Record<string, unknown>;
  provider: string;
};

type Phase = "idle" | "uploaded" | "recognizing" | "recognized" | "failed" | "saving" | "saved";

const num = (v: unknown): string =>
  v === null || v === undefined || v === "" ? "" : String(v);

const itemFromOcr = (it: OcrItem): Item => ({
  name: it.name ?? "",
  quantity: num(it.quantity),
  unit: it.unit ?? "",
  unit_price: num(it.unit_price),
  category: it.category ?? "",
  brand: it.brand ?? "",
});

export default function UploadPage() {
  const qc = useQueryClient();
  const [phase, setPhase] = useState<Phase>("idle");
  const [imageKey, setImageKey] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [supplierId, setSupplierId] = useState<string>("");
  const [purchaseTime, setPurchaseTime] = useState<string>("");
  const [totalAmount, setTotalAmount] = useState<string>("");
  const [items, setItems] = useState<Item[]>([]);
  const [rawLlm, setRawLlm] = useState<Record<string, unknown>>({});
  const [dirty, setDirty] = useState(false);

  const { data: suppliers } = useQuery<Supplier[]>({
    queryKey: ["suppliers"],
    queryFn: () => api.get<Supplier[]>("/api/v1/suppliers"),
  });

  const ocrMut = useMutation({
    mutationFn: async (key: string) =>
      api.post<OcrResult>("/api/v1/ocr/extract", { image_key: key }),
    onMutate: () => {
      setPhase("recognizing");
      setErrorMsg(null);
    },
    onSuccess: (r) => {
      setImageKey(r.image_key);
      setRawLlm(r.raw_llm_output);
      setItems(r.items.map(itemFromOcr));
      setTotalAmount(num(r.total_amount));
      setPhase("recognized");
      if (r.items.length === 0) {
        setErrorMsg("未识别到任何商品信息，请重拍或改手工录入");
        setPhase("failed");
      }
    },
    onError: (e: ApiError) => {
      setErrorMsg(ocrErrorText(e));
      setPhase("failed");
    },
  });

  const saveMut = useMutation({
    mutationFn: async () => {
      const body = {
        image_key: imageKey,
        supplier_id: supplierId || null,
        purchase_time: purchaseTime ? new Date(purchaseTime).toISOString() : null,
        total_amount: totalAmount || null,
        ocr_raw: rawLlm,
        manual_adjustment: dirty,
        items: items
          .filter((i) => i.name.trim() && i.unit_price)
          .map((i) => ({
            name: i.name.trim(),
            quantity: i.quantity || "1",
            unit: i.unit || null,
            unit_price: i.unit_price,
            category: i.category || null,
            brand: i.brand || null,
          })),
      };
      return api.post("/api/v1/purchases/from-ocr", body);
    },
    onMutate: () => {
      setPhase("saving");
      setErrorMsg(null);
    },
    onSuccess: () => {
      setPhase("saved");
      qc.invalidateQueries({ queryKey: ["purchases"] });
    },
    onError: (e: ApiError) => {
      setErrorMsg(`保存失败：${e.detail}`);
      setPhase("recognized");
    },
  });

  const reset = () => {
    setPhase("idle");
    setImageKey(null);
    setPreviewUrl(null);
    setErrorMsg(null);
    setSupplierId("");
    setPurchaseTime("");
    setTotalAmount("");
    setItems([]);
    setRawLlm({});
    setDirty(false);
  };

  const edit = (next: Item[]) => {
    setItems(next);
    setDirty(true);
  };

  return (
    <div className="max-w-3xl">
      <h2 className="mb-4 text-xl font-bold">📷 拍照记账</h2>

      <section className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
        {phase === "idle" ? (
          <ImageUploader
            onUploaded={(key, url) => {
              setImageKey(key);
              setPreviewUrl(url);
              setPhase("uploaded");
              ocrMut.mutate(key);
            }}
          />
        ) : (
          <div className="flex items-start gap-4">
            {previewUrl && (
              <img
                src={previewUrl}
                alt="预览"
                className="h-32 rounded border border-slate-200 object-contain"
              />
            )}
            <div className="flex-1 text-sm">
              {phase === "uploaded" && <p className="text-slate-500">准备识别…</p>}
              {phase === "recognizing" && <p className="text-slate-500">🔍 识别中…</p>}
              {phase === "recognized" && <p className="text-emerald-600">✓ 识别完成，可编辑后保存</p>}
              {phase === "failed" && errorMsg && (
                <p className="text-red-600">{errorMsg}</p>
              )}
              {phase === "saving" && <p className="text-slate-500">保存中…</p>}
              {phase === "saved" && (
                <p className="text-emerald-600">✓ 已保存，可继续上传下一张</p>
              )}
              <div className="mt-2 flex gap-2">
                <button
                  className="rounded border border-slate-300 px-3 py-1 text-xs"
                  onClick={reset}
                >
                  重新上传
                </button>
                {phase === "failed" && (
                  <>
                    <button
                      className="rounded bg-emerald-600 px-3 py-1 text-xs text-white"
                      onClick={() => imageKey && ocrMut.mutate(imageKey)}
                      disabled={!imageKey}
                    >
                      重试识别
                    </button>
                    <button
                      className="rounded border border-emerald-600 px-3 py-1 text-xs text-emerald-700"
                      onClick={() => {
                        setPhase("recognized");
                        setErrorMsg(null);
                      }}
                    >
                      改手工录入
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </section>

      {(phase === "recognized" || phase === "saving" || phase === "saved") && (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-3">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-slate-600">供应商</span>
              <select
                className="rounded border border-slate-300 px-2 py-1"
                value={supplierId}
                onChange={(e) => {
                  setSupplierId(e.target.value);
                  setDirty(true);
                }}
              >
                <option value="">— 不选 —</option>
                {suppliers?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-slate-600">采购时间</span>
              <input
                type="datetime-local"
                className="rounded border border-slate-300 px-2 py-1"
                value={purchaseTime}
                onChange={(e) => {
                  setPurchaseTime(e.target.value);
                  setDirty(true);
                }}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-slate-600">总额 (¥)</span>
              <input
                type="number"
                step="0.01"
                className="rounded border border-slate-300 px-2 py-1"
                value={totalAmount}
                onChange={(e) => {
                  setTotalAmount(e.target.value);
                  setDirty(true);
                }}
              />
            </label>
          </div>

          <ItemEditor items={items} onChange={edit} />

          <div className="mt-4 flex justify-end gap-2">
            <button
              className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              onClick={() => saveMut.mutate()}
              disabled={saveMut.isPending || items.filter((i) => i.name && i.unit_price).length === 0}
            >
              {saveMut.isPending ? "保存中…" : "保存"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}

function ocrErrorText(e: ApiError): string {
  if (e.status === 504 && e.detail.includes("OCR_TIMEOUT")) {
    return "OCR 超时（10s），请重试或换一张清晰的图";
  }
  if (e.detail.includes("OCR_PARSE_ERROR")) {
    return "OCR 服务异常（结果解析失败），请稍后再试";
  }
  if (e.detail.includes("OCR_UPSTREAM_ERROR")) {
    return "OCR 服务异常，请稍后再试";
  }
  return `OCR 失败：${e.detail}`;
}
