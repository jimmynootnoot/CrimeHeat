import { useEffect, useState, type ReactNode } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  LabelList,
  Pie,
  PieChart,
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

const integerFormatter = new Intl.NumberFormat('en-US');
const compactFormatter = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

const tooltipStyle = {
  backgroundColor: '#0f172a',
  border: 'none',
  borderRadius: 10,
  boxShadow: '0 10px 30px rgb(15 23 42 / 0.18)',
  color: '#f8fafc',
  fontSize: 12,
  padding: '10px 12px',
};

function StatCard({
  label,
  value,
  info,
  accent = 'bg-slate-900',
}: {
  label: string;
  value: number | string;
  info?: string;
  accent?: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className={`absolute inset-y-0 left-0 w-1 ${accent}`} aria-hidden="true" />
      <div className="pl-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
        {typeof value === 'number' ? integerFormatter.format(value) : value}
      </div>
      <div className="mt-1 pl-1 text-sm font-medium text-slate-500">
        {label}
        {info && <InfoIcon text={info} />}
      </div>
    </div>
  );
}

function ChartCard({
  title,
  subtitle,
  badge,
  children,
}: {
  title: string;
  subtitle: string;
  badge?: string;
  children: ReactNode;
}) {
  return (
    <section className="min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="font-semibold text-slate-900">{title}</h2>
          <p className="mt-0.5 text-xs leading-5 text-slate-500">{subtitle}</p>
        </div>
        {badge && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold tabular-nums text-slate-600">
            {badge}
          </span>
        )}
      </div>
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  );
}

function toChartData(record: Record<string, number>) {
  return Object.entries(record).map(([name, value]) => ({ name, value }));
}

type ChartDatum = ReturnType<typeof toChartData>[number];

function totalOf(data: ChartDatum[]) {
  return data.reduce((total, item) => total + item.value, 0);
}

function EmptyChart() {
  return (
    <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50/70 text-center">
      <div className="mb-2 h-8 w-8 rounded-full border-4 border-slate-200 border-t-slate-400" />
      <p className="text-sm font-medium text-slate-600">No chart data available</p>
      <p className="mt-1 text-xs text-slate-400">Import records to populate this view.</p>
    </div>
  );
}

function RankedBarChart({
  data,
  color,
  metric,
}: {
  data: ChartDatum[];
  color: string;
  metric: string;
}) {
  if (data.length === 0) return <EmptyChart />;

  return (
    <ResponsiveContainer width="100%" height={Math.max(280, data.length * 42)}>
      <BarChart
        accessibilityLayer
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 54, bottom: 4, left: 4 }}
        barCategoryGap="28%"
      >
        <CartesianGrid stroke="#e2e8f0" strokeDasharray="2 4" horizontal={false} />
        <XAxis
          type="number"
          allowDecimals={false}
          axisLine={false}
          tickLine={false}
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          tickFormatter={(value) => compactFormatter.format(Number(value))}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={132}
          axisLine={false}
          tickLine={false}
          tick={{ fill: '#475569', fontSize: 11, fontWeight: 500 }}
        />
        <Tooltip
          cursor={{ fill: '#f1f5f9' }}
          contentStyle={tooltipStyle}
          labelStyle={{ color: '#cbd5e1', marginBottom: 4 }}
          itemStyle={{ color: '#f8fafc' }}
          formatter={(value) => [integerFormatter.format(Number(value)), metric]}
        />
        <Bar dataKey="value" name={metric} fill={color} radius={[0, 6, 6, 0]} maxBarSize={24}>
          <LabelList
            dataKey="value"
            position="right"
            fill="#475569"
            fontSize={11}
            fontWeight={600}
            formatter={(value) => compactFormatter.format(Number(value ?? 0))}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

const persistenceOrder = [
  'active_persistent',
  'historical_persistent',
  'intermittent',
  'temporary',
];

const persistenceColors: Record<string, string> = {
  'Active persistent': '#0f766e',
  'Historical persistent': '#2563eb',
  Intermittent: '#d97706',
  Temporary: '#94a3b8',
};

