import type { PersistenceCategory } from '../../types';

/** Single source of truth for persistence-category styling, shared by
 * PersistenceLayer and MapLegend so the map and legend never drift apart.
 * Escalating emphasis is encoded in BOTH color AND border weight/opacity —
 * not color alone — per the accessibility requirement. */
export const PERSISTENCE_STYLES: Record<
  PersistenceCategory,
  { color: string; fillColor: string; weight: number; fillOpacity: number }
> = {
  temporary: { color: '#1d4ed8', fillColor: '#60a5fa', weight: 1, fillOpacity: 0.2 },
  intermittent: { color: '#b45309', fillColor: '#fbbf24', weight: 2, fillOpacity: 0.35 },
  historical_persistent: { color: '#dc2626', fillColor: '#fca5a5', weight: 3, fillOpacity: 0.5 },
  active_persistent: { color: '#991b1b', fillColor: '#ef4444', weight: 4, fillOpacity: 0.65 },
};
