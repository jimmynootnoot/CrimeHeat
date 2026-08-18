import { apiClient } from './client';
import type {
  AnalysisMetadata,
  Incident,
  IncidentFilters,
  MunicipalityStats,
} from '../types';
import type { FeatureCollection } from 'geojson';

export type MetaFeatureCollection = FeatureCollection & { metadata?: AnalysisMetadata };

export async function fetchMunicipalityBoundaries(): Promise<FeatureCollection> {
  const res = await fetch('/data/ppalma_municipalities.geojson');
  return res.json();
}

export async function fetchMunicipalityStats(municipalityName: string): Promise<MunicipalityStats> {
  const res = await apiClient.get(`/api/municipalities/${encodeURIComponent(municipalityName)}/stats`);
  return res.data;
}

export async function fetchBarangays(municipality: string): Promise<string[]> {
  const res = await apiClient.get('/api/incidents/barangays', { params: { municipality } });
  return res.data;
}

export async function fetchIncidents(
  filters: IncidentFilters,
  signal?: AbortSignal
): Promise<{ items: Incident[]; total: number }> {
  const res = await apiClient.get('/api/incidents', { params: filters, signal });
  return res.data;
}

export interface ClusterQuery {
  year?: number;
  crime_type?: string;
  municipality?: string;
  eps_km?: number;
  min_samples?: number;
}

export async function fetchClusters(
  query: ClusterQuery,
  signal?: AbortSignal
): Promise<MetaFeatureCollection> {
  const res = await apiClient.get('/api/clusters', { params: query, signal });
  return res.data;
}

export interface PersistenceQuery {
  municipality?: string;
  barangay?: string;
  crime_type?: string;
  category?: string;
}

export async function fetchPersistence(
  query: PersistenceQuery,
  signal?: AbortSignal
): Promise<MetaFeatureCollection> {
  const res = await apiClient.get('/api/persistence', { params: query, signal });
  return res.data;
}

export async function fetchYearsAvailable(): Promise<number[]> {
  const res = await apiClient.get('/api/incidents/years');
  return res.data;
}

export async function deleteIncident(id: number): Promise<void> {
  await apiClient.delete(`/api/incidents/${id}`);
}

export interface DashboardSummary {
  total_incidents: number;
  synthetic_incidents: number;
  pnp_incidents: number;
  crime_type_breakdown: Record<string, number>;
  municipality_breakdown: Record<string, number>;
  year_breakdown: Record<string, number>;
  municipality_count: number;
  distinct_year_count: number;
  persistence_category_breakdown: Record<string, number>;
  active_persistent_hotspots: number;
  noise_ratio: number | null;
  latest_analysis_at: string | null;
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const res = await apiClient.get('/api/dashboard/summary');
  return res.data;
}

export interface UploadPreview {
  batch_id: number;
  columns: string[];
  sample_rows: Record<string, unknown>[];
  suggested_mapping: Record<string, string>;
  row_count: number;
}

const TARGET_FIELDS = [
  'incident_id',
  'crime_type',
  'incident_date',
  'incident_time',
  'municipality',
  'barangay',
  'general_location',
  'latitude',
  'longitude',
] as const;

export type TargetField = (typeof TARGET_FIELDS)[number];
export { TARGET_FIELDS };

export async function uploadPreview(file: File): Promise<UploadPreview> {
  const form = new FormData();
  form.append('file', file);
  const res = await apiClient.post('/api/upload/preview', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export interface ValidationError {
  row: number;
  field: string;
  message: string;
}

export interface ValidationResult {
  valid_count: number;
  error_count: number;
  errors: ValidationError[];
}

export async function validateUpload(
  batchId: number,
  mapping: Record<string, string>
): Promise<ValidationResult> {
  const res = await apiClient.post(`/api/upload/${batchId}/validate`, { mapping });
  return res.data;
}

export async function commitUpload(
  batchId: number,
  mapping: Record<string, string>
): Promise<{ imported_count: number }> {
  const res = await apiClient.post(`/api/upload/${batchId}/commit`, { mapping });
  return res.data;
}

export function downloadErrorsCsv(errors: ValidationError[], filename = 'upload_errors.csv') {
  const header = 'row,field,message\n';
  const body = errors
    .map((e) => `${e.row},"${e.field}","${e.message.replace(/"/g, '""')}"`)
    .join('\n');
  const blob = new Blob([header + body], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadCsvReport(filters: IncidentFilters): Promise<void> {
  const res = await apiClient.get('/api/reports', {
    params: { ...filters, format: 'csv' },
    responseType: 'blob',
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'ppalma_incident_report.csv';
  a.click();
  URL.revokeObjectURL(url);
}

export async function openHtmlReport(filters: IncidentFilters): Promise<void> {
  const res = await apiClient.get('/api/reports', {
    params: { ...filters, format: 'html' },
    responseType: 'text',
  });
  const blob = new Blob([res.data as unknown as string], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank');
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}
