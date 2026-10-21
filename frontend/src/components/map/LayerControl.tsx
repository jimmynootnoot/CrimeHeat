import type { MapLayerVisibility, MapMode } from '../../types';
import { InfoIcon } from '../ui/Tooltip';

interface LayerDef {
  key: keyof MapLayerVisibility;
  label: string;
  info?: string;
  modes: MapMode[];
}

const LAYER_DEFS: LayerDef[] = [
  { key: 'boundaries', label: 'Municipality boundaries', modes: ['incident', 'cluster', 'persistence'] },
  { key: 'incidents', label: 'Raw incidents', modes: ['incident'] },
  { key: 'clusters', label: 'Cluster envelopes and counts', modes: ['cluster'] },
  { key: 'core', label: 'Core points (zoom 13+)', modes: ['cluster'] },
  {
    key: 'border',
    label: 'Border points',
    info: 'Incidents inside a cluster that have fewer than min-samples neighbours within epsilon. They belong to the cluster, but are not themselves dense enough to be core points.',
    modes: ['cluster'],
  },
  { key: 'noise', label: 'Noise points', modes: ['cluster'] },
  { key: 'persistence', label: 'Persistence hotspots', modes: ['persistence'] },
  {
    key: 'heatmap',
    label: 'Heatmap (density)',
    info: 'Visual point-density only — this is NOT DBSCAN output and does not represent clusters.',
    modes: ['incident'],
  },
];

export function LayerControl({
  mode,
  visibility,
  onChange,
}: {
  mode: MapMode;
  visibility: MapLayerVisibility;
  onChange: (visibility: MapLayerVisibility) => void;
}) {
  const relevant = LAYER_DEFS.filter((l) => l.modes.includes(mode));
  if (relevant.length === 0) return null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow">
      <h4 className="mb-2 text-xs font-semibold text-slate-700">Layers</h4>
      <div className="space-y-1.5">
        {relevant.map((layer) => (
          <label key={layer.key} className="flex items-center gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              checked={visibility[layer.key]}
              onChange={(e) => onChange({ ...visibility, [layer.key]: e.target.checked })}
              className="h-3.5 w-3.5 accent-slate-900"
            />
            {layer.label}
            {layer.info && <InfoIcon text={layer.info} />}
          </label>
        ))}
      </div>
    </div>
  );
}
