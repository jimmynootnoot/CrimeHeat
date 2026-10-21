import type { AnalysisMetadata } from '../../types';

export function AnalysisSummary({ metadata, loading, error, onRetry }: {
  metadata: AnalysisMetadata;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  const ready = !loading && !error && metadata.incidents_analyzed !== undefined;
  const metrics = [
    ['Incidents', ready ? metadata.incidents_analyzed?.toLocaleString() : '—'],
    ['Clusters', ready ? metadata.cluster_count?.toLocaleString() : '—'],
    ['Noise', ready && metadata.noise_ratio != null ? `${Math.round(metadata.noise_ratio * 100)}%` : '—'],
  ];
  return (
    <section aria-label="Cluster analysis summary" aria-busy={loading} className="w-64 rounded-lg border border-slate-200 bg-white p-3 shadow">
      <h4 className="mb-2 text-xs font-semibold text-slate-700">Analysis summary</h4>
      <div className="grid grid-cols-3 gap-2">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <div className="text-lg font-bold tabular-nums text-slate-900">{value}</div>
            <div className="text-[11px] text-slate-500">{label}</div>
          </div>
        ))}
      </div>
      <div aria-live="polite">
        {loading && <p className="mt-2 text-xs text-slate-500">Updating analysis…</p>}
        {error && <div role="alert" className="mt-2 text-xs text-red-700">{error} <button className="font-semibold underline" onClick={onRetry}>Retry</button></div>}
        {ready && <p className="mt-2 text-[11px] text-slate-500">All incidents in the selected filters; layer toggles only change visibility.</p>}
        {ready && metadata.incidents_analyzed === 0 && <p className="mt-2 text-xs text-slate-600">No incidents match these filters.</p>}
        {ready && (metadata.incidents_analyzed ?? 0) > 0 && (metadata.warnings ?? []).map((warning) => (
          <p key={warning} className="mt-2 rounded bg-amber-50 p-2 text-xs text-amber-900">{warning}</p>
        ))}
      </div>
    </section>
  );
}
