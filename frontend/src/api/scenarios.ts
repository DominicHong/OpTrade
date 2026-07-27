/** Scenario analysis API client. */
import apiClient from './client'
import type {
  ScenarioAnalysisRequest,
  ScenarioAnalysisResponse,
  BuiltinScenariosRequest,
  BuiltinScenariosResponse,
  RequiredPairsResponse,
  DefaultPairParams,
  EarliestTradeDateResponse,
  ScenarioSweepRequest,
  ScenarioSweepResponse,
} from '@/types/scenario'

export async function analyzeScenario(
  payload: ScenarioAnalysisRequest,
): Promise<ScenarioAnalysisResponse> {
  const { data } = await apiClient.post<ScenarioAnalysisResponse>('/scenarios/analyze', payload)
  return data
}

export async function analyzeBuiltinScenarios(
  payload: BuiltinScenariosRequest,
): Promise<BuiltinScenariosResponse> {
  const { data } = await apiClient.post<BuiltinScenariosResponse>('/scenarios/builtin', payload)
  return data
}

export async function fetchRequiredPairs(
  portfolioIds: string | null,
  valuationDate: string,
): Promise<RequiredPairsResponse> {
  const params: Record<string, string> = {}
  if (portfolioIds) params.portfolio_ids = portfolioIds
  params.valuation_date = valuationDate
  const { data } = await apiClient.get<RequiredPairsResponse>('/scenarios/required-pairs', { params })
  return data
}

export async function fetchDefaultPairParams(
  ccyPair: string,
  valuationDate: string,
  curveType?: string | null,
): Promise<DefaultPairParams> {
  const params: Record<string, string> = {
    ccy_pair: ccyPair,
    valuation_date: valuationDate,
  }
  if (curveType) params.curve_type = curveType
  const { data } = await apiClient.get<DefaultPairParams>('/scenarios/default-pair-params', { params })
  return data
}

export async function fetchEarliestGlobalTradeDate(): Promise<EarliestTradeDateResponse> {
  const { data } = await apiClient.get<EarliestTradeDateResponse>('/scenarios/earliest-trade-date')
  return data
}

export async function analyzeSweep(
  payload: ScenarioSweepRequest,
): Promise<ScenarioSweepResponse> {
  const { data } = await apiClient.post<ScenarioSweepResponse>('/scenarios/sweep', payload)
  return data
}
