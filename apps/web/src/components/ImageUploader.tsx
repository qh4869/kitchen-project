import { useRef, useState } from "react";
import { api, ApiError } from "../api/client";

type Status = "idle" | "uploading" | "uploaded" | "error";

export default function ImageUploader({
  onUploaded,
}: {
  onUploaded: (imageKey: string, previewUrl: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    setStatus("uploading");
    setError(null);
    const previewUrl = URL.createObjectURL(file);
    setPreview(previewUrl);
    try {
      const r = await api.upload<{ image_key: string; size: number; content_type: string }>(
        "/api/v1/uploads",
        file
      );
      setStatus("uploaded");
      onUploaded(r.image_key, previewUrl);
    } catch (e) {
      setStatus("error");
      setError((e as ApiError).detail || "上传失败");
    }
  };

  return (
    <div>
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
        onClick={() => inputRef.current?.click()}
        className="flex h-40 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 text-slate-500 hover:border-emerald-400 hover:bg-emerald-50"
      >
        {preview ? (
          <img src={preview} alt="预览" className="max-h-32 max-w-full object-contain" />
        ) : (
          <>
            <p className="text-sm">📷 点击 / 拖拽 / 拍照上传小票</p>
            <p className="mt-1 text-xs text-slate-400">JPEG / PNG / WebP / HEIC · ≤ 10 MB</p>
          </>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
      />
      <div className="mt-2 text-sm">
        {status === "uploading" && <p className="text-slate-500">上传中…</p>}
        {status === "uploaded" && <p className="text-emerald-600">✓ 上传完成</p>}
        {status === "error" && <p className="text-red-600">{error}</p>}
      </div>
    </div>
  );
}
