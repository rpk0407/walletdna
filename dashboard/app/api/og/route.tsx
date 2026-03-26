/**
 * OG image generation for WalletDNA personality cards.
 * Uses @vercel/og (ImageResponse) — rendered server-side at edge.
 *
 * Route: GET /api/og?address=<addr>&chain=<chain>
 *
 * Returns a 1200×630 PNG personality card showing:
 *   - Archetype emoji + label
 *   - Wallet address (truncated)
 *   - Six dimension bars with scores
 *   - WalletDNA branding + sybil/copytrade flags
 */

import { ImageResponse } from 'next/og'
import type { NextRequest } from 'next/server'

export const runtime = 'edge'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

const ARCHETYPE_META: Record<string, { emoji: string; label: string; color: string }> = {
  sniper:           { emoji: '🐺', label: 'The Sniper',          color: '#ef4444' },
  conviction_holder:{ emoji: '💎', label: 'Conviction Holder',   color: '#3b82f6' },
  degen:            { emoji: '🎰', label: 'The Degen',           color: '#f59e0b' },
  researcher:       { emoji: '🧠', label: 'The Researcher',      color: '#8b5cf6' },
  follower:         { emoji: '🐑', label: 'The Follower',        color: '#6b7280' },
  extractor:        { emoji: '🕷️', label: 'The Extractor',       color: '#dc2626' },
  unknown:          { emoji: '❓', label: 'Unknown',             color: '#9ca3af' },
}

const DIM_LABELS: Record<string, string> = {
  speed:          'Speed',
  conviction:     'Conviction',
  risk_appetite:  'Risk',
  sophistication: 'Sophistication',
  originality:    'Originality',
  consistency:    'Consistency',
}

export async function GET(req: NextRequest): Promise<ImageResponse | Response> {
  const { searchParams } = req.nextUrl
  const address = searchParams.get('address') ?? ''
  const chain   = searchParams.get('chain') ?? 'solana'

  if (!address) {
    return new Response('Missing address', { status: 400 })
  }

  // Fetch the wallet profile from the API
  let profile: Record<string, unknown> | null = null
  try {
    const res = await fetch(
      `${BASE_URL}/v1/wallet/${address}/profile?chain=${chain}`,
      { next: { revalidate: 3600 } },
    )
    if (res.ok) {
      profile = await res.json()
    }
  } catch {
    // Render a generic card if fetch fails
  }

  const archetype = (profile?.primary_archetype as string) ?? 'unknown'
  const meta      = ARCHETYPE_META[archetype] ?? ARCHETYPE_META.unknown
  const dims      = (profile?.dimensions as Record<string, number>) ?? {}
  const sybil     = profile?.sybil_flagged === true
  const copytrade = profile?.copytrade_flagged === true
  const confidence= typeof profile?.confidence === 'number'
    ? Math.round(profile.confidence * 100)
    : 0

  const shortAddr = address.length > 12
    ? `${address.slice(0, 6)}…${address.slice(-4)}`
    : address

  return new ImageResponse(
    (
      <div
        style={{
          width:           1200,
          height:          630,
          background:      'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
          display:         'flex',
          flexDirection:   'column',
          fontFamily:      '"Inter", sans-serif',
          color:           '#f8fafc',
          padding:         '48px 64px',
          position:        'relative',
        }}
      >
        {/* Top bar: brand + chain */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 40 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: meta.color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20 }}>
              🧬
            </div>
            <span style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.5px', color: '#94a3b8' }}>
              WalletDNA
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <span style={{ fontSize: 13, background: '#1e40af22', border: '1px solid #1e40af', borderRadius: 6, padding: '4px 12px', color: '#93c5fd' }}>
              {chain.toUpperCase()}
            </span>
            {sybil && (
              <span style={{ fontSize: 13, background: '#7f1d1d22', border: '1px solid #7f1d1d', borderRadius: 6, padding: '4px 12px', color: '#fca5a5' }}>
                ⚠ SYBIL
              </span>
            )}
            {copytrade && (
              <span style={{ fontSize: 13, background: '#78350f22', border: '1px solid #78350f', borderRadius: 6, padding: '4px 12px', color: '#fcd34d' }}>
                📋 COPY-TRADE
              </span>
            )}
          </div>
        </div>

        {/* Main content: archetype + dimensions */}
        <div style={{ display: 'flex', gap: 64, flex: 1 }}>
          {/* Left: archetype hero */}
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minWidth: 320 }}>
            <div style={{ fontSize: 96, lineHeight: 1, marginBottom: 16 }}>{meta.emoji}</div>
            <div style={{
              fontSize:    42,
              fontWeight:  800,
              letterSpacing: '-1px',
              color:       meta.color,
              lineHeight:  1.1,
              marginBottom: 12,
            }}>
              {meta.label}
            </div>
            <div style={{ fontSize: 18, color: '#64748b', fontFamily: 'monospace', marginBottom: 16 }}>
              {shortAddr}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: meta.color }} />
              <span style={{ fontSize: 14, color: '#94a3b8' }}>
                {confidence}% confidence
              </span>
            </div>
          </div>

          {/* Right: dimension bars */}
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', flex: 1, gap: 14 }}>
            {Object.entries(DIM_LABELS).map(([key, label]) => {
              const score = dims[key] ?? 0
              return (
                <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontSize: 13, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      {label}
                    </span>
                    <span style={{ fontSize: 15, fontWeight: 700, color: '#f1f5f9' }}>
                      {score}
                    </span>
                  </div>
                  <div style={{ width: '100%', height: 8, background: '#1e293b', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{
                      width:        `${score}%`,
                      height:       '100%',
                      background:   meta.color,
                      borderRadius: 4,
                    }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 32, paddingTop: 20, borderTop: '1px solid #1e293b' }}>
          <span style={{ fontSize: 13, color: '#334155' }}>walletdna.xyz</span>
          <span style={{ fontSize: 13, color: '#334155' }}>On-chain personality profiling</span>
        </div>
      </div>
    ),
    {
      width:  1200,
      height: 630,
    },
  )
}
