import axios, { AxiosError, AxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/** Shape of typical DRF validation error response */
export interface ApiErrorData {
  detail?: string | string[];
  non_field_errors?: string[];
  /** JSON 500 from our views (e.g. persist-mappings) */
  error?: string;
  [field: string]: string[] | string | undefined;
}

/**
 * Get a single user-friendly message from an API error response.
 * Handles error (our JSON 500), detail, non_field_errors, and per-field errors (e.g. from DRF serializers).
 */
export function getApiErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as AxiosError<ApiErrorData>;
    const data = axiosError.response?.data;
    if (data && typeof data === 'object' && !Array.isArray(data)) {
      if (typeof data.error === 'string') return data.error;
      if (typeof data.detail === 'string') return data.detail;
      if (Array.isArray(data.detail) && data.detail.length) return data.detail.join('. ');
      if (Array.isArray(data.non_field_errors) && data.non_field_errors.length)
        return data.non_field_errors.join('. ');
      const fieldMessages = Object.entries(data)
        .filter(([k]) => k !== 'detail' && k !== 'error' && Array.isArray(data[k]))
        .map(([field, msgs]) => `${field}: ${(msgs as string[]).join(', ')}`);
      if (fieldMessages.length) return fieldMessages.join('. ');
    }
    const dataStr = typeof data === 'string' ? data : null;
    if (dataStr !== null && dataStr.length < 500) return dataStr;
    if (dataStr !== null) return `Server error (HTML or long response). Check Network tab for response body.`;
  }
  if (error instanceof Error) return error.message;
  return String(error);
}
export const AUTH_TOKEN_KEY = 'authToken';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
    if (token && config.headers) {
      config.headers['Authorization'] = `Token ${token}`;
    }
  }
  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Log 404 errors for debugging
    if (error.response?.status === 404) {
      console.error('404 Error:', error.config?.method?.toUpperCase(), error.config?.url, error.response?.data);
    }
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
  id: number;
  code: string;
  name: string;
}

export interface ProductType {
  id: number;
  code: string;
  default_label: string;
  parent_id: number | null;
  main_category: string;
  category_path: string;
  is_active: boolean;
}

export interface AttributeValue {
  id: number;
  code: string;
  sort_order: number;
}

export interface Attribute {
  id: number;
  code: string;
  data_type: 'text' | 'number' | 'bool' | 'enum' | 'json';
  unit?: string | null;
  is_multi?: boolean;
  is_value_translatable?: boolean;
  created_at?: string;
  values?: AttributeValue[];
}

export interface ProductTypeAttribute {
  id: number;
  attribute: Attribute;
  required: boolean;
  filterable: boolean;
  variant_level: boolean;
}

export type ProductStatus = 'draft' | 'active' | 'discontinued';

export interface Product {
  id: number;
  product_type_id: number;
  code: string;
  status: ProductStatus;
  series: string | null;
  brand: string | null;
  model: string | null;
  default_label: string;
  variant_count?: number;
}

export interface Variant {
  id: number;
  product_id: number;
  product?: Product;  // Optional populated product
  barcode: string | null;
  mpn: string | null;
  internal_sku: string;
  sku: string | null;
  axis_signature: string | null;
  source_title?: string;
  source_description?: string;
  source_locale?: string;
  source_supplier?: string;
  source_sku?: string;
  created_at?: string;
}

export interface ProductCreate {
  product_type_id: number;
  code: string;
  status?: ProductStatus;
  series?: string | null;
  brand?: string | null;
  model?: string | null;
  default_label?: string;
  attributes?: Record<string, string | number | boolean | null>;
  // Note: source_* fields are on Variant, not Product
}

export interface VariantCreate {
  product_id: number;
  barcode?: string | null;
  mpn?: string | null;
  sku?: string | null;
  axis_signature?: string | null;
  source_title?: string | null;
  source_description?: string | null;
  source_locale?: string | null;
  source_supplier?: string | null;
  source_sku?: string | null;
}

export interface Channel {
  id: number;
  name: string;
  code: string;
  is_active?: boolean;
  priority?: number;
  created_at?: string;
}

export type ImportStatus = 'uploaded' | 'parsed' | 'mapped' | 'committed' | 'failed';

export interface Import {
  id: number;
  created_by: string;
  created_at: string;
  original_filename: string;
  file_type: string;
  status: ImportStatus;
  row_count: number;
  error_count: number;
  parse_error_message?: string;
}

export interface ImportRow {
  id: number;
  row_number: number;
  raw: Record<string, unknown>;
  normalized: Record<string, unknown> | null;
  errors: Record<string, unknown> | null;
  is_valid: boolean;
}

export interface ImportPreview {
  import: Import;
  rows: ImportRow[];
  errors: number;
  columns?: string[];
}

export interface CategoryBatch {
  id: number;
  product_import_id: number;
  category: string;
  status: string;
  product_count: number;
  variant_count: number;
  created_at: string;
}

export interface AttributeMapping {
  source_attr_name: string;
  target_attribute_id: number | null;
  strategy: 'matched' | 'created' | 'ignored';
  notes?: string;
  confidence?: number | null;
}

export type TranslationTaskStatus = 'pending' | 'in_progress' | 'done' | 'failed';
export type TranslationScope = 'attribute' | 'attribute_value' | 'product_type' | 'product_attribute_value';

export interface TranslationTask {
  id: number;
  locale: string;
  scope: TranslationScope;
  target_ids: number[];
  channel_id?: number | null;
  status: TranslationTaskStatus;
  model: string;
  error: string;
  // Progress tracking fields
  items_total: number;
  items_completed: number;
  progress_percent: number;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  // Timestamps
  created_at: string;
  updated_at: string;
}

export interface TranslationTaskCreate {
  locale: string;
  scope: TranslationScope;
  target_ids: number[];
  model?: string;
  channel_id?: number | null;
}

