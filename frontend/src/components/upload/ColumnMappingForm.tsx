import { TARGET_FIELDS } from '../../api/endpoints';

const REQUIRED_FIELDS = new Set([
  'incident_id',
  'crime_type',
  'incident_date',
  'municipality',
  'barangay',
  'latitude',
  'longitude',
]);

export function ColumnMappingForm({
  sourceColumns,
  mapping,
  onChange,
}: {
  sourceColumns: string[];
  mapping: Record<string, string>;
  onChange: (mapping: Record<string, string>) => void;
}) {
  function setMapping(targetField: string, sourceColumn: string) {
    onChange({ ...mapping, [targetField]: sourceColumn });
  }

  return (
    <div className="bg-white rounded-lg shadow border border-slate-200 p-4">
      <h2 className="font-semibold text-slate-800 mb-3">Map columns to the incident schema</h2>
      <div className="grid grid-cols-2 gap-3">
        {TARGET_FIELDS.map((field) => (
          <div key={field} className="flex items-center justify-between gap-2">
            <label className="text-sm text-slate-600 font-mono">
              {field}
              {REQUIRED_FIELDS.has(field) && <span className="text-red-500"> *</span>}
            </label>
            <select
              value={mapping[field] ?? ''}
              onChange={(e) => setMapping(field, e.target.value)}
              className="border border-slate-300 rounded px-2 py-1 text-sm w-48"
            >
              <option value="">— not mapped —</option>
              {sourceColumns.map((col) => (
                <option key={col} value={col}>{col}</option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </div>
  );
}
