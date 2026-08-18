import { useMap } from 'react-leaflet';
import type { LatLngBounds } from 'leaflet';

export function MapViewControls({
  getBoundaryBounds,
  getVisibleBounds,
}: {
  getBoundaryBounds: () => LatLngBounds | null;
  getVisibleBounds: () => LatLngBounds | null;
}) {
  const map = useMap();

  function fitTo(bounds: LatLngBounds | null) {
    if (bounds && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [24, 24] });
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
        onClick={() => fitTo(getVisibleBounds())}
        className="rounded px-2 py-1 text-left text-xs font-medium text-slate-600 hover:bg-slate-100"
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
