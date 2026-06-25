export type Item = {
  name: string;
  quantity: string;
  unit: string;
  unit_price: string;
  category: string;
  brand: string;
};

export default function ItemEditor({
  items,
  onChange,
}: {
  items: Item[];
  onChange: (next: Item[]) => void;
}) {
  const update = (i: number, patch: Partial<Item>) => {
    onChange(items.map((it, idx) => (idx === i ? { ...it, ...patch } : it)));
  };
  const remove = (i: number) => onChange(items.filter((_, idx) => idx !== i));
  const add = () =>
    onChange([
      ...items,
      { name: "", quantity: "1", unit: "", unit_price: "", category: "", brand: "" },
    ]);

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-slate-600">
          <tr>
            <th className="px-2 py-1.5 text-left font-medium">名称</th>
            <th className="px-2 py-1.5 text-right font-medium">数量</th>
            <th className="px-2 py-1.5 text-left font-medium">单位</th>
            <th className="px-2 py-1.5 text-right font-medium">单价</th>
            <th className="px-2 py-1.5 text-left font-medium">类目</th>
            <th className="px-2 py-1.5 text-left font-medium">品牌</th>
            <th className="px-2 py-1.5"></th>
          </tr>
        </thead>
        <tbody>
          {items.map((it, i) => (
            <tr key={i} className="border-t border-slate-100">
              <td className="px-2 py-1">
                <input
                  className="w-full rounded border border-slate-200 px-1.5 py-0.5"
                  value={it.name}
                  onChange={(e) => update(i, { name: e.target.value })}
                />
              </td>
              <td className="px-2 py-1">
                <input
                  className="w-16 rounded border border-slate-200 px-1.5 py-0.5 text-right"
                  value={it.quantity}
                  onChange={(e) => update(i, { quantity: e.target.value })}
                />
              </td>
              <td className="px-2 py-1">
                <input
                  className="w-14 rounded border border-slate-200 px-1.5 py-0.5"
                  value={it.unit}
                  onChange={(e) => update(i, { unit: e.target.value })}
                />
              </td>
              <td className="px-2 py-1">
                <input
                  className="w-20 rounded border border-slate-200 px-1.5 py-0.5 text-right"
                  value={it.unit_price}
                  onChange={(e) => update(i, { unit_price: e.target.value })}
                />
              </td>
              <td className="px-2 py-1">
                <input
                  className="w-20 rounded border border-slate-200 px-1.5 py-0.5"
                  value={it.category}
                  onChange={(e) => update(i, { category: e.target.value })}
                />
              </td>
              <td className="px-2 py-1">
                <input
                  className="w-20 rounded border border-slate-200 px-1.5 py-0.5"
                  value={it.brand}
                  onChange={(e) => update(i, { brand: e.target.value })}
                />
              </td>
              <td className="px-2 py-1 text-right">
                <button
                  className="text-xs text-red-500 hover:underline"
                  onClick={() => remove(i)}
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={7} className="px-2 py-3 text-center text-slate-400">
                暂无明细，点下方 + 添加
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <div className="border-t border-slate-100 bg-slate-50 p-2">
        <button
          className="text-xs text-emerald-700 hover:underline"
          onClick={add}
        >
          + 添加一行
        </button>
      </div>
    </div>
  );
}
