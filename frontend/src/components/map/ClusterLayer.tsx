import { useEffect, useState } from 'react';
import { GeoJSON } from 'react-leaflet';
import type { Feature, FeatureCollection } from 'geojson';
import { CircleMarker as LeafletCircleMarker, type Layer } from 'leaflet';
import { fetchClusters } from '../../api/endpoints';
import type { ClusterFeatureProperties, MapFilterState } from '../../types';

const CORE_STYLE = { color: '#991b1b', weight: 2.5, fillColor: '#ef4444', fillOpacity: 0.35 };
const NOISE_STYLE = { color: '#64748b', weight: 1, fillColor: '#94a3b8', fillOpacity: 0.5 };

export function ClusterLayer({
  filters,
  showClusters,
  showNoise,
  onSelectCluster,
  onMetadata,
}: {
  filters: MapFilterState;
  showClusters: boolean;
  showNoise: boolean;
  onSelectCluster: (props: ClusterFeatureProperties) => void;
  onMetadata?: (meta: { eps_km?: number; min_samples?: number }) => void;
}) {
  const [clusters, setClusters] = useState<FeatureCollection | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchClusters(
      {
        municipality: filters.municipality || undefined,
        crime_type: filters.crime_type || undefined,
        year: filters.year === 'all' ? undefined : filters.year,
      },
      controller.signal
    )
      .then((data) => {
        setClusters(data);
        if (data.metadata) onMetadata?.(data.metadata);
      })
      .catch((err) => {
        if (err.name !== 'CanceledError' && err.name !== 'AbortError') {
          console.error('Failed to load clusters:', err);
        }
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.municipality, filters.crime_type, filters.year]);

  if (!clusters) return null;

  const filtered: FeatureCollection = {
    ...clusters,
    features: clusters.features.filter((f) => {
      const status = f.properties?.status;
      if (status === 'core') return showClusters;
      if (status === 'noise') return showNoise;
      return true;
    }),
  };

  return (
    <GeoJSON
      key={JSON.stringify(filters) + showClusters + showNoise}
      data={filtered}
      style={(feature) => (feature?.properties?.status === 'noise' ? NOISE_STYLE : CORE_STYLE)}
      pointToLayer={(_feature, latlng) =>
        new LeafletCircleMarker(latlng, { ...NOISE_STYLE, radius: 3 })
      }
      onEachFeature={(feature: Feature, layer: Layer) => {
        const p = feature.properties as ClusterFeatureProperties;
        if (p.status === 'core') {
          layer.bindPopup(
            `<div style="font-size:13px"><b>Cluster #${p.cluster_id}</b><br/>${p.point_count} incidents — dominant: ${
              p.dominant_crime_type ?? 'n/a'
            }</div>`
          );
          layer.on('click', () => onSelectCluster(p));
        } else {
          layer.bindPopup('<div style="font-size:12px">Noise point — not part of any DBSCAN cluster</div>');
        }
      }}
    />
  );
}
