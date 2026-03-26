/**
 * API client — typed fetch wrapper for the WalletDNA FastAPI backend.
 */

import type { ActivityResponse, Chain, Timeline, WalletProfile, SimilarWalletsResponse } from './types'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const API_KEY = process.env.WALLETDNA_API_KEY ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(API_KEY ? { 'X-Api-Key': API_KEY } : {}),
    ...((init?.headers as Record<string, string>) ?? {}),
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    headers,
    ...init,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { code: 'unknown', message: res.statusText } }))
    throw new Error(err?.error?.message ?? `HTTP ${res.status}`)
  }

  return res.json() as Promise<T>
}

export const api = {
  getProfile(address: string, chain: Chain = 'solana', refresh = false): Promise<WalletProfile> {
    const params = new URLSearchParams({ chain, refresh: String(refresh) })
    return request<WalletProfile>(`/v1/wallet/${address}/profile?${params}`)
  },

  getTimeline(address: string, chain: Chain = 'solana', window = '90d'): Promise<Timeline> {
    const params = new URLSearchParams({ chain, window })
    return request<Timeline>(`/v1/wallet/${address}/timeline?${params}`)
  },

  getSimilar(address: string, limit = 10): Promise<SimilarWalletsResponse> {
    return request<SimilarWalletsResponse>(`/v1/wallet/${address}/similar?limit=${limit}`)
  },

  getActivity(address: string, chain: Chain = 'solana'): Promise<ActivityResponse> {
    return request<ActivityResponse>(`/v1/wallet/${address}/activity?chain=${chain}`)
  },

  compareWallets(addressA: string, addressB: string, chain: Chain = 'solana') {
    return request(`/v1/wallet/compare`, {
      method: 'POST',
      body: JSON.stringify({ address_a: addressA, address_b: addressB, chain }),
    })
  },
}
