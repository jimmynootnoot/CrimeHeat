import type { ReactNode } from 'react';

/** Generic right-side drawer shell, reused for municipality stats, cluster
 * details, and persistence details — one slide-over instead of three. */
export function DetailDrawer({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <aside className="absolute top-0 right-0 z-[1000] h-full w-80 overflow-y-auto border-l border-slate-200 bg-white shadow-2xl">
      <div className="sticky top-0 flex items-start justify-between border-b border-slate-200 bg-white px-4 py-3">
        <div>
          <h2 className="font-bold text-slate-900">{title}</h2>
          {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        </div>
        <button
          onClick={onClose}
          className="text-lg leading-none text-slate-400 hover:text-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 rounded"
          aria-label="Close"
        >
          ×
        </button>
      </div>
      <div className="space-y-4 p-4 text-sm">{children}</div>
    </aside>
  );
}
