import { Polygon } from 'react-leaflet';
import type { LatLngBounds } from 'leaflet';

// A generous rectangle covering any pan/zoom a user could reach, used as the
// outer ring of a donut polygon so everything outside the PPALMA study area
// reads as visually de-emphasized rather than a first-class part of the map.
const WORLD_RING: [number, number][] = [
  [-85, -190],
  [-85, 190],
  [85, 190],
  [85, -190],
];

export function StudyAreaMask({ bounds }: { bounds: LatLngBounds | null }) {
  if (!bounds) return null;

  const padded = bounds.pad(0.5);
  const sw = padded.getSouthWest();
  const ne = padded.getNorthEast();
  const holeRing: [number, number][] = [
    [sw.lat, sw.lng],
    [sw.lat, ne.lng],
    [ne.lat, ne.lng],
    [ne.lat, sw.lng],
  ];

  return (
    <Polygon
      positions={[WORLD_RING, holeRing]}
      pathOptions={{ stroke: false, fillColor: '#0f172a', fillOpacity: 0.45, interactive: false }}
    />
  );
}
