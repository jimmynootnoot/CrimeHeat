import { useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fetchDashboardSummary, type DashboardSummary } from '../api/endpoints';
import { PERSISTENCE_CATEGORY_LABELS } from '../types';
import { SkeletonCard } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';
import { InfoIcon } from '../components/ui/Tooltip';

function StatCard({
  label,
  value,
  info,
}: {
  label: string;
  value: number | string;
  info?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-3xl font-bold text-slate-900">{value}</div>
      <div className="text-sm text-slate-500">
        {label}
        {info && <InfoIcon text={info} />}
      </div>
    </div>
  );
}

function toChartData(record: Record<string, number>) {
  return Object.entries(record).map(([name, value]) => ({ name, value }));
}

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState(false);

  function load() {
    setError(false);
    fetchDashboardSummary()
      .then(setSummary)
      .catch(() => setError(true));
  }

  useEffect(load, []);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-50">
        <ErrorState message="Could not load the dashboard summary." onRetry={load} />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="h-full space-y-6 overflow-y-auto bg-slate-50 p-6">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  const persistenceChartData = toChartData(summary.persistence_category_breakdown).map((d) => ({
    ...d,
    name: PERSISTENCE_CATEGORY_LABELS[d.name as keyof typeof PERSISTENCE_CATEGORY_LABELS] ?? d.name,
  }));

  return (
    <div className="h-full space-y-6 overflow-y-auto bg-slate-50 p-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">
          Summary of {summary.official_incidents} official PNP records across{' '}
          {summary.municipality_count} PPALMA municipalities,{' '}
          {summary.distinct_year_count} analyzed years.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Total incidents" value={summary.total_incidents} />
        <StatCard label="Official PNP records" value={summary.official_incidents} />
        <StatCard label="Municipalities analyzed" value={summary.municipality_count} />
        <StatCard label="Years analyzed" value={summary.distinct_year_count} />
        <StatCard label="Active persistent hotspots" value={summary.active_persistent_hotspots} />
        <StatCard
          label="Noise ratio (whole dataset)"
          value={summary.noise_ratio !== null ? `${Math.round(summary.noise_ratio * 100)}%` : '—'}
          info="Share of incidents that DBSCAN could not assign to any cluster (default eps/min-samples, no filters) — a rough density signal, not a quality score."
        />
        <StatCard
          label="Latest analysis"
          value={
            summary.latest_analysis_at
              ? new Date(summary.latest_analysis_at).toLocaleString()
              : '—'
          }
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold text-slate-800">Incidents by crime type</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={toChartData(summary.crime_type_breakdown)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-30} textAnchor="end" height={70} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#1e293b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold text-slate-800">Incidents by municipality</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={toChartData(summary.municipality_breakdown)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold text-slate-800">Incidents by year</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={toChartData(summary.year_breakdown)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#dc2626" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-3 font-semibold text-slate-800">Persistence category breakdown</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={persistenceChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={50} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#7c3aed" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