export interface TranslatableAttribute {
  id: number;
  code: string;
  data_type: string;
  is_value_translatable: boolean;
  product_types: Array<{
    id: number;
    code: string;
    default_label: string;
    variant_level: boolean;
  }>;
  translatable_value_count: number;
}

export interface Translation {
  id: number;
  product_id: number;
  locale_code: string;
  title: string;
  description: string;
  status: string;
}

export interface ProductTranslation {
  product_id: number;
  locale: string;
  title: string;
  description: string;
  meta_title: string;
  meta_description: string;
  slug: string;
  attributes: Array<{
    product_attribute_value_id: number;
    attribute_id: number;
    attribute_code: string;
    source_value: string;
    translated_value: string;
  }>;
}

export interface ProductTranslationUpdate {
  title?: string;
  description?: string;
  meta_title?: string;
  meta_description?: string;
  slug?: string;
  attribute_values?: Array<{
    product_attribute_value_id: number;
    value_text: string;
  }>;
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

// Channel Listing (Group) types
export interface ChannelListing {
  id: number;
  product_id: number;
  product_code?: string;
  product_type_id?: number | null;
  channel_id: number;
  channel_code?: string;
  locale_id: number | null;
  locale_code?: string | null;
  name: string;
  is_default: boolean;
  variant_count?: number;
  created_at: string;
  updated_at: string;
}

/** Axis from API: listing-specific axes have id/enabled; resolved axes (channel/product fallback) may omit them */
export interface ChannelListingAxisItem {
  id?: number;
  attribute_id: number;
  attribute_code: string;
  position: number;
  label_override?: string | null;
  enabled?: boolean;
}

export interface ChannelListingDetail extends ChannelListing {
  variants: Array<{
    id: number;
    sku: string | null;
    barcode: string | null;
    external_id: string;
    sync_status: string;
  }>;
  axes: ChannelListingAxisItem[];
}

export interface ChannelListingCreate {
  product_id: number;
  channel_id: number;
  locale_id?: number | null;
  name?: string;
  is_default?: boolean;
}

export interface MoveVariantsResponse {
  listing_id: number;
  moved_count: number;
  removed_from: Array<{
    listing_id: number;
    listing_name: string;
    variant_ids: number[];
  }>;
  variants: Array<{
    id: number;
    sku: string | null;
    product_id: number;
  }>;
}

export interface ListingDifferences {
  listing: {
    id: number;
    name: string;
    product_id: number;
    product_code: string;
    channel_id: number;
    channel_code: string;
    locale_code: string | null;
  };
  variants: Array<{
    id: number;
    sku: string | null;
  }>;
  differences: Array<{
    attribute_id: number;
    attribute_code: string;
    attribute_data_type: string;
    variant_values: Record<number, { display: string | null; attribute_value_id: number | null } | null>;
    unique_values: string[];
    unique_values_count: number;
    is_candidate_axis: boolean;
    has_missing_values: boolean;
  }>;
  common_attributes: Array<{
    attribute_id: number;
    attribute_code: string;
    common_value: string;
  }>;
  suggested_axes: Array<{
    attribute_id: number;
    attribute_code: string;
    unique_values: string[];
  }>;
  message?: string;
}

export interface ListingAxis {
  attribute_id: number;
  position: number;
  label_override?: string | null;
  enabled?: boolean;
}

export interface SetAxesResponse {
  listing_id: number;
  axes: Array<{
    id: number;
    attribute_id: number;
    attribute_code: string;
    position: number;
    label_override: string | null;
    enabled: boolean;
  }>;
}

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  is_staff: boolean;
  is_superuser: boolean;
}

export interface AuthResponse {
  token: string;
  user: AuthUser;
}

// API functions

// Global data
export const getLocales = (params?: PaginationParams) => fetchPaginated<Locale>('/locales/', params);
export const getLocale = (id: number) => fetchOne<Locale>(`/locales/${id}/`);
export const createLocale = (data: { code: string; name?: string }) =>
  postData<Locale, { code: string; name?: string }>('/locales/', data);
export const updateLocale = (id: number, data: Partial<Locale>) =>
  patchData<Locale>(`/locales/${id}/`, data);
export const deleteLocale = (id: number) => apiClient.delete(`/locales/${id}/`);
export const getProductTypes = () => fetchPaginated<ProductType>('/product-types/');
export const getProductTypeAttributes = (productTypeId: number) =>
  fetchOne<ProductTypeAttribute[]>(`/product-types/${productTypeId}/attributes/`);

export interface ProductTypeCreate {
  code: string;
  default_label?: string;
  main_category?: string;
  category_path?: string;
  parent_id?: number | null;
  is_active?: boolean;
}

export const createProductType = (data: ProductTypeCreate) =>
  postData<ProductType, ProductTypeCreate>('/product-types/', data);
export const getAttributes = (params?: PaginationParams) => fetchPaginated<Attribute>('/attributes/', params);
export const getAttribute = (id: number) => fetchOne<Attribute>(`/attributes/${id}/`);
export const createAttribute = (data: Omit<Attribute, 'id' | 'created_at'>) =>
  postData<Attribute>('/attributes/', data);
export const updateAttribute = (id: number, data: Partial<Attribute>) =>
  patchData<Attribute>(`/attributes/${id}/`, data);
export const deleteAttribute = (id: number) => apiClient.delete(`/attributes/${id}/`);
export const bulkUpdateAttributes = (ids: number[], updates: Partial<Attribute>) =>
  apiClient.patch<{ updated_count: number; message: string }>('/attributes/bulk-update/', {
    ids,
    updates,
  }).then(res => res.data);

