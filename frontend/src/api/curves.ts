import apiClient from './client'
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

export async function triggerRefresh(): Promise<CrawlResult> {
  const { data } = await apiClient.post('/curves/fx-implied-rates/refresh')
  return data
}

export async function uploadFxImpliedXlsx(file: File): Promise<UploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post('/curves/fx-implied-rates/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60_000,
  })
  return data
}
