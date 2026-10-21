import { useEffect, useMemo, useState } from 'react';
import { deleteIncident, fetchIncidents } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { CRIME_TYPES, PPALMA_MUNICIPALITIES, type Incident, type IncidentFilters } from '../types';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { SkeletonTableRows } from '../components/ui/Skeleton';
import { formatIncidentDate } from '../utils/incidentDate';

const PAGE_SIZE = 25;

type SortKey = 'incident_date' | 'crime_type' | 'municipality' | 'barangay';

export function RecordsPage() {
  const { isAdmin } = useAuth();
  const [items, setItems] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<IncidentFilters>({});
  const [searchText, setSearchText] = useState('');
  const debouncedSearch = useDebouncedValue(searchText, 300);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>('incident_date');
  const [sortAsc, setSortAsc] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);

  function load() {
    setLoading(true);
    setError(false);
    fetchIncidents({ ...filters, q: debouncedSearch || undefined, page, page_size: PAGE_SIZE })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, filters, debouncedSearch]);

  const sortedItems = useMemo(() => {
    const copy = [...items];
    copy.sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      const cmp = String(av).localeCompare(String(bv));
      return sortAsc ? cmp : -cmp;
    });
    return copy;
  }, [items, sortKey, sortAsc]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortAsc((a) => !a);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  }

  async function confirmDelete() {
    if (pendingDeleteId === null) return;
    await deleteIncident(pendingDeleteId);
    setPendingDeleteId(null);
    load();
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function sortIndicator(key: SortKey) {
    if (key !== sortKey) return null;
    return <span className="ml-1 text-slate-400">{sortAsc ? '▲' : '▼'}</span>;
  }

  return (
    <div className="h-full space-y-4 overflow-y-auto bg-slate-50 p-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Crime Records</h1>
        <p className="text-sm text-slate-500">
          {total} records. Victim and suspect identities are never stored or displayed.
        </p>
        {items.some((i) => i.date_precision === 'year_only') && (
          <p className="mt-1 text-xs text-slate-500">
            Rows marked <span className="rounded bg-slate-100 px-1 font-medium">year only</span>{' '}
            came from a source that supplied the year but no incident date. They are counted in
            year-based analysis; their day and month are unknown.
          </p>
        )}
      </div>

      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search incident ID, barangay, location…"
          value={searchText}
          onChange={(e) => {
            setPage(1);
            setSearchText(e.target.value);
          }}
          className="min-w-[16rem] rounded border border-slate-300 px-3 py-1.5 text-sm"
        />
        <select
          className="rounded border border-slate-300 px-2 py-1.5 text-sm"
          value={filters.municipality ?? ''}
          onChange={(e) => {
            setPage(1);
            setFilters((f) => ({ ...f, municipality: e.target.value || undefined }));
          }}
        >
          <option value="">All municipalities</option>
          {PPALMA_MUNICIPALITIES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <select
          className="rounded border border-slate-300 px-2 py-1.5 text-sm"
          value={filters.crime_type ?? ''}
          onChange={(e) => {
            setPage(1);
            setFilters((f) => ({ ...f, crime_type: e.target.value || undefined }));
          }}
        >
          <option value="">All crime types</option>
          {CRIME_TYPES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <ErrorState message="Could not load records." onRetry={load} />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead className="sticky top-0 z-10 bg-slate-100 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2">Incident ID</th>
                <th
                  className="cursor-pointer select-none px-3 py-2"
                  onClick={() => toggleSort('crime_type')}
                >
                  Crime type{sortIndicator('crime_type')}
                </th>
                <th
                  className="cursor-pointer select-none px-3 py-2"
                  onClick={() => toggleSort('incident_date')}
                >
                  Date{sortIndicator('incident_date')}
                </th>
                <th
                  className="cursor-pointer select-none px-3 py-2"
                  onClick={() => toggleSort('municipality')}
                >
                  Municipality{sortIndicator('municipality')}
                </th>
                <th
                  className="cursor-pointer select-none px-3 py-2"
                  onClick={() => toggleSort('barangay')}
                >
                  Barangay{sortIndicator('barangay')}
                </th>
                <th className="px-3 py-2">Source</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {loading && <SkeletonTableRows rows={8} cols={7} />}
              {!loading &&
                sortedItems.map((i) => (
                  <tr key={i.id} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-mono text-xs">{i.incident_id}</td>
                    <td className="px-3 py-2">{i.crime_type}</td>
                    <td className="px-3 py-2">
                      {(() => {
                        const shown = formatIncidentDate(i);
                        return (
                          <span title={shown.title} className={shown.approximate ? 'text-slate-500' : undefined}>
                            {shown.label}
                            {shown.approximate && (
                              <span className="ml-1 rounded bg-slate-100 px-1 text-[10px] font-medium text-slate-600">
                                year only
                              </span>
                            )}
                          </span>
                        );
                      })()}
                    </td>
                    <td className="px-3 py-2">{i.municipality}</td>
                    <td className="px-3 py-2">{i.barangay}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          i.source === 'official'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {i.source}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      {isAdmin && (
                        <button
                          onClick={() => setPendingDeleteId(i.id)}
                          className="text-xs text-red-600 hover:underline"
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          {!loading && sortedItems.length === 0 && (
            <EmptyState title="No records match" description="Try adjusting the search or filters." />
          )}
        </div>
      )}

      <div className="flex items-center justify-between text-sm text-slate-600">
        <span>
          Page {page} of {totalPages}
        </span>
        <div className="flex gap-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40"
          >
            Previous
          </button>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>

      <ConfirmDialog
        open={pendingDeleteId !== null}
        title="Delete this incident record?"
        description="This permanently removes the record. This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={confirmDelete}
        onCancel={() => setPendingDeleteId(null)}
      />
    </div>
  );
}
