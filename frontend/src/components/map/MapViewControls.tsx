import { useMap } from 'react-leaflet';
import type { LatLngBounds } from 'leaflet';
import { fitResultBounds } from './mapBounds';

export function MapViewControls({
  getBoundaryBounds,
  visibleBounds,
}: {
  getBoundaryBounds: () => LatLngBounds | null;
  visibleBounds: LatLngBounds | null;
}) {
  const map = useMap();

  function fitTo(bounds: LatLngBounds | null) {
    if (bounds && bounds.isValid()) {
      fitResultBounds(map, bounds);
    }
  }

  return (
    <div className="flex flex-col gap-1 rounded-lg border border-slate-200 bg-white p-1.5 shadow">
      <button
        onClick={() => fitTo(getBoundaryBounds())}
        className="rounded px-2 py-1 text-left text-xs font-medium text-slate-600 hover:bg-slate-100"
      >
        Fit to PPALMA
      </button>
      <button
        onClick={() => fitTo(visibleBounds)}
        disabled={!visibleBounds?.isValid()}
        className="rounded px-2 py-1 text-left text-xs font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Fit to visible results
      </button>
      <button
        onClick={() => fitTo(getBoundaryBounds())}
        className="rounded px-2 py-1 text-left text-xs font-medium text-slate-600 hover:bg-slate-100"
      >
        Reset view
      </button>
    </div>
  );
}