function PersistenceDonut({ data }: { data: ChartDatum[] }) {
  if (data.length === 0) return <EmptyChart />;
  const total = totalOf(data);

  return (
    <div className="grid items-center gap-4 md:grid-cols-[minmax(0,1.35fr)_minmax(12rem,0.65fr)]">
      <div className="relative h-72 min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart accessibilityLayer>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={68}
              outerRadius={102}
              paddingAngle={3}
              cornerRadius={5}
              stroke="#ffffff"
              strokeWidth={2}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={persistenceColors[entry.name] ?? '#7c3aed'} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={tooltipStyle}
              itemStyle={{ color: '#f8fafc' }}
              formatter={(value, _name, item) => {
                const count = Number(value);
                const percentage = total ? Math.round((count / total) * 100) : 0;
                return [`${integerFormatter.format(count)} (${percentage}%)`, item.payload.name];
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold tracking-tight text-slate-900">
            {integerFormatter.format(total)}
          </span>
          <span className="mt-1 text-xs font-medium uppercase tracking-wider text-slate-400">
            Hotspots
          </span>
        </div>
      </div>
      <div className="space-y-3">
        {data.map((entry) => {
          const percentage = total ? Math.round((entry.value / total) * 100) : 0;
          return (
            <div key={entry.name} className="flex items-center justify-between gap-4">
              <div className="flex min-w-0 items-center gap-2.5">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: persistenceColors[entry.name] ?? '#7c3aed' }}
                />
                <span className="truncate text-sm text-slate-600">{entry.name}</span>
              </div>
              <div className="text-right tabular-nums">
                <span className="text-sm font-semibold text-slate-900">{entry.value}</span>
                <span className="ml-1 text-xs text-slate-400">{percentage}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
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

  const crimeTypeChartData = toChartData(summary.crime_type_breakdown).sort(
    (a, b) => b.value - a.value || a.name.localeCompare(b.name),
  );
  const municipalityChartData = toChartData(summary.municipality_breakdown).sort(
    (a, b) => b.value - a.value || a.name.localeCompare(b.name),
  );
  const yearChartData = toChartData(summary.year_breakdown).sort(
    (a, b) => Number(a.name) - Number(b.name),
  );
  const persistenceChartData = toChartData(summary.persistence_category_breakdown)
    .sort((a, b) => {
      const aIndex = persistenceOrder.indexOf(a.name);
      const bIndex = persistenceOrder.indexOf(b.name);
      return (aIndex === -1 ? persistenceOrder.length : aIndex)
        - (bIndex === -1 ? persistenceOrder.length : bIndex);
    })
    .map((item) => ({
      ...item,
      name: PERSISTENCE_CATEGORY_LABELS[item.name as keyof typeof PERSISTENCE_CATEGORY_LABELS]
        ?? item.name,
    }));

  const firstYear = yearChartData.at(0);
  const lastYear = yearChartData.at(-1);
  const yearChange = firstYear && lastYear ? lastYear.value - firstYear.value : null;

  return (
    <div className="h-full overflow-y-auto bg-slate-50">
      <div className="mx-auto max-w-[1600px] space-y-6 p-4 sm:p-6 lg:p-8">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">Operational overview</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Crime analysis dashboard</h1>
            <p className="mt-1 text-sm text-slate-500">
              {integerFormatter.format(summary.official_incidents)} official PNP records across{' '}
              {summary.municipality_count} PPALMA municipalities and {summary.distinct_year_count} analyzed years.
            </p>
          </div>
          {summary.latest_analysis_at && (
            <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-right shadow-sm">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Latest analysis</div>
              <div className="mt-0.5 text-xs font-medium text-slate-700">
                {new Date(summary.latest_analysis_at).toLocaleString()}
              </div>
            </div>
          )}
        </header>

        <section className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <StatCard label="Total incidents" value={summary.total_incidents} accent="bg-blue-600" />
          <StatCard label="Official PNP records" value={summary.official_incidents} accent="bg-teal-600" />
          <StatCard label="Municipalities analyzed" value={summary.municipality_count} accent="bg-indigo-500" />
          <StatCard label="Years analyzed" value={summary.distinct_year_count} accent="bg-violet-500" />
          <StatCard label="Active persistent hotspots" value={summary.active_persistent_hotspots} accent="bg-emerald-600" />
          <StatCard
            label="Noise ratio"
            value={summary.noise_ratio !== null ? `${Math.round(summary.noise_ratio * 100)}%` : '—'}
            info="Share of incidents that DBSCAN could not assign to a cluster using the default parameters."
            accent="bg-slate-500"
          />
        </section>

        <section className="grid items-start gap-5 xl:grid-cols-2">
          <ChartCard
            title="Incidents by crime type"
            subtitle="Ranked from the most to least frequently recorded offense."
            badge={`${integerFormatter.format(totalOf(crimeTypeChartData))} incidents`}
          >
            <RankedBarChart data={crimeTypeChartData} color="#0f766e" metric="Incidents" />
          </ChartCard>

          <ChartCard
            title="Incidents by municipality"
            subtitle="A consistent comparison across the six PPALMA municipalities."
            badge={`${municipalityChartData.length} municipalities`}
          >
            <RankedBarChart data={municipalityChartData} color="#2563eb" metric="Incidents" />
          </ChartCard>
        </section>

        <section className="grid items-start gap-5 xl:grid-cols-2">
          <ChartCard
            title="Incident trend by year"
            subtitle="Annual recorded incidents shown chronologically."
            badge={yearChange === null ? undefined : `${yearChange >= 0 ? '+' : ''}${integerFormatter.format(yearChange)} across range`}
          >
            {yearChartData.length === 0 ? (
              <EmptyChart />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart
                  accessibilityLayer
                  data={yearChartData}
                  margin={{ top: 12, right: 18, bottom: 4, left: 0 }}
                >
                  <defs>
                    <linearGradient id="incidentTrendFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity={0.28} />
                      <stop offset="100%" stopColor="#2563eb" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#e2e8f0" strokeDasharray="2 4" vertical={false} />
                  <XAxis
                    dataKey="name"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }}
                    dy={8}
                  />
                  <YAxis
                    allowDecimals={false}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                    tickFormatter={(value) => compactFormatter.format(Number(value))}
                    width={42}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    labelStyle={{ color: '#cbd5e1', marginBottom: 4 }}
                    itemStyle={{ color: '#f8fafc' }}
                    formatter={(value) => [integerFormatter.format(Number(value)), 'Incidents']}
                    labelFormatter={(label) => `Year ${label}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    name="Incidents"
                    stroke="#2563eb"
                    strokeWidth={3}
                    fill="url(#incidentTrendFill)"
                    dot={{ r: 4, fill: '#ffffff', stroke: '#2563eb', strokeWidth: 2 }}
                    activeDot={{ r: 6, fill: '#2563eb', stroke: '#ffffff', strokeWidth: 3 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          <ChartCard
            title="Hotspot persistence mix"
            subtitle="Composition of detected hotspots by recurrence category."
            badge={`${integerFormatter.format(totalOf(persistenceChartData))} hotspots`}
          >
            <PersistenceDonut data={persistenceChartData} />
          </ChartCard>
        </section>
      </div>
    </div>
  );
}
