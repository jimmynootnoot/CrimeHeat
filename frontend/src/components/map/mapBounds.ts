import type { LatLngBounds, Map } from 'leaflet';

/** Keep fitted results clear of the controls and an open detail drawer. */
export function fitResultBounds(map: Map, bounds: LatLngBounds | null, drawerOpen = false) {
  if (!bounds?.isValid()) return;
  const size = map.getSize();
  const desktop = size.x >= 900;
  map.fitBounds(bounds, {
    paddingTopLeft: desktop ? [288, 24] : [24, 24],
    paddingBottomRight: desktop ? [drawerOpen ? 356 : 24, 24] : [24, drawerOpen ? size.y * 0.47 : 24],
    maxZoom: 16,
    animate: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  });
}
