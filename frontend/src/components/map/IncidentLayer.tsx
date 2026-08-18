import { useEffect, useState } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.markercluster';
import { fetchIncidents } from '../../api/endpoints';
import type { Incident, MapFilterState } from '../../types';

const CRIME_COLORS: Record<string, string> = {
  Theft: '#f59e0b',
  Robbery: '#ef4444',
  'Physical Injury': '#dc2626',
  Homicide: '#7f1d1d',
  Rape: '#be185d',
  'Illegal Drugs': '#7c3aed',
  Carnapping: '#0ea5e9',
  'Estafa/Fraud': '#059669',
  'Malicious Mischief': '#65a30d',
  'Other Crimes': '#64748b',
};

function dotIcon(color: string) {
  return L.divIcon({
    className: '',
    html: `<span style="display:block;width:9px;height:9px;border-radius:50%;background:${color};opacity:0.65;border:1px solid rgba(30,41,59,0.5)"></span>`,
    iconSize: [9, 9],
    iconAnchor: [4.5, 4.5],
  });
}

/** Display-only clustering at low zoom via leaflet.markercluster — this is a
 * rendering aid for readability, NOT a DBSCAN result. */
export function IncidentLayer({
  filters,
  onIncidentsLoaded,
}: {
  filters: MapFilterState;
  onIncidentsLoaded?: (incidents: Incident[]) => void;
}) {
  const map = useMap();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    fetchIncidents(
      {
        municipality: filters.municipality || undefined,
        barangay: filters.barangay || undefined,
        crime_type: filters.crime_type || undefined,
        year: filters.year === 'all' ? undefined : filters.year,
        page_size: 2000,
      },
      controller.signal
    )
      .then((res) => {
        setIncidents(res.items);
        onIncidentsLoaded?.(res.items);
      })
      .catch((err) => {
        if (err.name !== 'CanceledError' && err.name !== 'AbortError') {
          console.error('Failed to load incidents:', err);
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.municipality, filters.barangay, filters.crime_type, filters.year]);

  useEffect(() => {
    if (loading) return;
    const group = L.markerClusterGroup({ maxClusterRadius: 40, disableClusteringAtZoom: 15 });

    incidents.forEach((incident) => {
      const marker = L.marker([incident.latitude, incident.longitude], {
        icon: dotIcon(CRIME_COLORS[incident.crime_type] ?? '#64748b'),
      });
      marker.bindPopup(
        `<div style="font-size:13px"><b>${incident.crime_type}</b><br/>${incident.incident_date} ${
          incident.incident_time ?? ''
        }<br/>${incident.barangay}, ${incident.municipality}<br/>` +
          (incident.general_location ? `<span style="color:#64748b">${incident.general_location}</span><br/>` : '') +
          `<span style="color:#b45309;font-size:11px">Synthetic record — ${incident.incident_id}</span></div>`
      );
      group.addLayer(marker);
    });

    group.addTo(map);
    return () => {
      map.removeLayer(group);
    };
  }, [map, incidents, loading]);

  return null;
}
