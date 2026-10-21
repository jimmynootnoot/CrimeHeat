import { useState } from 'react';
import { apiClient } from '../api/client';
import axios from 'axios';

export function EvaluationExport() {
  const [files, setFiles] = useState<Record<string, File | undefined>>({});
  const [source, setSource] = useState('expert_validated');
  const [validator, setValidator] = useState('');
  const [scope, setScope] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const inputs = [
    ['predictions_csv', 'System predictions', 'unit_id,predicted_label'],
    ['reference_csv', 'Reference classification', 'unit_id,reference_label'],
    ['functional_tests_csv', 'Functional test outcomes', 'case_code,status'],
  ];

  async function download() {
    setBusy(true);
    setError('');
    try {
      const contents = Object.fromEntries(await Promise.all(inputs.map(async ([key]) => [key, await files[key]!.text()])));
      const response = await apiClient.post('/api/reports/evaluation', {
        ...contents, reference_source: source, validated_by: validator, scope,
      }, { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'ppalma_evaluation_report.xlsx';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      let message = 'Could not export evaluation. Check the files and try again.';
      if (axios.isAxiosError(err) && err.response?.data instanceof Blob) {
        try {
          const body = JSON.parse(await err.response.data.text());
          if (typeof body.detail === 'string') message = body.detail;
        } catch { /* Keep the readable fallback for non-JSON errors. */ }
      }
      setError(message);
    } finally { setBusy(false); }
  }

  return (
    <section className="bg-white rounded-lg shadow border border-slate-200 p-4 space-y-3">
      <h2 className="font-semibold text-slate-900">Evaluation export (90% / 10%)</h2>
      <p className="text-sm text-slate-600">
        Algorithmic score = F1-Score against the reference. Precision and Recall are reported as supporting metrics.
        Overall effectiveness = 90% algorithmic score + 10% functional pass rate.
        Pass rate includes all supplied test cases; blocked and not-run cases do not count as passed.
      </p>
      <p className="text-sm text-slate-600">
        Upload CSV files with the headers below. Use 1 for hotspot and 0 for non-hotspot.
        Prediction and reference files must have identical, unique unit IDs covering the complete
        evaluation population. Test statuses: passed, failed, blocked, not_run.
        These files define the evaluation scope independently of the incident filters above.
      </p>
      {inputs.map(([key, label, headers]) => (
        <label key={key} className="block text-sm text-slate-700">
          {label} <span className="text-xs text-slate-500">({headers})</span>
          <input type="file" accept=".csv,text/csv" disabled={busy}
            onChange={e => { setFiles(previous => ({ ...previous, [key]: e.target.files?.[0] })); setConfirmed(false); }}
            className="block w-full mt-1 border rounded p-2 text-sm" />
        </label>
      ))}
      <label className="block text-sm">Reference source
        <select value={source} onChange={e => { setSource(e.target.value); setConfirmed(false); }} className="block w-full border rounded p-2">
          <option value="expert_validated">Expert validated</option>
          <option value="authorized_pnp">Authorized PNP</option>
          <option value="synthetic_demo">Synthetic demonstration only</option>
        </select>
      </label>
      <label className="block text-sm">Reference validator and evidence/source identifier
        <input value={validator} onChange={e => { setValidator(e.target.value); setConfirmed(false); }} maxLength={500} className="block w-full border rounded p-2" />
      </label>
      <label className="block text-sm">Evaluation scope (dataset/run, period, area, and unit definition)
        <textarea value={scope} onChange={e => { setScope(e.target.value); setConfirmed(false); }} maxLength={1000} className="block w-full border rounded p-2" />
      </label>
      <label className="flex gap-2 text-sm">
        <input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />
        I confirm these predictions and references cover the same complete population, the reference
        source is accurate, and all planned functional test cases are included.
      </label>
      <p className="text-xs text-slate-500">The Excel workbook includes a presentation-ready summary, confusion matrix,
        weighted score, provenance, and separate classification and functional-test evidence sheets. Undefined ratios use 0.
        Reference validation is supplied by the evaluator, not independently certified by the system.</p>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <button onClick={download} disabled={busy || !confirmed || !validator.trim() || !scope.trim() || inputs.some(([key]) => !files[key])}
        className="bg-slate-900 text-white rounded px-4 py-2 text-sm font-semibold disabled:opacity-50">
        {busy ? 'Exporting…' : 'Download evaluation workbook'}
      </button>
    </section>
  );
}
