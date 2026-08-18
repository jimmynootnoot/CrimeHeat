import type { MapMode } from '../../types';

const MODES: { value: MapMode; label: string; description: string }[] = [
  { value: 'incident', label: 'Incident View', description: 'Individual historical records' },
  { value: 'cluster', label: 'Cluster View', description: 'DBSCAN clusters for a period' },
  { value: 'persistence', label: 'Persistence View', description: 'Hotspots recurring across years' },
];

export function ModeToggle({
  mode,
  onChange,
}: {
  mode: MapMode;
  onChange: (mode: MapMode) => void;
}) {
  return (
    <div className="flex gap-1 bg-white rounded-lg shadow p-1 border border-slate-200">
      {MODES.map((m) => (
        <button
          key={m.value}
          onClick={() => onChange(m.value)}
          title={m.description}
          className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
            mode === m.value
              ? 'bg-slate-900 text-white'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
