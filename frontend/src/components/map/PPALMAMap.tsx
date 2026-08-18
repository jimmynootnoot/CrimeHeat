import { useRef, useState } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import L, { type LatLngBounds } from 'leaflet';
import { BoundaryLayer } from './BoundaryLayer';
import { IncidentLayer } from './IncidentLayer';
import { ClusterLayer } from './ClusterLayer';
import { PersistenceLayer } from './PersistenceLayer';
import { HeatmapLayer } from './HeatmapLayer';
import { ScaleBarControl } from './ScaleBarControl';
import { MapViewControls } from './MapViewControls';
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
  incidentCounts,
  onMunicipalityClick,
  onMunicipalityBoundsReady,
  onSelectCluster,
  onSelectPersistence,
  onMetadata,
}: {
  mode: MapMode;
  filters: MapFilterState;
  layerVisibility: MapLayerVisibility;
  activeMunicipality: string | null;
  incidentCounts: Record<string, number>;
  onMunicipalityClick: (name: string) => void;
  onMunicipalityBoundsReady?: (name: string, bounds: LatLngBounds) => void;
  onSelectCluster: (props: ClusterFeatureProperties) => void;
  onSelectPersistence: (props: PersistenceFeatureProperties) => void;
  onMetadata: (meta: AnalysisMetadata) => void;
}) {
  const boundaryBoundsRef = useRef<LatLngBounds | null>(null);
  const [visiblePoints, setVisiblePoints] = useState<[number, number][]>([]);

  function handleIncidentsLoaded(incidents: Incident[]) {
    setVisiblePoints(incidents.map((i) => [i.latitude, i.longitude]));
  }

  return (
    <MapContainer center={PPALMA_CENTER} zoom={10} className="h-full w-full">
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
      <ScaleBarControl />
      {layerVisibility.boundaries && (
        <BoundaryLayer
          onMunicipalityClick={onMunicipalityClick}
          activeMunicipality={activeMunicipality}
          incidentCounts={incidentCounts}
          onBoundsReady={(b) => {
            boundaryBoundsRef.current = b;
          }}
          onMunicipalityBoundsReady={onMunicipalityBoundsReady}
        />
      )}

      {mode === 'incident' && layerVisibility.incidents && (
        <IncidentLayer filters={filters} onIncidentsLoaded={handleIncidentsLoaded} />
      )}
      {mode === 'incident' && layerVisibility.heatmap && <HeatmapLayer points={visiblePoints} />}

      {mode === 'cluster' && (
        <ClusterLayer
          filters={filters}
          showClusters={layerVisibility.clusters}
          showNoise={layerVisibility.noise}
          onSelectCluster={onSelectCluster}
          onMetadata={onMetadata}
        />
      )}

      {mode === 'persistence' && layerVisibility.persistence && (
        <PersistenceLayer filters={filters} onSelectRecord={onSelectPersistence} onMetadata={onMetadata} />
      )}

      <MapViewControlsWrapper boundaryBoundsRef={boundaryBoundsRef} visiblePoints={visiblePoints} />
    </MapContainer>
  );
}

/** Small indirection so MapViewControls (which needs useMap()) can read the
 * latest refs/state without re-mounting the whole map. */
function MapViewControlsWrapper({
  boundaryBoundsRef,
  visiblePoints,
}: {
  boundaryBoundsRef: React.RefObject<LatLngBounds | null>;
  visiblePoints: [number, number][];
}) {
  return (
    <div className="leaflet-top leaflet-right" style={{ marginTop: 180 }}>
      <div className="leaflet-control">
        <MapViewControls
          getBoundaryBounds={() => boundaryBoundsRef.current}
          getVisibleBounds={() => (visiblePoints.length > 0 ? L.latLngBounds(visiblePoints) : null)}
        />
      </div>
    </div>
  );
}
