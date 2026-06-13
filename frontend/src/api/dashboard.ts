import apiClient from './client'
import type { DashboardSummary, RiskMetricsSummary, ExpiryProfile } from '@/types/api'

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await apiClient.get('/dashboard/summary')
  return data
}
