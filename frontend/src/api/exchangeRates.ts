import apiClient from './client'
import type {
  ExchangeRate,
  ExchangeRateCoverageSummary,
  ExchangeRateFilterParams,
  ExchangeRateImportResult,
  ExchangeRateListResponse,
  ExchangeRateManualCreate,
  ExchangeRateUploadResult,
} from '@/types/exchangeRate'

export async function fetchExchangeRates(
  params: ExchangeRateFilterParams,
): Promise<ExchangeRateListResponse> {
  const { data } = await apiClient.get('/exchange-rates', { params })
  return data
}

export async function exportExchangeRates(params: ExchangeRateFilterParams): Promise<Blob> {
  const { data } = await apiClient.get('/exchange-rates/export', {
    params,
    responseType: 'blob',
  })
  return data
}

export async function fetchExchangeRateCoverage(): Promise<ExchangeRateCoverageSummary> {
  const { data } = await apiClient.get('/exchange-rates/coverage')
  return data
}

export async function fetchCcyPairs(): Promise<string[]> {
  const { data } = await apiClient.get('/exchange-rates/ccy-pairs')
  return data
}

export async function importFromCurve(rateDate: string): Promise<ExchangeRateImportResult> {
  const { data } = await apiClient.post('/exchange-rates/import-from-curve', null, {
    params: { rate_date: rateDate },
  })
  return data
}

export async function importAllDatesFromCurve(): Promise<ExchangeRateImportResult> {
  const { data } = await apiClient.post('/exchange-rates/import-from-curve/all-dates')
  return data
}

export async function createManualRate(payload: ExchangeRateManualCreate): Promise<ExchangeRate> {
  const { data } = await apiClient.post('/exchange-rates/manual', payload)
  return data
}

export async function uploadExchangeRatesCsv(file: File): Promise<ExchangeRateUploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post('/exchange-rates/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60_000,
  })
  return data
}
