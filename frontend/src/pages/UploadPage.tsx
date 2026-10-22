import { useState, useRef, type ChangeEvent, type DragEvent } from 'react';
import axios from 'axios';
import { ColumnMappingForm } from '../components/upload/ColumnMappingForm';
import {
  commitUpload,
  downloadErrorsCsv,
  uploadPreview,
  validateUpload,
  type UploadPreview,
  type ValidationResult,
} from '../api/endpoints';

type Step = 'select' | 'map' | 'validated' | 'done';

/** Prefer the API's own explanation — it names what actually failed. */
function serverMessage(err: unknown, fallback: string): string {
  const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined;
  return typeof detail === 'string' && detail ? detail : fallback;
}

const STEP_ORDER: Step[] = ['select', 'map', 'validated', 'done'];
const STEP_LABELS: { step: Step; label: string }[] = [
  { step: 'select', label: 'Select File' },
  { step: 'map', label: 'Map Columns' },
  { step: 'validated', label: 'Validate' },
  { step: 'validated', label: 'Review' },
  { step: 'done', label: 'Import' },
];

function StepIndicator({ step }: { step: Step }) {
  const currentIndex = STEP_ORDER.indexOf(step);
  return (
    <ol className="flex flex-wrap items-center gap-2 text-sm">
      {STEP_LABELS.map((s, i) => {
        const stepIndex = STEP_ORDER.indexOf(s.step);
        const isReviewLabel = s.label === 'Review';
        const done = stepIndex < currentIndex || (isReviewLabel && step === 'done');
        const active = !done && (stepIndex === currentIndex || (isReviewLabel && step === 'validated'));
        return (
          <li key={s.label} className="flex items-center gap-2">
            {i > 0 && <span className="text-slate-300">&rarr;</span>}
            <span
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 font-medium ${
                active
                  ? 'bg-slate-900 text-white'
                  : done
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-slate-100 text-slate-500'
              }`}
            >
              <span className="flex h-4 w-4 items-center justify-center rounded-full bg-white/20 text-[10px]">
                {i + 1}
              </span>
              {s.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function UploadPage() {
  const [step, setStep] = useState<Step>('select');
  const [fileName, setFileName] = useState<string | null>(null);
  const [preview, setPreview] = useState<UploadPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [importedCount, setImportedCount] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function loadFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      setFileName(file.name);
      const result = await uploadPreview(file);
      setPreview(result);
      setMapping(result.suggested_mapping);
      setStep('map');
    } catch (err) {
      setError(serverMessage(err, 'Could not read this file. Confirm it is a valid CSV or Excel export.'));
    } finally {
      setBusy(false);
    }
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) loadFile(file);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) loadFile(file);
  }

  async function handleValidate() {
    if (!preview) return;
    setBusy(true);
    setError(null);
    try {
      const result = await validateUpload(preview.batch_id, mapping);
      setValidation(result);
      setStep('validated');
    } catch (err) {
      setError(serverMessage(err, 'Validation failed. Check the column mapping and try again.'));
    } finally {
      setBusy(false);
    }
  }

  async function handleCommit() {
    if (!preview) return;
    setBusy(true);
    setError(null);
    try {
      const result = await commitUpload(preview.batch_id, mapping);
      setImportedCount(result.imported_count);
      setStep('done');
    } catch (err) {
      setError(serverMessage(err, 'Import failed. No rows were committed.'));
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setStep('select');
    setFileName(null);
    setPreview(null);
    setMapping({});
    setValidation(null);
    setImportedCount(0);
    setError(null);
  }

  return (
    <div className="mx-auto h-full max-w-3xl space-y-6 overflow-y-auto bg-slate-50 p-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Import Crime Records</h1>
        <p className="text-sm text-slate-500">
          Upload the PNP export as you received it — the importer standardizes barangay and
          crime-type spellings, fills gaps, and lists every correction before anything is saved.
        </p>
      </div>

      <StepIndicator step={step} />

      {error && (
        <p className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-600">{error}</p>
      )}

      {step === 'select' && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
            dragActive
              ? 'border-slate-500 bg-slate-100'
              : 'border-slate-300 bg-white hover:border-slate-400'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileChange}
            disabled={busy}
            className="hidden"
          />
          <p className="text-sm font-medium text-slate-700">
            {busy ? 'Reading file…' : 'Drag & drop a CSV or Excel file here, or click to browse'}
          </p>
          <p className="mt-2 text-xs text-slate-400">Accepted formats: .csv, .xlsx, .xls</p>
        </div>
      )}

      {step === 'map' && preview && (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            <span className="font-medium">{fileName}</span> — {preview.row_count} rows detected.
            Review the suggested mapping below.
          </p>
          {preview.notes?.length > 0 && (
            <ul className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-2 text-sm text-sky-900">
              {preview.notes.map((note, idx) => (
                <li key={idx}>{note}</li>
              ))}
            </ul>
          )}
          <ColumnMappingForm
            sourceColumns={preview.columns}
            mapping={mapping}
            onChange={setMapping}
          />
          <div className="flex gap-3">
            <button
              onClick={handleValidate}
              disabled={busy}
              className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {busy ? 'Validating…' : 'Validate mapping'}
            </button>
            <button
              onClick={reset}
              className="rounded border border-slate-300 px-4 py-2 text-sm font-semibold"
            >
              Back
            </button>
          </div>
        </div>
      )}

      {step === 'validated' && validation && (
        <div className="space-y-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Validation report</h2>
              {validation.errors.length > 0 && (
                <button
                  onClick={() => downloadErrorsCsv(validation.errors)}
                  className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                >
                  Download error report (CSV)
                </button>
              )}
            </div>
            <p className="text-sm text-slate-600">
              <span className="font-semibold text-emerald-700">
                {validation.valid_count.toLocaleString()} rows will import
              </span>
              {' — '}
              {validation.warning_count.toLocaleString()} with advisories,{' '}
              {validation.error_count.toLocaleString()} rejected.
            </p>
            {Object.keys(validation.rejected_by_field ?? {}).length > 0 && (
              <p className="mt-1 text-xs text-slate-500">
                Rejected by reason:{' '}
                {Object.entries(validation.rejected_by_field)
                  .map(([field, count]) => `${field} ${count.toLocaleString()}`)
                  .join(' · ')}
                . Records outside the six PPALMA municipalities, and offences outside the eight
                index crimes, are excluded by design.
              </p>
            )}
            {validation.errors.length > 0 && (
              <div className="mt-3 max-h-80 overflow-y-auto">
                <table className="min-w-full text-xs">
                  <thead className="sticky top-0 bg-white text-left text-slate-500">
                    <tr>
                      <th className="py-1 pr-4">Row</th>
                      <th className="py-1 pr-4">Field</th>
                      <th className="py-1">Issue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {validation.errors.slice(0, 50).map((err, idx) => (
                      <tr key={idx} className="border-t border-slate-100">
                        <td className="py-1 pr-4">{err.row}</td>
                        <td className="py-1 pr-4 font-mono">{err.field}</td>
                        <td
                          className={`py-1 ${
                            err.severity === 'warning' ? 'text-amber-700' : 'text-red-600'
                          }`}
                        >
                          {err.message}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {validation.errors.length > 50 && (
                  <p className="mt-2 text-xs text-slate-400">
                    Showing first 50 of {validation.errors.length} errors — download the CSV for
                    the full list.
                  </p>
                )}
              </div>
            )}
          </div>

          {validation.standardizations.length > 0 && (
            <div className="rounded-lg border border-slate-200 bg-white p-4 shadow">
              <h2 className="font-semibold text-slate-800">
                Organized for you ({validation.standardizations.length} corrections)
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                The importer standardized these values so the file did not have to be cleaned by
                hand. Every change is listed rather than applied silently.
              </p>
              <div className="mt-3 max-h-80 overflow-y-auto">
                <table className="min-w-full text-xs">
                  <thead className="sticky top-0 bg-white text-left text-slate-500">
                    <tr>
                      <th className="py-1 pr-4">Row</th>
                      <th className="py-1 pr-4">Field</th>
                      <th className="py-1 pr-4">From</th>
                      <th className="py-1">To</th>
                    </tr>
                  </thead>
                  <tbody>
                    {validation.standardizations.slice(0, 50).map((fix, idx) => (
                      <tr key={idx} className="border-t border-slate-100">
                        <td className="py-1 pr-4">{fix.row}</td>
                        <td className="py-1 pr-4 font-mono">{fix.field}</td>
                        <td className="py-1 pr-4 text-slate-500 line-through">{fix.from}</td>
                        <td className="py-1 font-medium text-emerald-700">{fix.to}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {validation.standardizations.length > 50 && (
                  <p className="mt-2 text-xs text-slate-400">
                    Showing first 50 of {validation.standardizations.length} corrections.
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleCommit}
              disabled={busy || validation.valid_count === 0}
              className="rounded bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {busy ? 'Importing…' : `Import ${validation.valid_count} valid rows`}
            </button>
            <button
              onClick={() => setStep('map')}
              className="rounded border border-slate-300 px-4 py-2 text-sm font-semibold"
            >
              Back to mapping
            </button>
          </div>
        </div>
      )}

      {step === 'done' && (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-6 text-center shadow">
          <p className="font-semibold text-emerald-700">
            Imported {importedCount} records successfully.
          </p>
          <button
            onClick={reset}
            className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
          >
            Import another file
          </button>
        </div>
      )}
    </div>
  );
}
