import { useEffect, useRef, useState } from 'react';
import { GeoJSON, useMap } from 'react-leaflet';
import type { FeatureCollection, Feature } from 'geojson';
import type { Layer, LeafletMouseEvent, GeoJSON as LeafletGeoJSON, LatLngBounds } from 'leaflet';
import { fetchMunicipalityBoundaries } from '../../api/endpoints';
import { displayMunicipality } from '../../lib/taxonomy';

const DEFAULT_STYLE = { color: '#1e293b', weight: 1.5, fillColor: '#64748b', fillOpacity: 0.15 };
const HOVER_STYLE = { color: '#0f172a', weight: 3, fillColor: '#3b82f6', fillOpacity: 0.3 };
const DIMMED_STYLE = { color: '#94a3b8', weight: 1, fillColor: '#cbd5e1', fillOpacity: 0.05 };

export function BoundaryLayer({
  onMunicipalityClick,
  activeMunicipality,
  incidentCounts,
  onBoundsReady,
  onMunicipalityBoundsReady,
}: {
  onMunicipalityClick: (name: string) => void;
  activeMunicipality: string | null;
  incidentCounts: Record<string, number>;
  onBoundsReady?: (bounds: LatLngBounds) => void;
  onMunicipalityBoundsReady?: (name: string, bounds: LatLngBounds) => void;
}) {
  const map = useMap();
  const [boundaries, setBoundaries] = useState<FeatureCollection | null>(null);
  const geoJsonRef = useRef<LeafletGeoJSON | null>(null);
  const fitted = useRef(false);

  useEffect(() => {
    fetchMunicipalityBoundaries().then(setBoundaries);
  }, []);

  useEffect(() => {
    if (boundaries && geoJsonRef.current && !fitted.current) {
      const bounds = geoJsonRef.current.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [24, 24] });
        onBoundsReady?.(bounds);
        fitted.current = true;
      }
    }
  }, [boundaries, map, onBoundsReady]);

  if (!boundaries) return null;

  return (
    <GeoJSON
      ref={geoJsonRef}
      data={boundaries}
      style={(feature) => {
        // The boundary file is the PSGC source and uses its own spelling;
        // canonicalize so it matches the names used everywhere else.
        const name = displayMunicipality(feature?.properties?.adm3_en);
        if (name === activeMunicipality) return HOVER_STYLE;
        if (activeMunicipality) return DIMMED_STYLE;
        return DEFAULT_STYLE;
      }}
      onEachFeature={(feature: Feature, layer: Layer) => {
        const name = displayMunicipality(feature.properties?.adm3_en);
        layer.bindTooltip(name, { permanent: true, direction: 'center', className: 'ppalma-label' });

        const count = incidentCounts[name];
        layer.bindPopup(
          `<div style="font-size:12px"><b>${name}</b><br/>${
            count !== undefined ? `${count} recorded incidents` : 'No data yet'
          }</div>`,
          { closeButton: false, autoPan: false }
        );

        const pathLayer = layer as LeafletGeoJSON;
        if ('getBounds' in pathLayer && typeof (pathLayer as unknown as { getBounds: () => LatLngBounds }).getBounds === 'function') {
          onMunicipalityBoundsReady?.(name, (pathLayer as unknown as { getBounds: () => LatLngBounds }).getBounds());
        }

        layer.on({
          mouseover: (e: LeafletMouseEvent) => {
            if (name !== activeMunicipality) (e.target as LeafletGeoJSON).setStyle(HOVER_STYLE);
            layer.openPopup(e.latlng);
          },
          mouseout: (e: LeafletMouseEvent) => {
            if (name !== activeMunicipality) {
              (e.target as LeafletGeoJSON).setStyle(activeMunicipality ? DIMMED_STYLE : DEFAULT_STYLE);
            }
            layer.closePopup();
          },
          click: (e: LeafletMouseEvent) => {
            onMunicipalityClick(name);
            const bounds = (e.target as unknown as { getBounds: () => LatLngBounds }).getBounds();
            if (bounds.isValid()) map.fitBounds(bounds, { padding: [40, 40] });
          },
        });
      }}
    />
  );
}
