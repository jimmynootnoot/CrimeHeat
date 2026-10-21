import { divIcon } from 'leaflet';

/** Build labels as DOM text so data can never become marker HTML. */
export function locationIcon(value: string, color: string, label: string, size = 48) {
  const badge = document.createElement('span');
  badge.className = 'location-badge';
  badge.style.setProperty('--location-color', color);
  badge.style.setProperty('--location-size', `${size}px`);
  badge.textContent = value;
  badge.setAttribute('aria-label', label);
  return divIcon({
    className: 'location-marker',
    html: badge,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    tooltipAnchor: [0, -(size / 2 + 4)],
  });
}

/**
 * Marker diameter for a hotspot holding `count` incidents.
 *
 * Area is scaled proportionally to the count (diameter by its square root),
 * which is the standard proportional-symbol construction: doubling the
 * incidents doubles the ink, so the eye compares magnitudes rather than radii.
 * Clamped so the smallest chain stays legible and the largest cannot swallow
 * the municipality it sits in.
 */
export function magnitudeSize(count: number, min = 28, max = 60): number {
  const reference = 60; // incidents at which a marker reaches full size
  const scaled = min + (max - min) * Math.sqrt(Math.min(count, reference) / reference);
  return Math.round(Math.max(min, Math.min(max, scaled)));
}
