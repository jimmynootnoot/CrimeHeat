import { useEffect, useMemo, useState } from 'react';
import { GeoJSON, Marker, Tooltip, useMapEvents } from 'react-leaflet';
import type { Feature, FeatureCollection } from 'geojson';
import L, { type LatLngBounds, type PathOptions } from 'leaflet';
import { fetchClusters } from '../../api/endpoints';
import type { AnalysisMetadata, ClusterFeatureProperties, MapFilterState } from '../../types';
import { locationIcon } from './locationIcon';
import { fitResultBounds } from './mapBounds';

const CORE_ZOOM = 13;
const isExtent = (feature: Feature) => feature.geometry.type !== 'Point';

export function ClusterLayer({
  filters, showClusters, showCore, showBorder, showNoise, selectedClusterId,
  onSelectCluster, onMetadata, onLoadingChange, onBoundsChange, onError,
}: {
  filters: MapFilterState;
  showClusters: boolean;
  showCore: boolean;
  showBorder: boolean;
  showNoise: boolean;
  selectedClusterId: number | null;
  onSelectCluster: (props: ClusterFeatureProperties) => void;
  onMetadata: (meta: AnalysisMetadata) => void;
  onLoadingChange?: (loading: boolean) => void;
  onBoundsChange: (bounds: LatLngBounds | null) => void;
  onError: (error: string | null) => void;
}) {
  const map = useMapEvents({ zoomend: () => setZoom(map.getZoom()) });
  const [zoom, setZoom] = useState(map.getZoom());
  const [clusters, setClusters] = useState<FeatureCollection | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setClusters(null);
    onMetadata({});
    onError(null);
    onLoadingChange?.(true);
    fetchClusters({
      municipality: filters.municipality || undefined,
      barangay: filters.barangay || undefined,
      crime_type: filters.crime_type || undefined,
      year: filters.year === 'all' ? undefined : filters.year,
    }, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        setClusters(data);
        setVersion((v) => v + 1);
        onMetadata(data.metadata ?? {});
      })
      .catch(() => {
        if (!controller.signal.aborted) onError('Could not load clusters. Retry this analysis.');
      })
      .finally(() => { if (!controller.signal.aborted) onLoadingChange?.(false); });
    return () => controller.abort();
  }, [filters.municipality, filters.barangay, filters.crime_type, filters.year, onMetadata, onLoadingChange, onError]);

  const coreVisible = showCore && zoom >= CORE_ZOOM;
  const filtered = useMemo<FeatureCollection>(() => ({
    type: 'FeatureCollection',
    features: (clusters?.features ?? []).filter((f) => {
      if (isExtent(f)) return showClusters;
      if (f.properties?.status === 'core') return coreVisible;
      if (f.properties?.status === 'border') return showBorder;
      return showNoise;
    }),
  }), [clusters, showClusters, coreVisible, showBorder, showNoise]);

  useEffect(() => {
    const bounds = L.geoJSON(filtered).getBounds();
    onBoundsChange(bounds.isValid() ? bounds : null);
  }, [filtered, onBoundsChange]);

  if (!clusters) return null;

  const extents = clusters.features.filter(isExtent);
  function selectCluster(id: number | null) {
    const extent = extents.find((f) => f.properties?.cluster_id === id);
    if (!extent) return;
    onSelectCluster(extent.properties as ClusterFeatureProperties);
    fitResultBounds(map, L.geoJSON(extent).getBounds(), true);
  }

  function style(feature?: Feature): PathOptions {
    const p = feature?.properties as ClusterFeatureProperties | undefined;
    const selected = selectedClusterId !== null && p?.cluster_id === selectedClusterId;
    const dimmed = selectedClusterId !== null && !selected;
    const opacity = dimmed ? 0.25 : 1;
    if (feature && isExtent(feature)) {
      return { color: selected ? '#991b1b' : '#dc2626', weight: selected ? 3.5 : 1.5,
        fillColor: '#ef4444', fillOpacity: selected ? 0.18 : dimmed ? 0.025 : 0.08, opacity };
    }
    if (p?.status === 'noise') {
      return { color: '#64748b', weight: 1, fillColor: '#94a3b8', fillOpacity: 0.5 * opacity, opacity };
    }
    return { color: '#b91c1c', weight: selected ? 2 : 1.5, fillColor: '#dc2626',
      fillOpacity: p?.status === 'border' ? 0 : 0.9 * opacity, opacity };
  }

  return (
    <>
      <GeoJSON
        key={`${version}-${showClusters}-${coreVisible}-${showBorder}-${showNoise}-${selectedClusterId}`}
        data={filtered}
        style={style}
        pointToLayer={(feature, latlng) => new L.CircleMarker(latlng, {
          ...style(feature), radius: feature.properties?.status === 'noise' ? 3 : 4,
        })}
        onEachFeature={(feature, layer) => {
          const p = feature.properties as ClusterFeatureProperties;
          if (isExtent(feature) || p.cluster_id !== null) {
            layer.on('click', () => selectCluster(p.cluster_id));
            if (!isExtent(feature)) {
              layer.bindTooltip(`${p.status === 'core' ? 'Core' : 'Border'} point · Cluster #${p.cluster_id} · Click for cluster details`);
            }
          } else {
            layer.bindPopup('Noise point — not part of any DBSCAN cluster');
          }
        }}
      />
      {showClusters && extents.map((feature) => {
        const p = feature.properties as ClusterFeatureProperties;
        if (!p.centroid || !p.centroid.every(Number.isFinite)) return null;
        const selected = selectedClusterId === p.cluster_id;
        const label = `Cluster #${p.cluster_id}: ${p.point_count} incidents`;
        return (
          <Marker
            key={`${version}-${p.run_id}-${p.cluster_id}`}
            position={[p.centroid[1], p.centroid[0]]}
            icon={locationIcon(String(p.point_count), selected ? '#991b1b' : '#dc2626', label)}
            opacity={selectedClusterId !== null && !selected ? 0.3 : 1}
            zIndexOffset={selected ? 1000 : 0}
            title={label}
            alt={label}
            eventHandlers={{ click: () => selectCluster(p.cluster_id) }}
          >
            <Tooltip direction="top" className="location-tooltip">
              <div>{label}<br /><span className="font-normal">{p.dominant_crime_type ?? 'Mixed crime types'} · Click for details</span></div>
            </Tooltip>
          </Marker>
        );
      })}
    </>
  );
}
