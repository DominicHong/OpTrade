import apiClient from './client'
import type { HeatmapResponse, GreeksResult } from '@/types/calculation'

export async function runSpotShift(params: Record<string, unknown>): Promise<GreeksResult[]> {
  const { data } = await apiClient.post('/scenarios/spot-shift', params)
  return data
}

export async function runVolShift(params: Record<string, unknown>): Promise<GreeksResult[]> {
  const { data } = await apiClient.post('/scenarios/vol-shift', params)
  return data
}

export async function runTimeDecay(params: Record<string, unknown>): Promise<GreeksResult[]> {
  const { data } = await apiClient.post('/scenarios/time-decay', params)
  return data
}

export async function runHeatmap(params: Record<string, unknown>): Promise<HeatmapResponse> {
  const { data } = await apiClient.post('/scenarios/heatmap', params)
  return data
}
