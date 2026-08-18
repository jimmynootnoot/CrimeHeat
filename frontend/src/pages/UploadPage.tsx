import { useState, useRef, type ChangeEvent, type DragEvent } from 'react';
import { ColumnMappingForm } from '../components/upload/ColumnMappingForm';
import { useAuth } from '../context/AuthContext';
import {
  commitUpload,
  downloadErrorsCsv,
  uploadPreview,
  validateUpload,
  type UploadPreview,
  type ValidationResult,
} from '../api/endpoints';

type Step = 'select' | 'map' | 'validated' | 'done';

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
  const { isAdmin, user } = useAuth();
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
    } catch {
      setError('Could not read this file. Confirm it is a valid CSV or Excel export.');
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
    } catch {
      setError('Validation failed. Check the column mapping and try again.');
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
    } catch {
      setError('Import failed. No rows were committed.');
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
          Reusable CSV/Excel import — this same flow will be used to load the official PNP
          dataset once it is released.
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
              {validation.valid_count} valid rows, {validation.error_count} rows with errors.
            </p>
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
                        <td className="py-1 text-red-600">{err.message}</td>
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

          {!isAdmin && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
              Importing requires an admin role. Your account ({user?.role ?? 'analyst'}) can
              validate files but cannot commit an import.
            </p>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleCommit}
              disabled={busy || validation.valid_count === 0 || !isAdmin}
              title={!isAdmin ? 'Requires an admin role' : undefined}
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
