import type { ReactNode } from 'react';

/** Lightweight CSS-only tooltip — no extra dependency. */
export function Tooltip({ text, children }: { text: string; children: ReactNode }) {
  return (
    <span className="group relative inline-flex items-center">
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-[1500] mb-1.5 w-max max-w-[16rem] -translate-x-1/2 rounded bg-slate-900 px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
      >
        {text}
      </span>
    </span>
  );
}

export function InfoIcon({ text }: { text: string }) {
  return (
    <Tooltip text={text}>
      <span
        tabIndex={0}
        className="ml-1 inline-flex h-3.5 w-3.5 cursor-help items-center justify-center rounded-full border border-slate-400 text-[10px] font-bold leading-none text-slate-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
      >
        i
      </span>
    </Tooltip>
  );
}
