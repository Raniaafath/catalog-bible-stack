import axios, { AxiosError, AxiosRequestConfig } from 'axios';

const API_BASE_URL = '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - could redirect to login
      console.error('Unauthorized request');
    }
    return Promise.reject(error);
  }
);

// Pagination types
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
  [key: string]: unknown;
}

// Generic fetch function with pagination
export async function fetchPaginated<T>(
  url: string,
  params?: Record<string, unknown>
): Promise<PaginatedResponse<T>> {
  const response = await apiClient.get<PaginatedResponse<T>>(url, { params });
  return response.data;
}

// Generic fetch single item
export async function fetchOne<T>(url: string): Promise<T> {
  const response = await apiClient.get<T>(url);
  return response.data;
}

// Generic post
export async function postData<T, D = unknown>(url: string, data?: D): Promise<T> {
  const response = await apiClient.post<T>(url, data);
  return response.data;
}

// Generic patch
export async function patchData<T, D = unknown>(url: string, data: D): Promise<T> {
  const response = await apiClient.patch<T>(url, data);
  return response.data;
}

// File upload
export async function uploadFile<T>(
  url: string,
  file: File,
  additionalData?: Record<string, unknown>
): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);
  
  if (additionalData) {
    Object.entries(additionalData).forEach(([key, value]) => {
      formData.append(key, String(value));
    });
  }

  const response = await apiClient.post<T>(url, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
}

// API Types
export interface Locale {
  code: string;
  name: string;
}

export interface ProductType {
  id: number;
  name: string;
  slug: string;
}

export interface Attribute {
  id: number;
  name: string;
  slug: string;
  type: string;
}

export interface Channel {
  id: number;
  name: string;
  code: string;
}

export type ImportStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'awaiting_mapping';

export interface Import {
  id: number;
  filename: string;
  status: ImportStatus;
  row_count: number;
  error_count: number;
  created_at: string;
  updated_at: string;
}

export interface ImportPreview {
  headers: string[];
  rows: Record<string, unknown>[];
  errors: { row: number; message: string }[];
}

export interface AttributeMapping {
  file_column: string;
  db_attribute: number | null;
  create_new: boolean;
  new_attribute_name?: string;
}

export type TranslationTaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

export interface TranslationTask {
  id: number;
  locale: string;
  status: TranslationTaskStatus;
  product_count: number;
  translated_count: number;
  created_at: string;
}

export interface Translation {
  id: number;
  product_id: number;
  locale_code: string;
  title: string;
  description: string;
  status: string;
}

export type PlannerRunStatus = 'pending' | 'running' | 'completed' | 'approved' | 'failed';

export interface PlannerRun {
  id: number;
  locale: string;
  product_type: string;
  status: PlannerRunStatus;
  keyword_count: number;
  created_at: string;
}

export interface PlannerKeyword {
  id: number;
  keyword: string;
  search_volume: number;
  competition: string;
  approved: boolean;
}

export interface GenerationBatch {
  id: number;
  name: string;
  status: string;
  variant_count: number;
  created_at: string;
}

export interface GenerationRun {
  id: number;
  batch_id: number;
  type: 'title' | 'content';
  status: string;
  created_at: string;
}

export interface ExportProfile {
  id: number;
  name: string;
  channel: string;
  format: string;
}

export interface ExportJob {
  id: number;
  profile: string;
  status: string;
  file_url: string | null;
  created_at: string;
}

// API functions

// Global data
export const getLocales = () => fetchPaginated<Locale>('/locales/');
export const getProductTypes = () => fetchPaginated<ProductType>('/product-types/');
export const getAttributes = () => fetchPaginated<Attribute>('/attributes/');
export const getChannels = () => fetchPaginated<Channel>('/channels/');

// Imports
export const getImports = (params?: PaginationParams) => 
  fetchPaginated<Import>('/imports/', params);
export const getImport = (id: number) => fetchOne<Import>(`/imports/${id}/`);
export const createImport = (data: { name: string }) => postData<Import>('/imports/', data);
export const uploadImportFile = (file: File) => uploadFile<Import>('/imports/upload/', file);
export const getImportPreview = (id: number) => fetchOne<ImportPreview>(`/imports/${id}/preview/`);
export const assignCategory = (id: number, category: string) => 
  postData(`/imports/${id}/assign-category/`, { category });
export const mapAttributes = (id: number, mappings: AttributeMapping[]) =>
  postData(`/imports/${id}/map-attributes/`, { mappings });

// Translations
export const getTranslationTasks = (params?: PaginationParams) =>
  fetchPaginated<TranslationTask>('/translation-tasks/', params);
export const createTranslationTask = (data: { locale: string; product_ids?: number[] }) =>
  postData<TranslationTask>('/translations/create-task/', data);
export const getTranslationTask = (taskId: number) =>
  fetchOne<TranslationTask>(`/translations/tasks/${taskId}/`);
export const getTranslation = (localeCode: string, productId: number) =>
  fetchOne<Translation>(`/translations/${localeCode}/products/${productId}/`);
export const updateTranslation = (localeCode: string, productId: number, data: Partial<Translation>) =>
  patchData<Translation>(`/translations/${localeCode}/products/${productId}/`, data);

// Keywords
export const createPlannerRun = (data: {
  locale: string;
  product_type: string;
  seed_terms: string[];
  negative_terms: string[];
}) => postData<PlannerRun>('/keywords/planner-run/', data);
export const getPlannerRun = (runId: number) =>
  fetchOne<PlannerRun>(`/keywords/planner-run/${runId}/`);
export const approvePlannerRun = (runId: number, keywordIds: number[]) =>
  postData(`/keywords/planner-run/${runId}/approve/`, { keyword_ids: keywordIds });
export const getPlannerRuns = (params?: PaginationParams) =>
  fetchPaginated<PlannerRun>('/planner-runs/', params);
export const getPlannerKeywords = (runId: number) =>
  fetchPaginated<PlannerKeyword>('/planner-run-keywords/', { run_id: runId });

// Content generation
export const generateTitles = (data: { variant_ids: number[]; template?: string }) =>
  postData<GenerationRun>('/titles/generate/', data);
export const previewContent = (data: { variant_id: number; template?: string }) =>
  postData<{ content: string }>('/content/preview/', data);
export const generateContent = (data: { variant_ids: number[]; template?: string }) =>
  postData<GenerationRun>('/content/generate/', data);
export const getGenerationBatches = (params?: PaginationParams) =>
  fetchPaginated<GenerationBatch>('/generation-batches/', params);
export const getGenerationRuns = (params?: PaginationParams) =>
  fetchPaginated<GenerationRun>('/generation-runs/', params);

// Exports
export const getExportProfiles = () => fetchPaginated<ExportProfile>('/export-profiles/');
export const createExport = (data: { profile_id: number }) =>
  postData<ExportJob>('/exports/create/', data);
export const getExportJobs = (params?: PaginationParams) =>
  fetchPaginated<ExportJob>('/export-jobs/', params);
