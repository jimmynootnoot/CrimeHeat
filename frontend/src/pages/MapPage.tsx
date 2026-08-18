import { useEffect, useState } from 'react';
import { PPALMAMap } from '../components/map/PPALMAMap';
import { ModeToggle } from '../components/map/ModeToggle';
import { FilterPanel } from '../components/map/FilterPanel';
import { TimelineControl } from '../components/map/TimelineControl';
import { LayerControl } from '../components/map/LayerControl';
import { MunicipalitySidePanel } from '../components/map/MunicipalitySidePanel';
import { ClusterDetailPanel } from '../components/map/ClusterDetailPanel';
import { PersistenceDetailPanel } from '../components/map/PersistenceDetailPanel';
import { MapLegend } from '../components/map/MapLegend';
import { ErrorState } from '../components/ui/ErrorState';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import {
  fetchBarangays,
  fetchDashboardSummary,
  fetchMunicipalityStats,
  fetchYearsAvailable,
} from '../api/endpoints';
import type {
  AnalysisMetadata,
  ClusterFeatureProperties,
  MapFilterState,
  MapLayerVisibility,
  MapMode,
  MunicipalityStats,
  PersistenceFeatureProperties,
} from '../types';

const DEFAULT_FILTERS: MapFilterState = {
  municipality: '',
  barangay: '',
  crime_type: '',
  year: 'all',
  cluster_status: 'all',
  persistence_category: 'all',
};

const DEFAULT_LAYERS: MapLayerVisibility = {
  boundaries: true,
  incidents: true,
  clusters: true,
  noise: true,
  persistence: true,
  heatmap: false,
};

const FILTERS_STORAGE_KEY = 'ppalma_last_filters';

function loadStoredFilters(): MapFilterState {
  try {
    const raw = localStorage.getItem(FILTERS_STORAGE_KEY);
    if (!raw) return DEFAULT_FILTERS;
    return { ...DEFAULT_FILTERS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_FILTERS;
  }
}

type Selection =
  | { kind: 'municipality'; name: string }
  | { kind: 'cluster'; props: ClusterFeatureProperties }
  | { kind: 'persistence'; props: PersistenceFeatureProperties }
  | null;

export function MapPage() {
  const [mode, setMode] = useState<MapMode>('persistence');
  const [filters, setFilters] = useState<MapFilterState>(loadStoredFilters);
  const debouncedFilters = useDebouncedValue(filters, 300);

  const [layerVisibility, setLayerVisibility] = useState<MapLayerVisibility>(DEFAULT_LAYERS);
  const [years, setYears] = useState<number[]>([]);
  const [barangays, setBarangays] = useState<string[]>([]);
  const [incidentCounts, setIncidentCounts] = useState<Record<string, number>>({});
  const [metadata, setMetadata] = useState<AnalysisMetadata>({});
  const [loadError, setLoadError] = useState(false);

  const [selection, setSelection] = useState<Selection>(null);
  const [municipalityStats, setMunicipalityStats] = useState<MunicipalityStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  useEffect(() => {
    fetchYearsAvailable().then(setYears).catch(() => setYears([]));
    fetchDashboardSummary()
      .then((summary) => setIncidentCounts(summary.municipality_breakdown))
      .catch(() => setLoadError(true));
  }, []);

  useEffect(() => {
    localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(filters));
  }, [filters]);

  useEffect(() => {
    if (!filters.municipality) {
      setBarangays([]);
      return;
    }
    fetchBarangays(filters.municipality).then(setBarangays).catch(() => setBarangays([]));
  }, [filters.municipality]);

  function handleMunicipalityClick(name: string) {
    setSelection({ kind: 'municipality', name });
    setStatsLoading(true);
    fetchMunicipalityStats(name)
      .then(setMunicipalityStats)
      .catch(() => setMunicipalityStats(null))
      .finally(() => setStatsLoading(false));
  }

  function closeDrawer() {
    setSelection(null);
    setMunicipalityStats(null);
  }

  if (loadError) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-50">
        <ErrorState
          message="Could not reach the backend. Confirm the API is running and VITE_API_URL is correct."
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <PPALMAMap
        mode={mode}
        filters={debouncedFilters}
        layerVisibility={layerVisibility}
        activeMunicipality={selection?.kind === 'municipality' ? selection.name : null}
        incidentCounts={incidentCounts}
        onMunicipalityClick={handleMunicipalityClick}
        onSelectCluster={(props) => setSelection({ kind: 'cluster', props })}
        onSelectPersistence={(props) => setSelection({ kind: 'persistence', props })}
        onMetadata={(meta) => setMetadata((prev) => ({ ...prev, ...meta }))}
      />

      <div className="absolute top-3 left-3 z-[900] flex flex-col gap-3">
        <ModeToggle mode={mode} onChange={setMode} />
        <FilterPanel mode={mode} filters={filters} onChange={setFilters} barangays={barangays} metadata={metadata} />
        {(mode === 'incident' || mode === 'cluster') && (
          <TimelineControl
            years={years}
            value={filters.year}
            onChange={(year) => setFilters((f) => ({ ...f, year }))}
          />
        )}
        <LayerControl mode={mode} visibility={layerVisibility} onChange={setLayerVisibility} />
        <MapLegend mode={mode} filters={filters} />
      </div>

      {selection?.kind === 'municipality' && (
        <MunicipalitySidePanel
          name={selection.name}
          stats={municipalityStats}
          loading={statsLoading}
          onClose={closeDrawer}
        />
      )}
      {selection?.kind === 'cluster' && (
        <ClusterDetailPanel cluster={selection.props} onClose={closeDrawer} />
      )}
      {selection?.kind === 'persistence' && (
        <PersistenceDetailPanel record={selection.props} onClose={closeDrawer} />
      )}
    </div>
  );
}