export const getChannels = (params?: PaginationParams) => fetchPaginated<Channel>('/channels/', params);
export const getChannel = (id: number) => fetchOne<Channel>(`/channels/${id}/`);
export const createChannel = (data: Omit<Channel, 'id' | 'created_at'>) =>
  postData<Channel>('/channels/', data);
export const updateChannel = (id: number, data: Partial<Channel>) =>
  patchData<Channel>(`/channels/${id}/`, data);
export const deleteChannel = (id: number) => apiClient.delete(`/channels/${id}/`);

export interface CreateAttributeRequest {
  code: string;
  data_type: 'text' | 'number' | 'bool' | 'enum' | 'json';
  unit?: string;
  is_multi?: boolean;
  is_value_translatable?: boolean;
  product_type_id: number;
  required?: boolean;
  filterable?: boolean;
  variant_level?: boolean;
}

export interface CreateAttributeResponse {
  attribute: Attribute;
  product_type_attribute: ProductTypeAttribute;
  attribute_created: boolean;
  association_created: boolean;
}

export const createAttributeWithProductType = (data: CreateAttributeRequest) =>
  postData<CreateAttributeResponse>('/attributes/create-with-product-type/', data);

export interface AddAttributeValueRequest {
  attribute_id: number;
  code: string;
  sort_order?: number;
}

export const addAttributeValue = (data: AddAttributeValueRequest) =>
  postData<AttributeValue>('/attribute-values/add-to-attribute/', data);

export interface LinkAttributeToProductTypeRequest {
  attribute_id: number;
  required?: boolean;
  filterable?: boolean;
  variant_level?: boolean;
}

export const linkAttributeToProductType = (productTypeId: number, data: LinkAttributeToProductTypeRequest) =>
  postData<ProductTypeAttribute>(`/product-types/${productTypeId}/link-attribute/`, data);

export const login = (email: string, password: string) =>
  postData<AuthResponse, { email: string; password: string }>('/auth/login/', { email, password });
export const signup = (email: string, password: string, full_name?: string) =>
  postData<AuthResponse, { email: string; password: string; full_name?: string }>(
    '/auth/signup/',
    { email, password, full_name }
  );
export const logout = () => postData<{ detail: string }>('/auth/logout/');
export const getMe = () => fetchOne<{ user: AuthUser }>('/auth/me/');

// Imports
export const getImports = (params?: PaginationParams) => 
  fetchPaginated<Import>('/imports/', params);
