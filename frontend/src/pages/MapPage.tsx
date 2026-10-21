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
import { AnalysisSummary } from '../components/map/AnalysisSummary';
import { ErrorState } from '../components/ui/ErrorState';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import {
  fetchBarangays,
  fetchIncidentSummary,
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
  core: true,
  border: true,
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
  const countScope = JSON.stringify([
    debouncedFilters.municipality,
    debouncedFilters.barangay,
    debouncedFilters.crime_type,
    mode === 'persistence' ? 'all' : debouncedFilters.year,
  ]);
  const [incidentSummary, setIncidentSummary] = useState<{
    scope: string;
    municipality_breakdown: Record<string, number>;
    bounds: [number, number, number, number] | null;
    focus: [number, number] | null;
  } | null>(null);
  const summaryReady = incidentSummary?.scope === countScope;
  const incidentCounts = summaryReady ? incidentSummary.municipality_breakdown : null;
  const filteredIncidentBounds = summaryReady ? incidentSummary.bounds : null;
  const barangayFocus = summaryReady ? incidentSummary.focus : null;
  const [metadata, setMetadata] = useState<AnalysisMetadata>({});
  const [loadError, setLoadError] = useState(false);
  const [layerLoading, setLayerLoading] = useState(false);
  const [layerError, setLayerError] = useState<string | null>(null);
  const [analysisRevision, setAnalysisRevision] = useState(0);

  const [selection, setSelection] = useState<Selection>(null);
  const [municipalityStats, setMunicipalityStats] = useState<MunicipalityStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  useEffect(() => {
    fetchYearsAvailable().then(setYears).catch(() => setYears([]));
  }, []);

  // Persistence spans every analyzed year. Its category filter selects chains,
  // while boundary counts describe the underlying incident scope.
  const countYear = mode === 'persistence' || debouncedFilters.year === 'all' ? undefined : debouncedFilters.year;
  useEffect(() => {
    const controller = new AbortController();
    setLoadError(false);
    fetchIncidentSummary({
      municipality: debouncedFilters.municipality || undefined,
      barangay: debouncedFilters.barangay || undefined,
      crime_type: debouncedFilters.crime_type || undefined,
      year: countYear,
    }, controller.signal)
      .then((summary) => {
        if (!controller.signal.aborted) {
          setIncidentSummary({
            scope: countScope,
            municipality_breakdown: summary.municipality_breakdown,
            bounds: summary.bounds,
            focus: summary.focus,
          });
        }
      })
      .catch(() => { if (!controller.signal.aborted) setLoadError(true); });
    return () => controller.abort();
  }, [debouncedFilters.municipality, debouncedFilters.barangay, debouncedFilters.crime_type, countYear, countScope]);

  useEffect(() => {
    setSelection(null);
    setMetadata({});
    setLayerError(null);
  }, [mode, filters.municipality, filters.barangay, filters.crime_type, filters.year, filters.persistence_category, debouncedFilters, analysisRevision]);

  useEffect(() => {
    localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(filters));
  }, [filters]);

  useEffect(() => {
    if (!filters.municipality) {
      setBarangays([]);
      return;
    }
    let active = true;
    setBarangays([]);
    fetchBarangays(filters.municipality)
      .then((items) => { if (active) setBarangays(items); })
      .catch(() => { if (active) setBarangays([]); });
    return () => { active = false; };
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
        selectedClusterId={selection?.kind === 'cluster' ? selection.props.cluster_id : null}
        analysisRevision={analysisRevision}
        incidentCounts={incidentCounts}
        filteredIncidentBounds={filteredIncidentBounds}
        barangayFocus={barangayFocus}
        localityBoundsReady={summaryReady}
        onMunicipalityClick={handleMunicipalityClick}
        onSelectCluster={(props) => setSelection({ kind: 'cluster', props })}
        onSelectPersistence={(props) => setSelection({ kind: 'persistence', props })}
        onMetadata={setMetadata}
        onLoadingChange={setLayerLoading}
        onError={setLayerError}
      />

      {layerLoading && (mode === 'cluster' || mode === 'persistence') && (
        <div className="absolute top-3 left-1/2 z-[1000] -translate-x-1/2 rounded-full bg-slate-900/90 px-4 py-1.5 text-sm text-white shadow-lg">
          {mode === 'cluster' ? 'Computing DBSCAN clusters…' : 'Computing persistence chains…'}
        </div>
      )}

      {/* The control stack can be taller than the viewport (filters + timeline
          + layers + legend). Cap it to the map area and let it scroll on its
          own, so the bottom panels stay reachable on short screens instead of
          being clipped off the edge. `overscroll-contain` stops the scroll
          from chaining out to the page once the stack hits its end. */}
      <div className="absolute top-3 left-3 z-[900] flex max-h-[calc(100%-1.5rem)] flex-col gap-3 overflow-y-auto overscroll-contain pr-1 pb-1">
        <ModeToggle mode={mode} onChange={setMode} />
        {mode === 'cluster' && <AnalysisSummary metadata={metadata} loading={layerLoading || filters !== debouncedFilters} error={layerError} onRetry={() => setAnalysisRevision((v) => v + 1)} />}
        <FilterPanel mode={mode} filters={filters} onChange={setFilters} barangays={barangays} metadata={metadata} />
        {(mode === 'incident' || mode === 'cluster') && (
          <TimelineControl
            years={years}
            value={filters.year}
            onChange={(year) => setFilters((f) => ({ ...f, year }))}
          />
        )}
        <LayerControl mode={mode} visibility={layerVisibility} onChange={setLayerVisibility} />
        <MapLegend mode={mode} filters={filters} visibility={layerVisibility} />
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
