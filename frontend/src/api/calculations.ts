import apiClient from './client'
import type { GreeksRequest, GreeksResult, PricingRequest, PricingResult } from '@/types/calculation'

export async function calculateGreeks(payload: GreeksRequest): Promise<GreeksResult[]> {
  const { data } = await apiClient.post('/calculations/greeks', payload)
  return data
}

export async function priceOption(payload: PricingRequest): Promise<PricingResult> {
  const { data } = await apiClient.post('/calculations/price', payload)
  return data
}
