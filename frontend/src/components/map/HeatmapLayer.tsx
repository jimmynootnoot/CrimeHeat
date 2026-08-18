import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';

/**
 * Wraps leaflet.heat directly against the Leaflet map instance (react-leaflet
 * has no first-party heatmap component). This is a visual density surface
 * only — explicitly NOT a DBSCAN result — see the "Visual density" label
 * wherever this layer is toggled/legended.
 */
export function HeatmapLayer({ points }: { points: [number, number][] }) {
  const map = useMap();

  useEffect(() => {
    if (points.length === 0) return;
    const heat = (L as typeof L & { heatLayer: (pts: [number, number][], opts?: object) => L.Layer }).heatLayer(
      points,
      { radius: 22, blur: 18, maxZoom: 14 }
    );
    heat.addTo(map);
    return () => {
      map.removeLayer(heat);
    };
  }, [map, points]);

  return null;
}
