import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import ImageUploader from "../components/ImageUploader";
import ItemEditor, { type Item } from "../components/ItemEditor";

type Mode = "photo" | "manual";

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
  items: OcrItem[];
  raw_llm_output: Record<string, unknown>;
  provider: string;
};

type PurchaseOutItem = {
  id: string;
  name: string;
  quantity: string;
  unit: string | null;
  unit_price: string;
  category: string | null;
  brand: string | null;
};

type PurchaseOut = {
  id: string;
  supplier_id: string | null;
  purchase_time: string;
  notes: string | null;
  manual_adjustment: boolean;
  items: PurchaseOutItem[];
};

type PhotoPhase = "idle" | "uploaded" | "recognizing" | "recognized" | "failed" | "saving" | "saved";
type ManualPhase = "idle" | "saving" | "saved" | "error";

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

function nowLocalDateTime(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toLocalInputValue(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const EMPTY_ITEM: Item = {
  name: "",
  quantity: "1",
  unit: "",
  unit_price: "",
  category: "",
  brand: "",
};

export default function EntryPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editPurchaseId = searchParams.get("edit");
  const isEditMode = !!editPurchaseId;

  const didPrefillRef = useRef(false);

  const { data: editPurchase } = useQuery<PurchaseOut>({
    queryKey: ["purchase", editPurchaseId],
    queryFn: () => api.get<PurchaseOut>(`/api/v1/purchases/${editPurchaseId}`),
    enabled: isEditMode,
  });

  useEffect(() => {
    if (editPurchase && !didPrefillRef.current) {
      didPrefillRef.current = true;
      setManualSupplierId(editPurchase.supplier_id ?? "");
      setManualPurchaseTime(toLocalInputValue(editPurchase.purchase_time));
      setManualItems(
        editPurchase.items.map((it) => ({
          name: it.name,
          quantity: it.quantity,
          unit: it.unit ?? "",
          unit_price: it.unit_price,
          category: it.category ?? "",
          brand: it.brand ?? "",
        }))
      );
    }
  }, [editPurchase]);

  const isLoadingPurchase = isEditMode && !editPurchase;

  // --- Mode (segmented control) ---
  const [mode, setMode] = useState<Mode>("photo");

  // --- Photo mode state (unchanged from original UploadPage) ---
  const [photoPhase, setPhotoPhase] = useState<PhotoPhase>("idle");
  const [imageKey, setImageKey] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [photoErrorMsg, setPhotoErrorMsg] = useState<string | null>(null);

  const [photoSupplierId, setPhotoSupplierId] = useState<string>("");
  const [photoPurchaseTime, setPhotoPurchaseTime] = useState<string>("");
  const [photoItems, setPhotoItems] = useState<Item[]>([]);
  const [photoRawLlm, setPhotoRawLlm] = useState<Record<string, unknown>>({});
  const [photoDirty, setPhotoDirty] = useState(false);

  // --- Manual mode state (new) ---
  const [manualSupplierId, setManualSupplierId] = useState<string>("");
  const [manualPurchaseTime, setManualPurchaseTime] = useState<string>(nowLocalDateTime());
  const [manualItems, setManualItems] = useState<Item[]>([{ ...EMPTY_ITEM }]);

  const { data: suppliers } = useQuery<Supplier[]>({
    queryKey: ["suppliers"],
    queryFn: () => api.get<Supplier[]>("/api/v1/suppliers"),
  });

  // --- Photo mode mutations (unchanged) ---
  const ocrMut = useMutation({
    mutationFn: async (key: string) =>
      api.post<OcrResult>("/api/v1/ocr/extract", { image_key: key }),
    onMutate: () => {
      setPhotoPhase("recognizing");
      setPhotoErrorMsg(null);
    },
    onSuccess: (r) => {
      setImageKey(r.image_key);
      setPhotoRawLlm(r.raw_llm_output);
      setPhotoItems(r.items.map(itemFromOcr));
      setPhotoPhase("recognized");
      if (r.items.length === 0) {
        setPhotoErrorMsg("未识别到任何商品信息，请重拍或改手工录入");
        setPhotoPhase("failed");
      }
    },
    onError: (e: ApiError) => {
      setPhotoErrorMsg(ocrErrorText(e));
      setPhotoPhase("failed");
    },
  });

  const photoSaveMut = useMutation({
    mutationFn: async () => {
      const body = {
        image_key: imageKey,
        supplier_id: photoSupplierId || null,
        purchase_time: photoPurchaseTime ? new Date(photoPurchaseTime).toISOString() : null,
        ocr_raw: photoRawLlm,
        manual_adjustment: photoDirty,
        items: photoItems
          .filter((i) => i.name.trim() && i.unit_price)
          .map((i) => ({
            name: i.name.trim(),
            quantity: (i.quantity || "1").trim() || "1",
            unit: i.unit?.trim() || null,
            unit_price: i.unit_price,
            category: i.category?.trim() || null,
            brand: i.brand?.trim() || null,
          })),
      };
      return api.post("/api/v1/purchases/from-ocr", body);
    },
    onMutate: () => {
      setPhotoPhase("saving");
      setPhotoErrorMsg(null);
    },
    onSuccess: () => {
      setPhotoPhase("saved");
      qc.invalidateQueries({ queryKey: ["purchases"] });
    },
    onError: (e: ApiError) => {
      setPhotoErrorMsg(`保存失败：${e.detail}`);
      setPhotoPhase("recognized");
    },
  });

  // --- Manual mode mutation (new) ---
  const manualSaveMut = useMutation({
    mutationFn: async () => {
      const body = {
        supplier_id: manualSupplierId || null,
        purchase_time: manualPurchaseTime
          ? new Date(manualPurchaseTime).toISOString()
          : null,
        manual_adjustment: isEditMode ? true : undefined,
        items: manualItems
          .filter((i) => i.name.trim() && i.unit_price)
          .map((i) => ({
            name: i.name.trim(),
            quantity: (i.quantity || "1").trim() || "1",
            unit: i.unit?.trim() || null,
            unit_price: i.unit_price,
            category: i.category?.trim() || null,
            brand: i.brand?.trim() || null,
          })),
      };
      if (isEditMode && editPurchaseId) {
        return api.put(`/api/v1/purchases/${editPurchaseId}`, body);
      }
      return api.post("/api/v1/purchases", body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["purchases"] });
      qc.invalidateQueries({ queryKey: ["prices"] });
      if (isEditMode && editPurchaseId) {
        qc.invalidateQueries({ queryKey: ["purchase", editPurchaseId] });
        navigate("/");
      }
    },
  });

  // --- Mode switching ---
  const resetPhotoState = () => {
    setPhotoPhase("idle");
    setImageKey(null);
    setPreviewUrl(null);
    setPhotoErrorMsg(null);
    setPhotoSupplierId("");
    setPhotoPurchaseTime("");
    setPhotoItems([]);
    setPhotoRawLlm({});
    setPhotoDirty(false);
  };

  const resetManualState = () => {
    manualSaveMut.reset();
    setManualSupplierId("");
    setManualPurchaseTime(nowLocalDateTime());
    setManualItems([{ ...EMPTY_ITEM }]);
  };

  const switchMode = (next: Mode) => {
    if (next === mode) return;
    resetPhotoState();
    resetManualState();
    setMode(next);
  };

  // Manual mode phase is derived from mutation state
  const manualPhase: ManualPhase = manualSaveMut.isPending
    ? "saving"
    : manualSaveMut.isSuccess
      ? "saved"
      : manualSaveMut.isError
        ? "error"
        : "idle";

  const manualErrorMsg = manualSaveMut.isError
    ? manualSaveMut.error instanceof ApiError
      ? `保存失败：${manualSaveMut.error.detail}`
      : `保存失败：${(manualSaveMut.error as Error).message || "网络异常，请稍后重试"}`
    : null;

  const manualCanSave =
    !manualSaveMut.isPending &&
    manualItems.filter((i) => i.name.trim() && i.unit_price).length > 0;

  if (isLoadingPurchase) {
    return (
      <div className="max-w-3xl">
        <p className="text-sm text-slate-500">加载采购单...</p>
      </div>
    );
  }

  // In edit mode we always render the manual form regardless of the segmented control.
  const effectiveMode: Mode = isEditMode ? "manual" : mode;

  return (
    <div className="max-w-3xl">
      <h2 className="mb-4 text-xl font-bold">{isEditMode ? "编辑记录" : "记账"}</h2>

      {/* Segmented control */}
      {!isEditMode && (
        <div className="mb-4 inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
          <button
            type="button"
            onClick={() => switchMode("photo")}
            className={`rounded-md px-4 py-1.5 text-sm transition-colors ${
              mode === "photo"
                ? "bg-white text-emerald-700 font-medium shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            📷 拍照
          </button>
          <button
            type="button"
            onClick={() => switchMode("manual")}
            className={`rounded-md px-4 py-1.5 text-sm transition-colors ${
              mode === "manual"
                ? "bg-white text-emerald-700 font-medium shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            ✍️ 手工
          </button>
        </div>
      )}

      {effectiveMode === "photo" ? (
        <>
          {/* ============ PHOTO MODE (unchanged from original UploadPage) ============ */}
          <section className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
            {photoPhase === "idle" ? (
              <ImageUploader
                onUploaded={(key, url) => {
                  setImageKey(key);
                  setPreviewUrl(url);
                  setPhotoPhase("uploaded");
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
                  {photoPhase === "uploaded" && <p className="text-slate-500">准备识别…</p>}
                  {photoPhase === "recognizing" && <p className="text-slate-500">🔍 识别中…</p>}
                  {photoPhase === "recognized" && (
                    <p className="text-emerald-600">✓ 识别完成，可编辑后保存</p>
                  )}
                  {photoPhase === "failed" && photoErrorMsg && (
                    <p className="text-red-600">{photoErrorMsg}</p>
                  )}
                  {photoPhase === "saving" && <p className="text-slate-500">保存中…</p>}
                  {photoPhase === "saved" && (
                    <p className="text-emerald-600">✓ 已保存，可继续上传下一张</p>
                  )}
                  <div className="mt-2 flex gap-2">
                    <button
                      className="rounded border border-slate-300 px-3 py-1 text-xs"
                      onClick={resetPhotoState}
                    >
                      重新上传
                    </button>
                    {photoPhase === "failed" && (
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
                            setPhotoPhase("recognized");
                            setPhotoErrorMsg(null);
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

          {(photoPhase === "recognized" ||
            photoPhase === "saving" ||
            photoPhase === "saved") && (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-slate-600">供应商</span>
                  <select
                    className="rounded border border-slate-300 px-2 py-1"
                    value={photoSupplierId}
                    onChange={(e) => {
                      setPhotoSupplierId(e.target.value);
                      setPhotoDirty(true);
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
                    value={photoPurchaseTime}
                    onChange={(e) => {
                      setPhotoPurchaseTime(e.target.value);
                      setPhotoDirty(true);
                    }}
                  />
                </label>
              </div>

              <ItemEditor
                items={photoItems}
                onChange={(next) => {
                  setPhotoItems(next);
                  setPhotoDirty(true);
                }}
              />

              <div className="mt-4 flex justify-end gap-2">
                <button
                  className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                  onClick={() => {
                    if (!photoSaveMut.isPending) photoSaveMut.mutate();
                  }}
                  disabled={
                    photoSaveMut.isPending ||
                    photoItems.filter((i) => i.name && i.unit_price).length === 0
                  }
                >
                  {photoSaveMut.isPending ? "保存中…" : "保存"}
                </button>
              </div>
            </section>
          )}
        </>
      ) : (
        <>
          {/* ============ MANUAL MODE (new) ============ */}
          {manualPhase === "saved" ? (
            <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-6 text-center">
              <p className="text-emerald-700">✓ 已保存</p>
              <button
                type="button"
                onClick={() => {
                  manualSaveMut.reset();
                  resetManualState();
                }}
                className="mt-3 rounded border border-emerald-600 px-4 py-1.5 text-sm font-medium text-emerald-700 hover:bg-emerald-100"
              >
                新建一条
              </button>
            </section>
          ) : (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-slate-600">供应商</span>
                  <select
                    className="rounded border border-slate-300 px-2 py-1"
                    value={manualSupplierId}
                    onChange={(e) => {
                      setManualSupplierId(e.target.value);
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
                    value={manualPurchaseTime}
                    onChange={(e) => {
                      setManualPurchaseTime(e.target.value);
                    }}
                  />
                </label>
              </div>

              <ItemEditor
                items={manualItems}
                onChange={(next) => {
                  setManualItems(next);
                }}
              />

              {manualErrorMsg && (
                <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                  {manualErrorMsg}
                </div>
              )}

              <div className="mt-4 flex justify-end gap-2">
                {isEditMode && (
                  <button
                    type="button"
                    className="rounded border border-slate-300 px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
                    onClick={() => navigate("/")}
                  >
                    取消
                  </button>
                )}
                <button
                  type="button"
                  className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:bg-slate-400"
                  onClick={() => {
                    if (!manualSaveMut.isPending) manualSaveMut.mutate();
                  }}
                  disabled={!manualCanSave}
                >
                  {manualPhase === "saving"
                    ? "保存中…"
                    : isEditMode
                      ? "保存修改"
                      : "保存"}
                </button>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function ocrErrorText(e: ApiError): string {
  if (e.status === 504 && e.detail.includes("OCR_TIMEOUT")) {
    return "OCR 超时（30s），请重试或换一张清晰的图";
  }
  if (e.detail.includes("OCR_PARSE_ERROR")) {
    return "OCR 服务异常（结果解析失败），请稍后再试";
  }
  if (e.detail.includes("OCR_UPSTREAM_ERROR")) {
    return "OCR 服务异常，请稍后再试";
  }
  return `OCR 失败：${e.detail}`;
}
