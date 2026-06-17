export default function UploadPage() {
  return (
    <div className="max-w-3xl">
      <h2 className="mb-4 text-xl font-bold">拍照记账</h2>
      <div className="rounded-lg border-2 border-dashed border-slate-300 bg-white p-12 text-center">
        <p className="text-slate-500">
          Phase 2 将在此实现：上传小票 → GLM-4V OCR 提取 → 人工微调 → 保存为采购记录。
        </p>
        <p className="mt-3 text-xs text-slate-400">
          当前阶段请先到「供应商」标签页维护店铺，再到「采购记录」查看手工录入。
        </p>
      </div>
    </div>
  );
}
