import apiClient from './client'
import type {
  Portfolio,
  PortfolioCreate,
  PortfolioGreeksRequest,
  PortfolioGreeksResponse,
  PortfolioResolveRequest,
  PortfolioResolveResponse,
} from '@/types/portfolio'

export async function fetchPortfolios(): Promise<Portfolio[]> {
  const { data } = await apiClient.get('/portfolios')
  return data
}

export async function fetchPortfolio(id: number): Promise<Portfolio> {
  const { data } = await apiClient.get(`/portfolios/${id}`)
  return data
}

export async function createPortfolio(payload: PortfolioCreate): Promise<Portfolio> {
  const { data } = await apiClient.post('/portfolios', payload)
  return data
}

export async function updatePortfolio(
  id: number,
  payload: { name?: string | null; description?: string | null },
): Promise<Portfolio> {
  const { data } = await apiClient.put(`/portfolios/${id}`, payload)
  return data
}

export async function deletePortfolio(id: number): Promise<void> {
  await apiClient.delete(`/portfolios/${id}`)
}

export async function resolvePortfolioParams(
  portfolioId: number,
  params: PortfolioResolveRequest,
): Promise<PortfolioResolveResponse> {
  const { data } = await apiClient.post(
    `/portfolios/${portfolioId}/resolve-params`,
    params,
  )
  return data
}

export async function fetchPortfolioGreeks(
  portfolioId: number,
  params: PortfolioGreeksRequest,
): Promise<PortfolioGreeksResponse> {
  const { data } = await apiClient.post(`/portfolios/${portfolioId}/greeks`, params)
  return data
}
