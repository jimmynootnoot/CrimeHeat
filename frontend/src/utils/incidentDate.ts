import type { Incident } from '../types';

/**
 * How an incident's date should be shown.
 *
 * Records whose source gave only a year are stored with a placeholder 1
 * January so they can still be filtered and clustered by period. Printing that
 * placeholder as "2024-01-01" would present a value nobody observed, so those
 * rows display as the year alone and carry the reason with them.
 */
export function formatIncidentDate(
  incident: Pick<Incident, 'incident_date' | 'date_precision'>
): { label: string; approximate: boolean; title?: string } {
  if (incident.date_precision === 'year_only') {
    return {
      label: incident.incident_date.slice(0, 4),
      approximate: true,
      title:
        'The source dataset supplied only the year for this record, not a date. ' +
        'Year-based analysis is valid; the day and month are not known.',
    };
  }
  return { label: incident.incident_date, approximate: false };
}
