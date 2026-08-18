import { PERSISTENCE_CATEGORY_LABELS, type MapFilterState, type MapMode, type PersistenceCategory } from '../../types';
import { PERSISTENCE_STYLES } from './persistenceStyles';

const CATEGORY_ORDER: PersistenceCategory[] = [
  'active_persistent',
  'historical_persistent',
  'intermittent',
  'temporary',
];

function activeFilterChips(filters: MapFilterState): string[] {
  const chips: string[] = [];
  if (filters.municipality) chips.push(filters.municipality);
  if (filters.barangay) chips.push(filters.barangay);
  if (filters.crime_type) chips.push(filters.crime_type);
  if (filters.year !== 'all') chips.push(String(filters.year));
  if (filters.cluster_status !== 'all') chips.push(`status: ${filters.cluster_status}`);
  if (filters.persistence_category !== 'all') chips.push(filters.persistence_category);
  return chips;
}

export function MapLegend({ mode, filters }: { mode: MapMode; filters: MapFilterState }) {
  const chips = activeFilterChips(filters);

  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-3 text-xs">
      {mode === 'persistence' && (
        <div className="space-y-1">
          <h4 className="mb-1 font-semibold text-slate-700">Persistence category</h4>
          {CATEGORY_ORDER.map((cat) => {
            const style = PERSISTENCE_STYLES[cat];
            return (
              <div key={cat} className="flex items-center gap-2">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{
                    backgroundColor: style.fillColor,
                    border: `${style.weight}px solid ${style.color}`,
                  }}
                />
                <span className="text-slate-600">{PERSISTENCE_CATEGORY_LABELS[cat]}</span>
              </div>
            );
          })}
        </div>
      )}

      {mode === 'cluster' && (
        <div className="space-y-1">
          <h4 className="mb-1 font-semibold text-slate-700">Cluster view</h4>
          <div className="flex items-center gap-2">
            <span className="inline-block h-3 w-3 rounded-full border-2 border-red-700 bg-red-400" />
            <span className="text-slate-600">DBSCAN cluster extent (convex hull)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-slate-400" />
            <span className="text-slate-600">Noise (not part of any cluster)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-orange-300 opacity-70" />
            <span className="text-slate-600">Heatmap = visual density, not DBSCAN</span>
          </div>
        </div>
      )}

      {mode === 'incident' && (
        <div className="space-y-1">
          <h4 className="mb-1 font-semibold text-slate-700">Incident view</h4>
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full border border-slate-500 bg-slate-400 opacity-60" />
            <span className="text-slate-600">Individual incident (colored by crime type)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-orange-300 opacity-70" />
            <span className="text-slate-600">Heatmap = visual density, not DBSCAN</span>
          </div>
        </div>
      )}

      {chips.length > 0 && (
        <div className="border-t border-slate-100 pt-2">
          <h4 className="mb-1 font-semibold text-slate-700">Active filters</h4>
          <div className="flex flex-wrap gap-1">
            {chips.map((chip) => (
              <span key={chip} className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
                {chip}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
