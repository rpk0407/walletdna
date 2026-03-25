/**
 * WalletDNA TypeScript types — mirrors FastAPI Pydantic schemas.
 * Generated from /v1 OpenAPI schema.
 */

export type Chain = 'solana' | 'ethereum' | 'base' | 'arbitrum'

export type ArchetypeName =
  | 'sniper'
  | 'conviction_holder'
  | 'degen'
  | 'researcher'
  | 'follower'
  | 'extractor'
  | 'unknown'

export interface Dimensions {
  speed: number
  conviction: number
  risk_appetite: number
  sophistication: number
  originality: number
  consistency: number
}

export interface WalletProfile {
  request_id: string
  address: string
  chain: Chain
  primary_archetype: ArchetypeName
  secondary_archetype: ArchetypeName | null
  confidence: number
  dimensions: Dimensions
  summary: string
  sybil_flagged: boolean
  copytrade_flagged: boolean
  analyzed_at: string
}

export interface TimelineEntry {
  archetype: ArchetypeName
  dimensions: Dimensions
  recorded_at: string
}

export interface Timeline {
  request_id: string
  address: string
  timeline: TimelineEntry[]
}

export interface SimilarWallet {
  address: string
  archetype: ArchetypeName
  similarity_score: number
}

export interface SimilarWalletsResponse {
  request_id: string
  address: string
  similar: SimilarWallet[]
}

export interface ArchetypeInfo {
  name: ArchetypeName
  description: string
  key_features: string[]
  wallet_count: number
}

export interface ApiError {
  error: {
    code: string
    message: string
  }
  request_id: string
}

export const ARCHETYPE_META: Record<ArchetypeName, { emoji: string; label: string; color: string }> = {
  sniper: { emoji: '\uD83D\uDC3A', label: 'The Sniper', color: '#ef4444' },
  conviction_holder: { emoji: '\uD83D\uDC8E', label: 'Conviction Holder', color: '#3b82f6' },
  degen: { emoji: '\uD83C\uDFB0', label: 'The Degen', color: '#f59e0b' },
  researcher: { emoji: '\uD83E\uDDE0', label: 'The Researcher', color: '#8b5cf6' },
  follower: { emoji: '\uD83D\uDC11', label: 'The Follower', color: '#6b7280' },
  extractor: { emoji: '\uD83D\uDD77', label: 'The Extractor', color: '#dc2626' },
  unknown: { emoji: '\u2753', label: 'Unknown', color: '#9ca3af' },
}
