import { useEffect, useState } from 'react';
import { GeoJSON, useMap } from 'react-leaflet';
import type { FeatureCollection } from 'geojson';
import { geoJSON, Marker as LeafletMarker, type LatLngBounds } from 'leaflet';
import { fetchPersistence } from '../../api/endpoints';
import type { MapFilterState, PersistenceFeatureProperties } from '../../types';
import { PERSISTENCE_STYLES } from './persistenceStyles';
import { locationIcon, magnitudeSize } from './locationIcon';
import { PERSISTENCE_CATEGORY_LABELS } from '../../types';

export function PersistenceLayer({
  filters,
  onSelectRecord,
  onMetadata,
  onLoadingChange,
  onBoundsChange,
}: {
  filters: MapFilterState;
  onSelectRecord: (props: PersistenceFeatureProperties) => void;
  onMetadata?: (meta: { persistence_score_threshold?: number; match_distance_km?: number }) => void;
  onLoadingChange?: (loading: boolean) => void;
  onBoundsChange: (bounds: LatLngBounds | null) => void;
}) {
  const map = useMap();
  const [data, setData] = useState<FeatureCollection | null>(null);
  // Bumped only when a fetch actually resolves with new data — NOT on every
  // filter change. react-leaflet's <GeoJSON> can't react to a changed `data`
  // prop in place (Leaflet bakes the data in at layer creation), so it must
  // be remounted via `key` to show new data. Keying on `filters` directly
  // remounted it the instant filters changed, which is synchronous and
  // happens *before* the async fetch resolves — so the freshly-remounted
  // layer got baked in with whatever `data` was still sitting in state (the
  // previous filter's result, or null on first load), and then never
  // updated again since the key didn't change a second time. Net effect:
  // the map always showed the *previous* filter's results, one step behind,
  // or nothing at all on a first load with a narrow filter.
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const bounds = data ? geoJSON(data).getBounds() : null;
    onBoundsChange(bounds?.isValid() ? bounds : null);
  }, [data, onBoundsChange]);

  useEffect(() => {
    const controller = new AbortController();
    onLoadingChange?.(true);
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
        setVersion((v) => v + 1);
        if (res.metadata) onMetadata?.(res.metadata);
        onLoadingChange?.(false);
      })
      .catch((err) => {
        if (err.name !== 'CanceledError' && err.name !== 'AbortError') {
          console.error('Failed to load persistence data:', err);
          onLoadingChange?.(false);
        }
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.municipality, filters.barangay, filters.crime_type, filters.persistence_category]);

  if (!data) return null;

  return (
    <GeoJSON
      key={version}
      data={data}
      // The shaded hull is the hotspot's real extent; the badge only labels it.
      style={(feature) => {
        const p = feature?.properties as PersistenceFeatureProperties;
        const base = PERSISTENCE_STYLES[p.category];
        return {
          color: base.color,
          fillColor: base.fillColor,
          weight: base.weight,
          fillOpacity: base.fillOpacity,
          // Historical chains are drawn dashed: they recurred strongly and then
          // stopped, so they read as a past pattern rather than a live one
          // without relying on colour alone to say so.
          dashArray: p.category === 'historical_persistent' ? '6 4' : undefined,
        };
      }}
      pointToLayer={(feature, latlng) => {
        const p = feature.properties as PersistenceFeatureProperties;
        const style = PERSISTENCE_STYLES[p.category];
        const score = `${Math.round(p.persistence_score * 100)}%`;
        const count = p.incident_count ?? 0;
        const label =
          `${p.municipality}: ${PERSISTENCE_CATEGORY_LABELS[p.category]}, ${score} persistence, ` +
          `${count} incidents across ${p.period_count} of ${p.total_periods_analyzed} periods`;
        return new LeafletMarker(latlng, {
          icon: locationIcon(score, style.color, label, magnitudeSize(count)),
          title: label,
          alt: label,
          // Labels sit above the shaded extents regardless of draw order.
          zIndexOffset: 500,
        });
      }}
      onEachFeature={(feature, layer) => {
        const p = feature.properties as PersistenceFeatureProperties;
        const tooltip = document.createElement('div');
        const heading = document.createElement('div');
        heading.textContent = `${p.municipality} · ${PERSISTENCE_CATEGORY_LABELS[p.category]}`;
        const detail = document.createElement('div');
        detail.style.fontWeight = '400';
        detail.textContent =
          `${p.incident_count ?? 0} incidents · present in ${p.period_count} of ` +
          `${p.total_periods_analyzed} years (${p.first_year}–${p.latest_year})`;
        tooltip.append(heading, detail);
        layer.bindTooltip(tooltip, { direction: 'top', className: 'location-tooltip', sticky: true });
        layer.on('click', () => {
          if (layer instanceof LeafletMarker) {
            map.panTo(layer.getLatLng(), { animate: !window.matchMedia('(prefers-reduced-motion: reduce)').matches });
          }
          onSelectRecord(p);
        });
      }}
    />
  );
}
