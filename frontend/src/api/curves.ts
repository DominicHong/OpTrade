import apiClient from './client'
import { uploadFile } from './upload'
import type {
  CurveDefinition,
  CurveCoverageSummary,
  CrawlResult,
  FxImpliedRateFilterParams,
  FxImpliedRateListResponse,
  UploadResult,
} from '@/types/curve'

export async function fetchCurveDefinitions(): Promise<CurveDefinition[]> {
  const { data } = await apiClient.get('/curves/definitions')
  return data
}

export async function fetchFxImpliedRates(
  params: FxImpliedRateFilterParams,
): Promise<FxImpliedRateListResponse> {
  const { data } = await apiClient.get('/curves/fx-implied-rates', { params })
  return data
}

export async function exportFxImpliedRates(params: FxImpliedRateFilterParams): Promise<Blob> {
  const { data } = await apiClient.get('/curves/fx-implied-rates/export', {
    params,
    responseType: 'blob',
  })
  return data
}

export async function fetchCurveCoverage(): Promise<CurveCoverageSummary> {
  const { data } = await apiClient.get('/curves/fx-implied-rates/coverage')
  return data
}

export async function fetchCurrencies(): Promise<string[]> {
  const { data } = await apiClient.get('/curves/fx-implied-rates/currencies')
  return data
}

export async function fetchTenors(): Promise<string[]> {
  const { data } = await apiClient.get('/curves/fx-implied-rates/tenors')
  return data
}

/** Crawl trigger timeout: browser launch plus one or more export/parse
 *  cycles can take several minutes (chinamoney limits exports to one month
 *  per file, so long gaps need multiple downloads). */
const CRAWL_TIMEOUT_MS = 600_000

export async function triggerRefresh(): Promise<CrawlResult> {
  const { data } = await apiClient.post('/curves/fx-implied-rates/refresh', undefined, {
    timeout: CRAWL_TIMEOUT_MS,
  })
  return data
}

export async function uploadFxImpliedXlsx(file: File): Promise<UploadResult> {
  return uploadFile<UploadResult>('/curves/fx-implied-rates/upload', file)
}
