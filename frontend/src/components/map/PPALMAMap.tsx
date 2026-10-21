import { useCallback, useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import L, { type LatLngBounds } from 'leaflet';
import { BoundaryLayer } from './BoundaryLayer';
import { StudyAreaMask } from './StudyAreaMask';
import { IncidentLayer } from './IncidentLayer';
import { ClusterLayer } from './ClusterLayer';
import { PersistenceLayer } from './PersistenceLayer';
import { HeatmapLayer } from './HeatmapLayer';
import { ScaleBarControl } from './ScaleBarControl';
import { MapViewControls } from './MapViewControls';
import { fitResultBounds } from './mapBounds';
import type {
  AnalysisMetadata,
  ClusterFeatureProperties,
  Incident,
  MapFilterState,
  MapLayerVisibility,
  MapMode,
  PersistenceFeatureProperties,
} from '../../types';

const PPALMA_CENTER: [number, number] = [7.15, 124.5];

export function PPALMAMap({
  mode,
  filters,
  layerVisibility,
  activeMunicipality,
  selectedClusterId,
  analysisRevision,
  incidentCounts,
  filteredIncidentBounds,
  barangayFocus,
  localityBoundsReady,
  onMunicipalityClick,
  onMunicipalityBoundsReady,
  onSelectCluster,
  onSelectPersistence,
  onMetadata,
  onLoadingChange,
  onError,
}: {
  mode: MapMode;
  filters: MapFilterState;
  layerVisibility: MapLayerVisibility;
  activeMunicipality: string | null;
  selectedClusterId: number | null;
  analysisRevision: number;
  incidentCounts: Record<string, number> | null;
  filteredIncidentBounds: [number, number, number, number] | null;
  barangayFocus: [number, number] | null;
  localityBoundsReady: boolean;
  onMunicipalityClick: (name: string) => void;
  onMunicipalityBoundsReady?: (name: string, bounds: LatLngBounds) => void;
  onSelectCluster: (props: ClusterFeatureProperties) => void;
  onSelectPersistence: (props: PersistenceFeatureProperties) => void;
  onMetadata: (meta: AnalysisMetadata) => void;
  onLoadingChange?: (loading: boolean) => void;
  onError: (error: string | null) => void;
}) {
  const boundaryBoundsRef = useRef<LatLngBounds | null>(null);
  const [boundaryBounds, setBoundaryBounds] = useState<LatLngBounds | null>(null);
  const [municipalityBounds, setMunicipalityBounds] = useState<Record<string, LatLngBounds>>({});
  const scope = JSON.stringify([mode, filters.municipality, filters.barangay, filters.crime_type,
    mode === 'persistence' ? filters.persistence_category : filters.year, analysisRevision]);
  const [incidentResult, setIncidentResult] = useState<{ scope: string; points: [number, number][] } | null>(null);
  const [analysisBounds, setAnalysisBounds] = useState<{ scope: string; bounds: LatLngBounds | null } | null>(null);
  const visiblePoints = incidentResult?.scope === scope ? incidentResult.points : [];
  const handleIncidentsLoaded = useCallback((incidents: Incident[]) => {
    setIncidentResult({ scope, points: incidents.map((i) => [i.latitude, i.longitude]) });
  }, [scope]);
  const handleBoundsChange = useCallback((bounds: LatLngBounds | null) => {
    setAnalysisBounds({ scope, bounds });
  }, [scope]);
  const visibleBounds = mode === 'incident'
    ? (layerVisibility.incidents || layerVisibility.heatmap) && visiblePoints.length > 0 ? L.latLngBounds(visiblePoints) : null
    : (mode !== 'persistence' || layerVisibility.persistence) && analysisBounds?.scope === scope ? analysisBounds.bounds : null;

  return (
    <MapContainer center={PPALMA_CENTER} zoom={10} scrollWheelZoom className="h-full w-full">
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
      <ScaleBarControl />
      <StudyAreaMask bounds={boundaryBounds} />
      {layerVisibility.boundaries && (
        <BoundaryLayer
          onMunicipalityClick={onMunicipalityClick}
          activeMunicipality={activeMunicipality}
          incidentCounts={incidentCounts}
          initialFitEnabled={!filters.municipality}
          onBoundsReady={(b) => {
            boundaryBoundsRef.current = b;
            setBoundaryBounds(b);
          }}
          onMunicipalityBoundsReady={onMunicipalityBoundsReady}
          onInternalMunicipalityBoundsReady={(name, bounds) => {
            setMunicipalityBounds((current) => current[name] ? current : { ...current, [name]: bounds });
          }}
        />
      )}

      {mode === 'incident' && (layerVisibility.incidents || layerVisibility.heatmap) && (
        <IncidentLayer key={scope} filters={filters} showMarkers={layerVisibility.incidents} onIncidentsLoaded={handleIncidentsLoaded} />
      )}
      {mode === 'incident' && layerVisibility.heatmap && <HeatmapLayer points={visiblePoints} />}

      {mode === 'cluster' && (
        <ClusterLayer
          key={scope}
          filters={filters}
          showClusters={layerVisibility.clusters}
          showCore={layerVisibility.core}
          showBorder={layerVisibility.border}
          showNoise={layerVisibility.noise}
          selectedClusterId={selectedClusterId}
          onSelectCluster={onSelectCluster}
          onMetadata={onMetadata}
          onLoadingChange={onLoadingChange}
          onBoundsChange={handleBoundsChange}
          onError={onError}
        />
      )}

      {mode === 'persistence' && layerVisibility.persistence && (
        <PersistenceLayer
          key={scope}
          filters={filters}
          onSelectRecord={onSelectPersistence}
          onMetadata={onMetadata}
          onLoadingChange={onLoadingChange}
          onBoundsChange={handleBoundsChange}
        />
      )}

      <LocalityAutoFit
        municipality={filters.municipality}
        barangay={filters.barangay}
        municipalityBounds={filters.municipality ? municipalityBounds[filters.municipality] ?? null : boundaryBounds}
        filteredIncidentBounds={filteredIncidentBounds}
        barangayFocus={barangayFocus}
        localityBoundsReady={localityBoundsReady}
      />

      <MapViewControlsWrapper boundaryBoundsRef={boundaryBoundsRef} visibleBounds={visibleBounds} />
    </MapContainer>
  );
}

function LocalityAutoFit({
  municipality,
  barangay,
  municipalityBounds,
  filteredIncidentBounds,
  barangayFocus,
  localityBoundsReady,
}: {
  municipality: string;
  barangay: string;
  municipalityBounds: LatLngBounds | null;
  filteredIncidentBounds: [number, number, number, number] | null;
  barangayFocus: [number, number] | null;
  localityBoundsReady: boolean;
}) {
  const map = useMap();
  const lastFit = useRef('');

  useEffect(() => {
    const localityKey = `${municipality}|${barangay}`;
    if (lastFit.current === localityKey) return;

    if (!municipality) {
      if (municipalityBounds) {
        fitResultBounds(map, municipalityBounds);
        lastFit.current = localityKey;
      }
      return;
    }

    // Use the municipality-qualified official barangay centroid. Incident
    // extents are only a fallback because centroid-placed or generalized
    // records can be displaced from the locality named in the filter.
    if (barangay) {
      if (!localityBoundsReady) return;
      const bounds = barangayFocus
        ? L.latLngBounds(
            [barangayFocus[0] - 0.006, barangayFocus[1] - 0.006],
            [barangayFocus[0] + 0.006, barangayFocus[1] + 0.006],
          )
        : filteredIncidentBounds
          ? L.latLngBounds(
            [filteredIncidentBounds[1], filteredIncidentBounds[0]],
            [filteredIncidentBounds[3], filteredIncidentBounds[2]],
          )
          : municipalityBounds;
      if (bounds) {
        fitResultBounds(map, bounds);
        lastFit.current = localityKey;
      }
      return;
    }

    if (municipalityBounds) {
      fitResultBounds(map, municipalityBounds);
      lastFit.current = localityKey;
    }
  }, [map, municipality, barangay, municipalityBounds, filteredIncidentBounds, barangayFocus, localityBoundsReady]);

  return null;
}

/** Small indirection so MapViewControls (which needs useMap()) can read the
 * latest refs/state without re-mounting the whole map. */
function MapViewControlsWrapper({
  boundaryBoundsRef,
  visibleBounds,
}: {
  boundaryBoundsRef: React.RefObject<LatLngBounds | null>;
  visibleBounds: LatLngBounds | null;
}) {
  return (
    <div className="leaflet-top leaflet-right" style={{ marginTop: 180 }}>
      <div className="leaflet-control">
        <MapViewControls
          getBoundaryBounds={() => boundaryBoundsRef.current}
          visibleBounds={visibleBounds}
        />
      </div>
    </div>
  );
}
