import { PERSISTENCE_CATEGORY_LABELS, type MapFilterState, type MapLayerVisibility, type MapMode, type PersistenceCategory } from '../../types';
import { PERSISTENCE_STYLES } from './persistenceStyles';

const CATEGORY_ORDER: PersistenceCategory[] = [
  'active_persistent',
  'historical_persistent',
  'intermittent',
  'temporary',
];

function activeFilterChips(filters: MapFilterState, mode: MapMode): string[] {
  const chips: string[] = [];
  if (filters.municipality) chips.push(filters.municipality);
  if (filters.barangay) chips.push(filters.barangay);
  if (filters.crime_type) chips.push(filters.crime_type);
  if (mode !== 'persistence' && filters.year !== 'all') chips.push(String(filters.year));
  if (mode === 'persistence' && filters.persistence_category !== 'all') chips.push(PERSISTENCE_CATEGORY_LABELS[filters.persistence_category as PersistenceCategory]);
  return chips;
}

export function MapLegend({ mode, filters, visibility }: { mode: MapMode; filters: MapFilterState; visibility: MapLayerVisibility }) {
  const chips = activeFilterChips(filters, mode);

  return (
    <div className="w-64 space-y-2 rounded-lg border border-slate-200 bg-white p-3 text-xs">
      {mode === 'persistence' && visibility.persistence && (
        <div className="space-y-1">
          <h4 className="mb-1 font-semibold text-slate-700">Persistence category</h4>
          <p className="pb-1 text-slate-500">
            Shaded area = where the hotspot's incidents fall. Badge = persistence score, sized by
            incident count. Click to explore.
          </p>
          {CATEGORY_ORDER.map((cat) => {
            const style = PERSISTENCE_STYLES[cat];
            return (
              <div key={cat} className="flex items-center gap-2">
                <span
                  className="inline-block h-3 w-4 rounded-sm"
                  style={{
                    backgroundColor: style.fillColor,
                    border: `${style.weight}px ${
                      cat === 'historical_persistent' ? 'dashed' : 'solid'
                    } ${style.color}`,
                    opacity: 0.4 + style.fillOpacity * 0.6,
                  }}
                />
                <span className="text-slate-600">{PERSISTENCE_CATEGORY_LABELS[cat]}</span>
              </div>
            );
          })}
          <div className="flex items-center gap-2 pt-1">
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-slate-400" />
              <span className="inline-block h-3.5 w-3.5 rounded-full bg-slate-500" />
            </span>
            <span className="text-slate-500">Marker size = incidents in the hotspot</span>
          </div>
          <p className="pt-1 text-[11px] leading-snug text-slate-400">
            Dashed outline marks a historical hotspot — it recurred, then stopped before the
            latest period.
          </p>
        </div>
      )}

      {mode === 'cluster' && (
        <div className="space-y-1">
          <h4 className="mb-1 font-semibold text-slate-700">Cluster view</h4>
          {visibility.clusters && <div className="flex items-center gap-2">
            <span className="inline-block h-3 w-3 rounded-full border-2 border-red-700 bg-red-400" />
            <span className="text-slate-600">Badge = incident count; shading = cluster envelope</span>
          </div>}
          {visibility.core && <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 shrink-0 rounded-full bg-red-600" />
            <span className="text-slate-600">Core point (solid, visible at zoom 13+)</span>
          </div>}
          {visibility.border && <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 shrink-0 rounded-full border-2 border-red-700" />
            <span className="text-slate-600">Border point (in a cluster, not dense itself)</span>
          </div>}
          {visibility.noise && <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-slate-400" />
            <span className="text-slate-600">Noise (not part of any cluster)</span>
          </div>}
          <p className="pt-1 text-slate-500">
            Envelopes enclose member points and may include empty space. Click a cluster to highlight its members.
          </p>
        </div>
      )}

      {mode === 'incident' && (
        <div className="space-y-1">
          <h4 className="mb-1 font-semibold text-slate-700">Incident view</h4>
          {visibility.incidents && <p className="pb-1 text-slate-500">Numbered badges group nearby incidents. Zoom to separate.</p>}
          {visibility.incidents && <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full border border-slate-500 bg-slate-400 opacity-60" />
            <span className="text-slate-600">Individual incident (colored by crime type)</span>
          </div>}
          {visibility.heatmap && <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-orange-300 opacity-70" />
            <span className="text-slate-600">Heatmap = visual density, not DBSCAN</span>
          </div>}
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
