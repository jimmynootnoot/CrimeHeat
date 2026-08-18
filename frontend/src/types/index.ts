export interface Municipality {
  id: number;
  psgc_code: string;
  name: string;
}

export interface MunicipalityStats {
  municipality_id: number;
  name: string;
  total_incidents: number;
  incidents_by_crime_type: Record<string, number>;
  incidents_by_year: Record<string, number>;
  active_persistent_clusters: number;
}

/** Compact stats used for the boundary hover tooltip — derived client-side
 * from the dashboard summary's municipality_breakdown, so hovering never
 * fires a new network request. */
export interface MunicipalityHoverStats {
  name: string;
  totalIncidents: number;
}

export interface Incident {
  id: number;
  incident_id: string;
  crime_type: string;
  incident_date: string;
  incident_time: string | null;
  municipality: string;
  barangay: string;
  general_location: string | null;
  latitude: number;
  longitude: number;
  source: 'synthetic' | 'pnp';
}

export interface IncidentFilters {
  municipality?: string;
  barangay?: string;
  crime_type?: string;
  year?: number;
  q?: string;
  page?: number;
  page_size?: number;
}

export interface ClusterFeatureProperties {
  cluster_id: number | null;
  run_id: number;
  year: number | null;
  crime_type: string | null;
  point_count: number;
  status: 'core' | 'noise';
  centroid?: [number, number];
  municipality?: string;
  dominant_crime_type?: string;
  barangays?: string[];
}

export type PersistenceCategory =
  | 'temporary'
  | 'intermittent'
  | 'historical_persistent'
  | 'active_persistent';

export interface PersistenceFeatureProperties {
  persistence_id: number;
  municipality: string;
  category: PersistenceCategory;
  periods_present: number[];
  period_count: number;
  persistence_score: number;
  total_periods_analyzed: number;
  first_year: number | null;
  latest_year: number | null;
  crime_type: string | null;
}

export interface AnalysisMetadata {
  eps_km?: number;
  min_samples?: number;
  match_distance_km?: number;
  persistence_score_threshold?: number;
}

export type MapMode = 'incident' | 'cluster' | 'persistence';

export interface MapFilterState {
  municipality: string;
  barangay: string;
  crime_type: string;
  year: number | 'all';
  cluster_status: string;
  persistence_category: string;
}

export interface MapLayerVisibility {
  boundaries: boolean;
  incidents: boolean;
  clusters: boolean;
  noise: boolean;
  persistence: boolean;
  heatmap: boolean;
}

export const PERSISTENCE_CATEGORY_LABELS: Record<PersistenceCategory, string> = {
  temporary: 'Temporary',
  intermittent: 'Intermittent',
  historical_persistent: 'Historical persistent',
  active_persistent: 'Active persistent',
};

export const PERSISTENCE_CATEGORY_DESCRIPTIONS: Record<PersistenceCategory, string> = {
  temporary: 'Appeared in exactly one analyzed period — not yet established as recurring.',
  intermittent: 'Recurred in 2+ periods, but below the persistence-score threshold.',
  historical_persistent:
    'Recurred strongly (score at/above threshold) but was NOT present in the most recent period — may have stopped.',
  active_persistent:
    'Recurred strongly (score at/above threshold) AND is present in the most recent period — the strongest ongoing signal.',
};

/** The eight index crimes analyzed by this study.
 * Must stay in sync with `INDEX_CRIME_TYPES` in backend/app/core/taxonomy.py —
 * that module is the authoritative definition and the importer validates
 * against it. */
export const CRIME_TYPES = [
  'Murder',
  'Homicide',
  'Physical Injury',
  'Rape',
  'Robbery',
  'Theft',
  'Carnapping',
  'Cattle Rustling',
] as const;

export const CRIMES_AGAINST_PERSONS: readonly string[] = [
  'Murder',
  'Homicide',
  'Physical Injury',
  'Rape',
];

/** Canonical display spelling. The importer additionally accepts "Pigkawayan"
 * (the spelling used by the PSGC boundary source) and standardizes it. */
export const PPALMA_MUNICIPALITIES = [
  'Alamada',
  'Aleosan',
  'Libungan',
  'Midsayap',
  'Pigcawayan',
  'Pikit',
] as const;

export type UserRole = 'viewer' | 'analyst' | 'admin';

export const ROLE_LABELS: Record<UserRole, string> = {
  viewer: 'Viewer',
  analyst: 'Analyst',
  admin: 'Administrator',
};

export const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  viewer: 'Read-only access to approved maps, summaries, and reports.',
  analyst: 'Can upload and validate datasets and run analyses. Cannot manage users or delete data.',
  admin: 'Full access, including user management, imports, deletions, and analytical parameters.',
};
