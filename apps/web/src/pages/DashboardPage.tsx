export default function DashboardPage() {
  return (
    <div className="max-w-3xl">
      <h2 className="mb-4 text-xl font-bold">价格仪表盘</h2>
      <div className="rounded-lg border-2 border-dashed border-slate-300 bg-white p-12 text-center">
        <p className="text-slate-500">
          Phase 3 将在此实现：单品历史价格曲线、跨店铺比价、推荐购买店铺。
        </p>
        <p className="mt-3 text-xs text-slate-400">
          需要先通过 OCR 或手工录入至少 3 条采购记录以形成可比对数据。
        </p>
      </div>
    </div>
  );
}
