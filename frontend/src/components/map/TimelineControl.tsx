import { useEffect, useRef, useState } from 'react';

const PLAY_INTERVAL_MS = 1400;

export function TimelineControl({
  years,
  value,
  onChange,
}: {
  years: number[];
  value: number | 'all';
  onChange: (value: number | 'all') => void;
}) {
  const [playing, setPlaying] = useState(false);
  // Interval callbacks close over stale props otherwise — keep the latest
  // value/onChange in a ref so each tick advances from the real current year.
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  valueRef.current = value;
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!playing || years.length === 0) return;
    const timer = setInterval(() => {
      const current = valueRef.current;
      const idx = current === 'all' ? -1 : years.indexOf(current as number);
      const nextIdx = (idx + 1) % years.length;
      onChangeRef.current(years[nextIdx]);
    }, PLAY_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [playing, years]);

  if (years.length === 0) return null;

  const currentIdx = value === 'all' ? -1 : years.indexOf(value);

  function step(delta: number) {
    setPlaying(false);
    const base = currentIdx === -1 ? (delta > 0 ? -1 : years.length) : currentIdx;
    const nextIdx = Math.min(Math.max(base + delta, 0), years.length - 1);
    onChange(years[nextIdx]);
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-xs font-semibold text-slate-700">Timeline</h4>
        <button
          onClick={() => onChange('all')}
          className={`rounded px-2 py-0.5 text-xs font-medium ${
            value === 'all' ? 'bg-slate-900 text-white' : 'text-slate-500 hover:bg-slate-100'
          }`}
        >
          All years
        </button>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => step(-1)}
          disabled={currentIdx === 0}
          aria-label="Previous year"
          className="rounded border border-slate-300 px-1.5 py-0.5 text-xs disabled:opacity-30"
        >
          ◀
        </button>
        <button
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? 'Pause' : 'Play'}
          className="rounded border border-slate-300 px-1.5 py-0.5 text-xs"
        >
          {playing ? '❚❚' : '▶'}
        </button>
        <button
          onClick={() => step(1)}
          disabled={currentIdx === years.length - 1}
          aria-label="Next year"
          className="rounded border border-slate-300 px-1.5 py-0.5 text-xs disabled:opacity-30"
        >
          ▶
        </button>

        <input
          type="range"
          min={0}
          max={years.length - 1}
          step={1}
          value={currentIdx === -1 ? years.length - 1 : currentIdx}
          onChange={(e) => {
            setPlaying(false);
            onChange(years[Number(e.target.value)]);
          }}
          className="mx-1 flex-1 accent-slate-900"
        />
        <span className="w-10 shrink-0 text-right text-xs font-semibold text-slate-800">
          {value === 'all' ? 'All' : value}
        </span>
      </div>
    </div>
  );
}
