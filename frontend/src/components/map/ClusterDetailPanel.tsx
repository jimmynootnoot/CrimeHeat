import type { ClusterFeatureProperties } from '../../types';
import { DetailDrawer } from './DetailDrawer';

export function ClusterDetailPanel({
  cluster,
  onClose,
}: {
  cluster: ClusterFeatureProperties;
  onClose: () => void;
}) {
  return (
    <DetailDrawer
      title={`Cluster #${cluster.cluster_id}`}
      subtitle={`${cluster.municipality ?? ''} — ${cluster.year ?? 'all years'}`}
      onClose={onClose}
    >
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded bg-slate-50 p-3">
          <div className="text-2xl font-bold text-slate-900">{cluster.point_count}</div>
          <div className="text-xs text-slate-500">Incidents in this cluster</div>
        </div>
        <div className="rounded bg-slate-50 p-3">
          <div className="text-lg font-bold text-slate-900">{cluster.dominant_crime_type ?? '—'}</div>
          <div className="text-xs text-slate-500">Dominant crime type</div>
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-3 rounded border border-slate-200 p-3">
        <div><dt className="text-xs text-slate-500">Core points · solid</dt><dd className="text-lg font-semibold">{cluster.core_point_count ?? '—'}</dd></div>
        <div><dt className="text-xs text-slate-500">Border points · hollow</dt><dd className="text-lg font-semibold">{cluster.border_point_count ?? '—'}</dd></div>
      </dl>

      <div>
        <h3 className="mb-2 font-semibold text-slate-800">Barangays involved</h3>
        <ul className="flex flex-wrap gap-1.5">
          {(cluster.barangays ?? []).map((b) => (
            <li key={b} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
              {b}
            </li>
          ))}
        </ul>
      </div>

      <p className="text-xs text-slate-400">
        This is a spatial concentration of historical, already-reported incidents for the
        selected year/crime-type filter — it is not a prediction of future crime.
      </p>
    </DetailDrawer>
  );
}
