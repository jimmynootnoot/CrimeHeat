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
    <aside aria-label={title} className="absolute bottom-3 left-3 right-3 z-[1000] max-h-[45%] overflow-y-auto rounded-2xl border border-slate-200/80 bg-white/95 shadow-2xl backdrop-blur-md sm:bottom-auto sm:left-auto sm:top-3 sm:max-h-[calc(100%-1.5rem)] sm:w-80">
      <div className="sticky top-0 flex items-start justify-between border-b border-slate-200 bg-white/95 px-4 py-3">
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