export const getImport = (id: number) => fetchOne<Import>(`/imports/${id}/`);
export const createImport = (data: { name: string }) => postData<Import>('/imports/', data);
export const uploadImportFile = (file: File, options?: { group_by_product_key?: boolean }) => {
  const formData = new FormData();
  formData.append('source_file', file);
  
  // Default to false for manual grouping workflow
  const groupByProductKey = options?.group_by_product_key ?? false;
  formData.append('group_by_product_key', String(groupByProductKey));
  
  return apiClient.post<Import>('/imports/upload/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }).then(res => res.data);
};
export const getImportPreview = (id: number) => fetchOne<ImportPreview>(`/imports/${id}/preview/`);
export const assignCategory = (id: number, category: string) =>
  postData<CategoryBatch, { category: string }>(`/imports/${id}/assign-category/`, { category });
export const mapAttributes = (
  id: number,
  categoryBatchId: number,
  mappings: AttributeMapping[]
) =>
  postData(`/imports/${id}/map-attributes/`, {
    category_batch_id: categoryBatchId,
    mappings,
  });

export const processImport = (id: number) =>
  postData<{
    products_created: number;
    products_updated: number;
    variants_created: number;
    variants_updated: number;
    attribute_values_created: number;
    errors: number;
    error_details: Array<{ row: number; error: string }>;
  }>(`/imports/${id}/process/`, {});

// Products
export const getProducts = (params?: PaginationParams) =>
  fetchPaginated<Product>('/products/', params);

export const createProduct = (data: ProductCreate) =>
  postData<Product, ProductCreate>('/products/', data);

export const deleteProduct = (id: number) =>
  apiClient.delete(`/products/${id}/`).then((res) => res.data);

export const createVariant = (data: VariantCreate) =>
  postData<Variant, VariantCreate>('/variants/', data);

export const createVariantForProduct = (productId: number, data: Omit<VariantCreate, 'product_id'>) =>
  postData<Variant>(`/products/${productId}/variants/`, data);

export const getVariants = (params?: PaginationParams) =>
  fetchPaginated<Variant>('/variants/', params);

export const getProductVariants = (productId: number) =>
  fetchOne<Variant[]>(`/products/${productId}/variants/`);

export const getVariant = (id: number) =>
  fetchOne<Variant>(`/variants/${id}/`);

export const updateVariant = (id: number, data: Partial<Omit<VariantCreate, 'product_id'>>) =>
  patchData<Variant>(`/variants/${id}/`, data);

export const deleteVariant = (id: number) =>
  apiClient.delete(`/variants/${id}/`);

export interface VariantAttributeValue {
  id: number;
  attribute_id: number;
  attribute_code: string;
  attribute_name: string;
  data_type: string;
  value: string | number | boolean | null;
  attribute_value_id: number | null;
  attribute_value_label: string | null;
}

export const getVariantAttributeValues = (variantId: number) =>
  fetchOne<VariantAttributeValue[]>(`/variants/${variantId}/attribute-values/`);

// Variant grouping types and functions
export interface VariantComparison {
  variants: Array<{
    id: number;
    sku: string | null;
    product_id: number;
    product_code: string | null;
  }>;
  differences: Array<{
    attribute_id: number;
    attribute_code: string;
    attribute_data_type: string;
    variant_values: Record<string, {
      display: string | null;
      attribute_value_id: number | null;
      raw: {
        value_text: string | null;
        value_number: string | null;
        value_bool: boolean | null;
      };
    } | null>;
    unique_values: string[];
    unique_values_count: number;
    is_candidate_axis: boolean;
    has_missing_values: boolean;
  }>;
  common_attributes: Array<{
    attribute_id: number;
    attribute_code: string;
    common_value: string;
  }>;
}

export interface VariationAxis {
  attribute_id: number;
  position: number;
  label_override?: string;
}

export interface GroupVariantsRequest {
  variant_ids: number[];
  channel_id: number;
  variation_axes: VariationAxis[];
  create_new_product: boolean;
  product_code?: string;
  product_type_id?: number;
  target_product_id?: number;
}

export interface GroupVariantsResponse {
  product: {
    id: number;
    code: string;
    created: boolean;
  };
  channel: {
    id: number;
    code: string;
  };
  variants_grouped: number;
  axes: Array<{
    id: number;
    attribute_id: number;
    attribute_code: string;
    position: number;
  }>;
}

export const compareVariants = (variantIds: number[]) =>
  postData<VariantComparison>('/variants/compare/', { variant_ids: variantIds });

export const groupVariantsWithAxes = (data: GroupVariantsRequest) =>
  postData<GroupVariantsResponse>('/variants/group-with-axes/', data);

export interface UngroupVariantsResponse {
  ungrouped_count: number;
  variants: Array<{
    id: number;
    sku: string | null;
    old_product_id: number;
    old_product_code: string;
    new_product_id: number;
    new_product_code: string;
  }>;
  orphaned_products_deleted: number;
}

export const ungroupVariants = (variantIds: number[]) =>
  postData<UngroupVariantsResponse>('/variants/ungroup/', { variant_ids: variantIds });

// Translations
export const getTranslationTasks = (params?: PaginationParams) =>
  fetchPaginated<TranslationTask>('/translation-tasks/', params);
export const createTranslationTask = (data: TranslationTaskCreate) =>
  postData<TranslationTask>('/translation-tasks/', data);
export const getTranslationTask = (taskId: number) =>
  fetchOne<TranslationTask>(`/translation-tasks/${taskId}/`);
export const retryTranslationTask = (taskId: number) =>
  postData<TranslationTask>(`/translation-tasks/${taskId}/retry/`, {});

export interface TranslationResultItem {
  id: number;
  source_id: number;
  source_code?: string;
  source_value: string;
  translated_value: string;
  attribute_code?: string;
  main_category?: string;
}

export interface TranslationResults {
  scope: TranslationScope;
  locale: string;
  count: number;
  items: TranslationResultItem[];
  truncated?: boolean;
}

export const getTranslationTaskResults = (taskId: number) =>
  fetchOne<TranslationResults>(`/translation-tasks/${taskId}/results/`);

// Returns the URL for downloading translations Excel export
export const getTranslationExportUrl = (taskId: number) =>
  `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/translations/export/${taskId}/`;

// Returns the URL for downloading translated products CSV (attributes + values) for a locale
export const getTranslatedProductsCsvExportUrl = (localeCode: string) =>
  `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/translations/export-translated-products-csv/?locale_code=${encodeURIComponent(localeCode)}`;

export interface TranslationStatusCounts {
  total: number;
  translated: number;
  untranslated: number;
}

export interface TranslationStatus {
  locale: string;
  attributes: TranslationStatusCounts;
  attribute_values: TranslationStatusCounts;
  product_types: TranslationStatusCounts;
  product_attribute_values: TranslationStatusCounts;
}

export const getTranslationStatus = (localeCode: string) =>
  fetchOne<TranslationStatus>(`/translations/status/${localeCode}/`);

export const updateTranslation = (
  scope: TranslationScope, 
  translationId: number, 
  data: { translated_value: string; main_category?: string }
) => patchData<TranslationResultItem>(`/translations/${scope}/${translationId}/`, data);

export const getProductTranslation = (localeCode: string, productId: number) =>
  fetchOne<ProductTranslation>(`/translations/${localeCode}/products/${productId}/`);
export const updateProductTranslation = (localeCode: string, productId: number, data: ProductTranslationUpdate) =>
  patchData<ProductTranslation>(`/translations/${localeCode}/products/${productId}/`, data);
export const getTranslatableAttributes = () =>
  fetchPaginated<TranslatableAttribute>('/attributes-translatable/');

// Keywords
export const createPlannerRun = (data: {
  locale: string;
  product_type_id?: number;
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

export interface ImportKeywordsCsvParams {
  locale_code: string;
  channel_code: string;
  product_type_id?: number | null;
  run_id?: number | null;
  source_code?: string;
  month?: string;
  delimiter?: string;
}
export interface ImportKeywordsCsvResult {
  run_id: number;
  keywords_created: number;
  keywords_updated: number;
  metrics_created: number;
  metrics_updated: number;
  run_links: number;
}
export const importKeywordsCsv = (file: File, params: ImportKeywordsCsvParams) =>
  uploadFile<ImportKeywordsCsvResult>('/keywords/planner-run/import-csv/', file, {
    locale_code: params.locale_code,
    channel_code: params.channel_code,
    ...(params.product_type_id != null && { product_type_id: String(params.product_type_id) }),
    ...(params.run_id != null && { run_id: String(params.run_id) }),
    ...(params.source_code && { source_code: params.source_code }),
    ...(params.month && { month: params.month }),
    ...(params.delimiter && { delimiter: params.delimiter }),
  });

// Keyword mapping
export interface RunAttributeMap {
  id: number;
  keyword_id: number;
  keyword_term: string;
  attribute_code: string;
  attribute_value_id: number | null;
  attribute_value_code: string | null;
  confidence: number | null;
  status: 'suggested' | 'approved' | 'rejected';
  tagged_by: string;
  reason_code: string;
  updated_at: string;
}
export const mapPlannerRunKeywords = (runId: number, params?: { limit?: number; dry_run?: boolean }) =>
  postData<{ mapped: number; mapping_ids: number[] }>(`/keywords/planner-run/${runId}/map/`, params ?? {});
export const getPlannerRunMappings = (runId: number, params?: { page?: number; page_size?: number }) =>
  fetchPaginated<RunAttributeMap>(`/keywords/planner-run/${runId}/mappings/`, params);
export const updatePlannerRunMapping = (attributeMapId: number, status: 'approved' | 'rejected') =>
  patchData<{ status: string }>(`/keywords/planner-run/mappings/${attributeMapId}/`, { status });
export const persistPlannerRunMappings = (runId: number) =>
  postData<{ status: string; message: string }>(`/keywords/planner-run/${runId}/persist-mappings/`, {});

// Title generation (POST /titles/generate/)
export interface TitleGenerateRequest {
  variant_ids: number[];
  locale_code: string;
  channel_code: string;
  planner_run_id?: number | null;
  include_descriptions?: boolean;
  title_mode_override?: 'auto' | 'review' | null;
  context?: string;
}

export interface TitleGenerateOutputItem {
  status: 'generated' | 'needs_approval';
  variant_id: number;
  product_id: number;
  output_id?: number;
  run_id?: number;
  template_id?: number;
  title?: string;
  selection_id?: number | null;
  preview_title?: string;
  suggestions?: string[];
}

export interface TitleGenerateResponse {
  status: 'completed';
  outputs: TitleGenerateOutputItem[];
}

export const generateTitles = (data: TitleGenerateRequest) =>
  postData<TitleGenerateResponse>('/titles/generate/', data);

// Content generation
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

// Channel Listings (Groups)
export const getChannelListings = (params?: PaginationParams & { product_id?: number; channel_id?: number; channel_code?: string }) =>
  fetchPaginated<ChannelListing>('/channel-listings/', params);

export const getChannelListing = (id: number) =>
  fetchOne<ChannelListingDetail>(`/channel-listings/${id}/`);

export const createChannelListing = (data: ChannelListingCreate) =>
  postData<ChannelListing, ChannelListingCreate>('/channel-listings/', data);

export interface ChannelListingUpdate {
  name?: string;
  is_default?: boolean;
}

export const updateChannelListing = (id: number, data: ChannelListingUpdate) =>
  patchData<ChannelListing, ChannelListingUpdate>(`/channel-listings/${id}/`, data);

export const deleteChannelListing = (id: number) =>
  apiClient.delete(`/channel-listings/${id}/`);

export const moveVariantsToListing = (listingId: number, variantIds: number[]) =>
  postData<MoveVariantsResponse>(`/channel-listings/${listingId}/move-variants/`, { variant_ids: variantIds });

export const removeVariantsFromListing = (listingId: number, variantIds: number[]) =>
  postData<{ listing_id: number; removed_count: number }>(`/channel-listings/${listingId}/remove-variants/`, { variant_ids: variantIds });

export const getListingDifferences = (listingId: number) =>
  fetchOne<ListingDifferences>(`/channel-listings/${listingId}/differences/`);

export interface AvailableVariantForListing {
  id: number;
  sku: string | null;
  barcode: string | null;
  product_id: number;
  attributes: Record<string, string>;
}

export interface AvailableVariantsForListingResponse {
  product_id: number | null;
  product_code: string | null;
  attribute_codes: string[];
  variants: AvailableVariantForListing[];
}

export const getAvailableVariantsForListing = (listingId: number) =>
  fetchOne<AvailableVariantsForListingResponse>(`/channel-listings/${listingId}/available-variants/`);

export const getListingAxes = (listingId: number) =>
  fetchOne<{ listing_id: number; axes: SetAxesResponse['axes'] }>(`/channel-listings/${listingId}/axes/`);

export const setListingAxes = (listingId: number, axes: ListingAxis[]) =>
  apiClient.put<SetAxesResponse>(`/channel-listings/${listingId}/axes/`, { axes }).then(res => res.data);

// Channel Policy Sets
export interface ChannelPolicySet {
  id: number;
  channel: number; // channel ID
  channel_code?: string;
  version: number;
  status: 'draft' | 'active' | 'archived';
  notes: string;
  created_at: string;
}

export interface ChannelPolicySetCreate {
  channel: number;
  version: number;
  status?: 'draft' | 'active' | 'archived';
  notes?: string;
}

export const getChannelPolicySets = (params?: PaginationParams & { channel_id?: number; status?: string }) =>
  fetchPaginated<ChannelPolicySet>('/channel-policy-sets/', params);
export const getChannelPolicySet = (id: number) => fetchOne<ChannelPolicySet>(`/channel-policy-sets/${id}/`);
export const createChannelPolicySet = (data: ChannelPolicySetCreate) =>
  postData<ChannelPolicySet, ChannelPolicySetCreate>('/channel-policy-sets/', data);
export const updateChannelPolicySet = (id: number, data: Partial<ChannelPolicySetCreate>) =>
  patchData<ChannelPolicySet>(`/channel-policy-sets/${id}/`, data);
export const deleteChannelPolicySet = (id: number) => apiClient.delete(`/channel-policy-sets/${id}/`);

// Channel Locale Policies
export interface ChannelLocalePolicy {
  id: number;
  policy_set: number;
  policy_set_id?: number;
  channel_code?: string;
  locale: number;
  locale_id?: number;
  locale_code?: string;
  country_code: string;
  currency_code: string;
  title_max_len: number;
  meta_title_max_len: number;
  meta_description_max_len: number;
  description_max_len: number;
  bullet_count: number;
  bullet_max_len: number;
  title_separator: string;
  brand_position: 'start' | 'end' | 'none';
  title_mode: 'auto' | 'review';
  auto_create_selection: boolean;
  auto_approve_selection: boolean;
  selection_scope: 'product' | 'variant';
  context: string;
  normalize_whitespace: boolean;
  dedupe_words: boolean;
  banned_terms: string[];
  rules_json: Record<string, unknown>;
}

export interface ChannelLocalePolicyCreate {
  policy_set_id: number;
  locale_id: number;
  country_code?: string;
  currency_code?: string;
  title_max_len?: number;
  meta_title_max_len?: number;
  meta_description_max_len?: number;
  description_max_len?: number;
  bullet_count?: number;
  bullet_max_len?: number;
  title_separator?: string;
  brand_position?: 'start' | 'end' | 'none';
  title_mode?: 'auto' | 'review';
  auto_create_selection?: boolean;
  auto_approve_selection?: boolean;
  selection_scope?: 'product' | 'variant';
  context?: string;
  normalize_whitespace?: boolean;
  dedupe_words?: boolean;
  banned_terms?: string[];
  rules_json?: Record<string, unknown>;
}

export const getChannelLocalePolicies = (params?: PaginationParams & { channel_id?: number; locale_id?: number; policy_set_id?: number }) =>
  fetchPaginated<ChannelLocalePolicy>('/channel-locale-policies/', params);
export const getChannelLocalePolicy = (id: number) => fetchOne<ChannelLocalePolicy>(`/channel-locale-policies/${id}/`);
export const createChannelLocalePolicy = (data: ChannelLocalePolicyCreate) =>
  postData<ChannelLocalePolicy, ChannelLocalePolicyCreate>('/channel-locale-policies/', data);
export const updateChannelLocalePolicy = (id: number, data: Partial<ChannelLocalePolicyCreate>) =>
  patchData<ChannelLocalePolicy>(`/channel-locale-policies/${id}/`, data);
export const deleteChannelLocalePolicy = (id: number) => apiClient.delete(`/channel-locale-policies/${id}/`);

export interface ListingTitleGenerationRequest {
  locale_code: string;
  template_id?: number;
  planner_run_id?: number;
}

export interface ListingTitleGenerationResponse {
  generation_run_ids: number[];
  variant_count: number;
  outputs: Array<{
    status: string;
    variant_id: number;
    product_id: number;
    output_id?: number;
    run_id?: number;
    template_id?: number;
    title?: string;
    selection_id?: number;
    preview_title?: string;
  }>;
  /** Attribute values that have no translation for the requested locale (so titles show original). */
  untranslated_attribute_values?: Array<{ attribute_value_id: number; code: string; attr_code: string; attribute_id?: number }>;
}

export interface AvailableTemplate {
  id: number;
  kind: string;
  version: number;
  locale: string;
  part_count: number;
  status: string;
  created_at: string | null;
}

export const getAvailableTemplatesForListing = (listingId: number, localeCode: string) =>
  fetchOne<{ templates: AvailableTemplate[] }>(
    `/channel-listings/${listingId}/available-templates/?locale=${localeCode}`
  );

export interface CreateDefaultTemplateResponse {
  template: AvailableTemplate;
  created: boolean;
}

export const createDefaultTemplateForListing = (listingId: number, localeCode: string) =>
  postData<CreateDefaultTemplateResponse>(
    `/channel-listings/${listingId}/create-default-template/`,
    { locale_code: localeCode }
  );

export const generateListingTitles = (listingId: number, data: ListingTitleGenerationRequest) =>
  postData<ListingTitleGenerationResponse>(`/channel-listings/${listingId}/generate-titles/`, data);

export interface ListingGeneratedTitleItem {
  variant_id: number;
  sku: string;
  title: string;
  generated_at: string | null;
}

export interface ListingGeneratedTitlesResponse {
  results: ListingGeneratedTitleItem[];
}

export const getListingGeneratedTitles = (listingId: number, localeCode: string) =>
  apiClient
    .get<ListingGeneratedTitlesResponse>(`/channel-listings/${listingId}/generated-titles/`, {
      params: { locale_code: localeCode },
    })
    .then((res) => res.data);

export const updateListingGeneratedTitle = (
  listingId: number,
  variantId: number,
  localeCode: string,
  title: string
) =>
  apiClient
    .patch<ListingGeneratedTitleItem>(
      `/channel-listings/${listingId}/generated-titles/${variantId}/`,
      { locale_code: localeCode, title }
    )
    .then((res) => res.data);

/** All generated titles (DB-wide), filterable by locale and channel */
export interface AllGeneratedTitleItem {
  variant_id: number;
  sku: string;
  product_id: number | null;
  product_code: string | null;
  channel_code: string | null;
  locale_code: string | null;
  title: string;
  generated_at: string | null;
}

export interface AllGeneratedTitlesResponse {
  count: number;
  results: AllGeneratedTitleItem[];
}

export const getAllGeneratedTitles = (params?: {
  locale_code?: string;
  channel_code?: string;
  page?: number;
  page_size?: number;
}) =>
  apiClient
    .get<AllGeneratedTitlesResponse>('/generated-titles/', { params })
    .then((res) => res.data);

export interface VariantAttributeDetailsItem {
  attribute_id: number;
  attribute_code: string;
  attribute_label?: string | null;
  data_type: string;
  is_variant_level: boolean;
  product_attribute_value_id: number;
  raw_value: string | null;
  translated_value: string | null;
  source: string;
}

export interface VariantAttributeDetailsResponse {
  attributes: VariantAttributeDetailsItem[];
}

export const getVariantAttributeDetails = (
  variantId: number,
  params: { locale_code: string; channel_code?: string }
) =>
  apiClient
    .get<VariantAttributeDetailsResponse>(`/variants/${variantId}/attribute-details/`, {
      params,
    })
    .then((res) => res.data);

// Variant-level attribute value CRUD
export interface VariantAttributeValueWrite {
  attribute_id?: number;
  attribute_value_id?: number | null;
  value_text?: string | null;
  value_number?: number | null;
  value_bool?: boolean;
}

export const createVariantAttributeValue = (
  variantId: number,
  data: VariantAttributeValueWrite
) => apiClient.post<{ id: number }>(`/variants/${variantId}/attribute-values/`, data).then((res) => res.data);

export const updateVariantAttributeValue = (
  variantId: number,
  pavId: number,
  data: VariantAttributeValueWrite
) =>
  apiClient
    .patch<{ id: number }>(`/variants/${variantId}/attribute-values/${pavId}/`, data)
    .then((res) => res.data);

export const deleteVariantAttributeValue = (variantId: number, pavId: number) =>
  apiClient.delete<void>(`/variants/${variantId}/attribute-values/${pavId}/`).then(() => undefined);

// Title templates (build head term, hook term, attributes)
export const TEMPLATE_PART_TYPES = {
  head_term: 'Head term',
  hook_term: 'Hook term',
  literal: 'Literal',
  axis_attribute: 'Axis attribute',
  attribute_value: 'Attribute value',
  keyword: 'Keyword',
  brand: 'Brand',
} as const;

export interface Template {
  id: number;
  product_type_id: number;
  locale_code: string;
  channel_code: string;
  kind: string;
  version: number;
  status: string;
}

export interface TemplatePart {
  id: number;
  template_id: number;
  position: number;
  part_type: keyof typeof TEMPLATE_PART_TYPES;
  attribute_id: number | null;
  keyword_role: string | null;
  literal_text: string | null;
  required: boolean;
}

export const getTemplates = (params?: {
  product_type_id?: number;
  channel_code?: string;
  locale_code?: string;
} & PaginationParams) =>
  fetchPaginated<Template>('/templates/', params as Record<string, unknown>);

export const getTemplate = (id: number) => fetchOne<Template>(`/templates/${id}/`);

export interface TemplateCreate {
  product_type_id: number;
  locale_code: string;
  channel_code: string;
  kind?: string;
  version?: number;
  status?: string;
}

export const createTemplate = (data: TemplateCreate) =>
  postData<Template, TemplateCreate>('/templates/', {
    kind: 'title',
    version: 1,
    status: 'active',
    ...data,
  });

export const updateTemplate = (id: number, data: Partial<TemplateCreate> & { status?: string }) =>
  patchData<Template>(`/templates/${id}/`, data);

export const deleteTemplate = (id: number) => apiClient.delete(`/templates/${id}/`);

export const getTemplateParts = (templateId: number) =>
  fetchPaginated<TemplatePart>('/template-parts/', { template_id: templateId }).then((r) => r.results);

export interface TemplatePartCreate {
  template_id: number;
  position: number;
  part_type: string;
  attribute_id?: number | null;
  literal_text?: string | null;
  keyword_role?: string | null;
  required?: boolean;
}

export const createTemplatePart = (data: TemplatePartCreate) =>
  postData<TemplatePart, TemplatePartCreate>('/template-parts/', data);

export const updateTemplatePart = (id: number, data: Partial<TemplatePartCreate>) =>
  patchData<TemplatePart>(`/template-parts/${id}/`, data);

export const deleteTemplatePart = (id: number) => apiClient.delete(`/template-parts/${id}/`);

// Product-level keyword mapping (per-variant AI mapping)
export interface PersistProductKeywordMapsRequest {
  product_id?: number;
  limit?: number;
  min_confidence?: number;
  include_text_values?: boolean;
  include_i18n?: boolean;
  include_descriptions?: boolean;
  max_description_chars?: number;
  max_text_matches?: number;
  max_enum_maps?: number;
  use_llm?: boolean;
  llm_max_keywords?: number;
  dry_run?: boolean;
  /** Tell the AI what to focus on (e.g. "material, installation") */
  focus_on?: string;
  /** Tell the AI what to ignore (e.g. "oder, vs, comparison words") */
  ignore?: string;
  /** Do not map size or marketplace keywords */
  ignore_size_and_marketplace?: boolean;
  /** Prioritize head terms (broad category terms) */
  focus_head_terms?: boolean;
  /** Prioritize hook terms (product-specific terms) */
  focus_hook_terms?: boolean;
}

export interface PersistProductKeywordMapsResponse {
  products_processed: number;
  maps_created: number;
  maps_updated: number;
}

export const persistProductKeywordMaps = (runId: number, data: PersistProductKeywordMapsRequest) =>
  postData<PersistProductKeywordMapsResponse>(`/keywords/planner-run/${runId}/persist-mappings/`, data);

export interface ProductKeywordMap {
  id: number;
  product_id: number;
  keyword_term: string;
  source: string;
  match_kind: string;
  matched_text: string;
  confidence: number | null;
  attribute_code: string | null;
  attribute_name: string | null;
  attribute_value_label: string | null;
  attribute_value_code: string | null;
  num_value: number | null;
  num_unit: string | null;
  evidence: Record<string, unknown>;
  created_at: string;
}

export const getProductKeywordMaps = (runId: number, params?: PaginationParams & { product_id?: number; source?: string }) =>
  fetchPaginated<ProductKeywordMap>(`/keywords/planner-run/${runId}/product-maps/`, params);

export const deleteProductKeywordMap = (runId: number, mapId: number) =>
  apiClient.delete(`/keywords/planner-run/${runId}/product-maps/${mapId}/`);

// Suggested head/hook terms (extract after mapping; user approves/denies for title generation)
export interface SuggestedHeadTerm {
  term: string;
  keyword_id: number;
  product_count: number;
  match_kinds: string[];
  avg_searches: number;
  product_type_id: number | null;
  product_type_code: string | null;
  /** Product type label (e.g. English meaning): "Shower receiver" */
  product_type_default_label?: string | null;
  /** Longer description (e.g. notes) for the product type */
  product_type_notes?: string | null;
  /** Main category for the product type */
  product_type_main_category?: string | null;
  /** AI-generated short English meaning (when use_ai_meaning=1) */
  meaning_en?: string | null;
}
export interface ProductDisplay {
  code: string | null;
  default_label: string | null;
  variant_sku: string | null;
  variant_source_title: string | null;
}
export interface SuggestedHookTerm {
  term: string;
  keyword_id: number;
  match_kind: string;
  source: string;
  attribute_code: string | null;
  attribute_label: string | null;
  attribute_id: number | null;
  avg_searches: number;
  product_id: number;
  product_display: ProductDisplay;
}
export interface ProductVariantSummary {
  id: number;
  sku: string | null;
  source_title: string | null;
}

export interface SuggestedTermsResponse {
  run_id: number;
  product_type_id: number | null;
  product_type_code?: string | null;
  /** Product type label (e.g. English meaning): "Shower receiver" */
  product_type_default_label?: string | null;
  product_type_notes?: string | null;
  product_type_main_category?: string | null;
  product_id: number | null;
  locale_id: number;
  channel_id: number | null;
  max_head_terms: number;
  max_hook_terms: number;
  suggested_head_terms: SuggestedHeadTerm[];
  suggested_hook_terms: SuggestedHookTerm[];
  product_variants: Record<string, ProductVariantSummary[]>;
  approve_head_url: string | null;
  approve_hook_url: string | null;
}

export const getSuggestedTerms = (
  runId: number,
  params: {
    product_id?: number;
    locale_id: number;
    channel_id?: number;
    max_head_terms?: number;
    max_hook_terms?: number;
    /** Use AI to generate short English meaning for each head term (requires OPENAI_API_KEY) */
    use_ai_meaning?: boolean;
  }
) =>
  apiClient
    .get<SuggestedTermsResponse>(`/keywords/planner-run/${runId}/suggested-terms/`, {
      params: { ...params, use_ai_meaning: params.use_ai_meaning ? '1' : undefined },
    })
    .then((r) => r.data);

export interface HeadTermItem {
  term: string;
  source: 'label' | 'synonym';
  id: number | null;
}
export const getHeadTerms = (
  productTypeId: number,
  params: { locale_id: number; channel_id?: number | null }
) =>
  apiClient
    .get<{ terms: HeadTermItem[] }>(`/product-types/${productTypeId}/head-terms/`, { params })
    .then((r) => r.data);

export const removeHeadTerm = (productTypeId: number, synonymId: number) =>
  apiClient.delete(`/product-types/${productTypeId}/head-terms/${synonymId}/`);

export const addHeadTerm = (
  productTypeId: number,
  data: { locale_id: number; channel_id?: number | null; term: string }
) =>
  apiClient
    .post<{ id: number; term: string; locale_id: number; channel_id: number | null }>(
      `/product-types/${productTypeId}/head-terms/`,
      data
    )
    .then((r) => r.data);

export interface HookTermItem {
  id: number;
  term: string;
  locale_id: number;
  channel_id: number | null;
  priority: number;
}
export const getHookTerms = (
  productId: number,
  params: { locale_id: number; channel_id?: number | null }
) =>
  apiClient
    .get<{ terms: HookTermItem[] }>(`/products/${productId}/hook-terms/`, { params })
    .then((r) => r.data);

export const removeHookTerm = (productId: number, hookTermId: number) =>
  apiClient.delete(`/products/${productId}/hook-terms/${hookTermId}/`);

export const addHookTerm = (
  productId: number,
  data: { locale_id: number; channel_id?: number | null; term: string; priority?: number }
) =>
  apiClient
    .post<{ id: number; term: string; locale_id: number; channel_id: number | null; priority: number }>(
      `/products/${productId}/hook-terms/`,
      data
    )
    .then((r) => r.data);

// Saved terms (aggregate by locale/channel) for the Saved terms page
export interface SavedTermsHeadItem {
  id: number | null;
  term: string;
  source: 'label' | 'synonym';
}
export interface SavedTermsHeadByProductType {
  product_type_id: number;
  product_type_code: string | null;
  default_label: string;
  terms: SavedTermsHeadItem[];
}
export interface SavedTermsHookItem {
  id: number;
  term: string;
  priority: number;
}
export interface SavedTermsHookByProduct {
  product_id: number;
  product_code: string | null;
  default_label: string;
  terms: SavedTermsHookItem[];
}
export interface SavedTermsResponse {
  locales: Array<{ id: number; code: string; name?: string }>;
  channels: Array<{ id: number; code: string; name?: string }>;
  head_terms_by_product_type: SavedTermsHeadByProductType[];
  hook_terms_by_product: SavedTermsHookByProduct[];
}
export const getSavedTerms = (params: { locale_id?: number; channel_id?: number }) =>
  apiClient.get<SavedTermsResponse>('/keywords/saved-terms/', { params }).then((r) => r.data);

// Head selection (choose a specific head term per product/locale/channel)
export interface ProductHeadSelection {
  id: number | null;
  head_text: string | null;
  head_source: string | null;
  status: string | null;
  head_keyword_id: number | null;
}

export const getProductHeadSelection = (
  productId: number,
  params: { locale_code: string; channel_code: string }
) =>
  apiClient
    .get<ProductHeadSelection>(`/products/${productId}/head-selection/`, { params })
    .then((r) => r.data);

export const setProductHeadSelection = (
  productId: number,
  data: { locale_code: string; channel_code: string; head_text: string }
) =>
  apiClient
    .post<ProductHeadSelection>(`/products/${productId}/head-selection/`, data)
    .then((r) => r.data);

export const clearProductHeadSelection = (
  productId: number,
  data: { locale_code: string; channel_code: string }
) =>
  apiClient
    .post(`/products/${productId}/head-selection/`, { ...data, head_text: null })
    .then(() => undefined);


