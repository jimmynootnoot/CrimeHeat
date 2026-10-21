import { useState } from 'react';
import { downloadCsvReport, openHtmlReport } from '../api/endpoints';
import { CRIME_TYPES, PPALMA_MUNICIPALITIES } from '../types';
import { EvaluationExport } from '../components/EvaluationExport';
import { TemporalSplitEvaluation } from '../components/TemporalSplitEvaluation';
import { useAuth } from '../context/AuthContext';

export function ReportsPage() {
  const { canAnalyze } = useAuth();
  const [municipality, setMunicipality] = useState('');
  const [crimeType, setCrimeType] = useState('');
  const [year, setYear] = useState('');

  const filters = {
    municipality: municipality || undefined,
    crime_type: crimeType || undefined,
    year: year ? Number(year) : undefined,
  };

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-50 max-w-2xl mx-auto space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Reports</h1>
        <p className="text-sm text-slate-500">
          Export the currently filtered record set from the official PNP dataset.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow border border-slate-200 p-4 space-y-3">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Municipality</label>
          <select
            value={municipality}
            onChange={(e) => setMunicipality(e.target.value)}
            className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm"
          >
            <option value="">All municipalities</option>
            {PPALMA_MUNICIPALITIES.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Crime type</label>
          <select
            value={crimeType}
            onChange={(e) => setCrimeType(e.target.value)}
            className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm"
          >
            <option value="">All crime types</option>
            {CRIME_TYPES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Year</label>
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            placeholder="e.g. 2024"
            className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm"
          />
        </div>

        <div className="flex gap-3 pt-2">
          <button
            onClick={() => downloadCsvReport(filters)}
            className="bg-slate-900 text-white rounded px-4 py-2 text-sm font-semibold"
          >
            Download CSV
          </button>
          <button
            onClick={() => openHtmlReport(filters)}
            className="border border-slate-300 rounded px-4 py-2 text-sm font-semibold"
          >
            Open printable summary
          </button>
        </div>
      </div>
      {canAnalyze ? (
        <>
          <EvaluationExport />
          <TemporalSplitEvaluation />
        </>
      ) : (
        <div className="rounded-lg border border-sky-200 bg-sky-50 p-4">
          <h2 className="font-semibold text-sky-950">Evaluation tools are read-only for viewers</h2>
          <p className="mt-1 text-sm text-sky-800">
            You can download incident reports above. Running a new evaluation or changing analytical parameters requires an analyst or administrator account.
          </p>
        </div>
      )}
    </div>
  );
}
