import { useEffect, useState } from 'react';
import { GeoJSON } from 'react-leaflet';
import type { FeatureCollection } from 'geojson';
import { CircleMarker as LeafletCircleMarker } from 'leaflet';
import { fetchPersistence } from '../../api/endpoints';
import type { MapFilterState, PersistenceFeatureProperties } from '../../types';
import { PERSISTENCE_STYLES } from './persistenceStyles';

export function PersistenceLayer({
  filters,
  onSelectRecord,
  onMetadata,
}: {
  filters: MapFilterState;
  onSelectRecord: (props: PersistenceFeatureProperties) => void;
  onMetadata?: (meta: { persistence_score_threshold?: number; match_distance_km?: number }) => void;
}) {
  const [data, setData] = useState<FeatureCollection | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchPersistence(
      {
        municipality: filters.municipality || undefined,
        barangay: filters.barangay || undefined,
        crime_type: filters.crime_type || undefined,
        category:
          filters.persistence_category && filters.persistence_category !== 'all'
            ? filters.persistence_category
            : undefined,
      },
      controller.signal
    )
      .then((res) => {
        setData(res);
        if (res.metadata) onMetadata?.(res.metadata);
      })
      .catch((err) => {
        if (err.name !== 'CanceledError' && err.name !== 'AbortError') {
          console.error('Failed to load persistence data:', err);
        }
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.municipality, filters.barangay, filters.crime_type, filters.persistence_category]);

  if (!data) return null;

  return (
    <GeoJSON
      key={JSON.stringify(filters)}
      data={data}
      pointToLayer={(feature, latlng) => {
        const p = feature.properties as PersistenceFeatureProperties;
        const style = PERSISTENCE_STYLES[p.category];
        return new LeafletCircleMarker(latlng, {
          radius: 6 + p.persistence_score * 16,
          color: style.color,
          weight: style.weight,
          fillColor: style.fillColor,
          fillOpacity: style.fillOpacity,
        });
      }}
      onEachFeature={(feature, layer) => {
        const p = feature.properties as PersistenceFeatureProperties;
        layer.bindPopup(
          `<div style="font-size:13px"><b>${p.municipality}</b><br/>${p.category.replace('_', ' ')} — score ${Math.round(
            p.persistence_score * 100
          )}%<br/>Periods: ${p.periods_present.join(', ')}</div>`
        );
        layer.on('click', () => onSelectRecord(p));
      }}
    />
  );
}
