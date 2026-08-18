import { useState } from 'react';
import {
  CRIME_TYPES,
  PERSISTENCE_CATEGORY_LABELS,
  PPALMA_MUNICIPALITIES,
  type AnalysisMetadata,
  type MapFilterState,
  type MapMode,
  type PersistenceCategory,
} from '../../types';
import { InfoIcon } from '../ui/Tooltip';

const PERSISTENCE_CATEGORIES: (PersistenceCategory | 'all')[] = [
  'all',
  'active_persistent',
  'historical_persistent',
  'intermittent',
  'temporary',
];

function activeFilterCount(filters: MapFilterState): number {
  let n = 0;
  if (filters.municipality) n++;
  if (filters.barangay) n++;
  if (filters.crime_type) n++;
  if (filters.persistence_category !== 'all') n++;
  return n;
}

export function FilterPanel({
  mode,
  filters,
  onChange,
  barangays,
  metadata,
}: {
  mode: MapMode;
  filters: MapFilterState;
  onChange: (filters: MapFilterState) => void;
  barangays: string[];
  metadata: AnalysisMetadata;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const count = activeFilterCount(filters);

  function set<K extends keyof MapFilterState>(key: K, value: MapFilterState[K]) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <div className="w-64 rounded-lg border border-slate-200 bg-white shadow">
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex w-full items-center justify-between px-3 py-2 text-sm font-semibold text-slate-800"
      >
        <span>
          Filters
          {count > 0 && (
            <span className="ml-1.5 rounded-full bg-slate-900 px-1.5 py-0.5 text-[10px] font-bold text-white">
              {count}
            </span>
          )}
        </span>
        <span className="text-xs text-slate-400">{collapsed ? 'Show' : 'Hide'}</span>
      </button>

      {!collapsed && (
        <div className="space-y-3 border-t border-slate-100 p-3 text-sm">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Municipality</label>
            <select
              value={filters.municipality}
              onChange={(e) => set('municipality', e.target.value)}
              className="w-full rounded border border-slate-300 px-2 py-1.5"
            >
              <option value="">All municipalities</option>
              {PPALMA_MUNICIPALITIES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Barangay</label>
            <select
              value={filters.barangay}
              onChange={(e) => set('barangay', e.target.value)}
              disabled={barangays.length === 0}
              className="w-full rounded border border-slate-300 px-2 py-1.5 disabled:bg-slate-100"
            >
              <option value="">All barangays</option>
              {barangays.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Crime type</label>
            <select
              value={filters.crime_type}
              onChange={(e) => set('crime_type', e.target.value)}
              className="w-full rounded border border-slate-300 px-2 py-1.5"
            >
              <option value="">All crime types</option>
              {CRIME_TYPES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {mode === 'persistence' && (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">
                Persistence category
              </label>
              <select
                value={filters.persistence_category}
                onChange={(e) => set('persistence_category', e.target.value)}
                className="w-full rounded border border-slate-300 px-2 py-1.5"
              >
                {PERSISTENCE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c === 'all' ? 'All categories' : PERSISTENCE_CATEGORY_LABELS[c]}
                  </option>
                ))}
              </select>
            </div>
          )}

          {mode === 'cluster' && (
            <div className="rounded bg-slate-50 p-2 text-xs text-slate-600">
              <div className="flex items-center justify-between">
                <span>
                  Epsilon (eps)
                  <InfoIcon text="DBSCAN neighborhood radius: points within this distance of each other can join the same cluster." />
                </span>
                <span className="font-mono font-semibold">
                  {metadata.eps_km !== undefined ? `${metadata.eps_km} km` : '—'}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between">
                <span>
                  Min samples
                  <InfoIcon text="Minimum number of points required within eps to form a cluster. Points that don't meet this are labeled noise." />
                </span>
                <span className="font-mono font-semibold">{metadata.min_samples ?? '—'}</span>
              </div>
            </div>
          )}

          {mode === 'persistence' && (
            <div className="rounded bg-slate-50 p-2 text-xs text-slate-600">
              <div className="flex items-center justify-between">
                <span>
                  Persistence threshold
                  <InfoIcon text="persistence_score = periods present / total periods analyzed. At/above this threshold a location is 'persistent' (active or historical); below it, 'intermittent' or 'temporary'." />
                </span>
                <span className="font-mono font-semibold">
                  {metadata.persistence_score_threshold !== undefined
                    ? `${Math.round(metadata.persistence_score_threshold * 100)}%`
                    : '—'}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
