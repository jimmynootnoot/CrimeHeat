import type { MunicipalityStats } from '../../types';
import { DetailDrawer } from './DetailDrawer';
import { Skeleton } from '../ui/Skeleton';
import { EmptyState } from '../ui/EmptyState';

export function MunicipalitySidePanel({
  name,
  stats,
  loading,
  onClose,
}: {
  name: string;
  stats: MunicipalityStats | null;
  loading: boolean;
  onClose: () => void;
}) {
  return (
    <DetailDrawer title={name} subtitle="Municipality overview · all years and crime types" onClose={onClose}>
      {loading && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
          <Skeleton className="h-24" />
        </div>
      )}

      {!loading && stats && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded bg-slate-50 p-3">
              <div className="text-2xl font-bold text-slate-900">{stats.total_incidents}</div>
              <div className="text-xs text-slate-500">Total recorded incidents</div>
            </div>
            <div className="rounded bg-slate-50 p-3">
              <div className="text-2xl font-bold text-slate-900">
                {stats.active_persistent_clusters}
              </div>
              <div className="text-xs text-slate-500">Active persistent hotspots</div>
            </div>
          </div>

          <div>
            <h3 className="mb-2 font-semibold text-slate-800">Incidents by crime type</h3>
            <ul className="space-y-1">
              {Object.entries(stats.incidents_by_crime_type).map(([type, count]) => (
                <li key={type} className="flex justify-between text-slate-600">
                  <span>{type}</span>
                  <span className="font-medium text-slate-900">{count}</span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="mb-2 font-semibold text-slate-800">Incidents by year</h3>
            <ul className="space-y-1">
              {Object.entries(stats.incidents_by_year).map(([year, count]) => (
                <li key={year} className="flex justify-between text-slate-600">
                  <span>{year}</span>
                  <span className="font-medium text-slate-900">{count}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      {!loading && !stats && (
        <EmptyState title="No statistics available" description="This municipality has no recorded incidents yet." />
      )}
    </DetailDrawer>
  );
}
