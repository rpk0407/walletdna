'use client'

import { motion } from 'framer-motion'
import type { WalletProfile } from '@/lib/types'
import { ARCHETYPE_META } from '@/lib/types'
import { ArchetypeBadge } from './ArchetypeBadge'
import { DimensionBar } from './DimensionBar'
import { ShieldAlert, Copy } from 'lucide-react'
import { useState } from 'react'

interface Props {
  profile: WalletProfile
}

export function PersonalityCard({ profile }: Props) {
  const meta = ARCHETYPE_META[profile.primary_archetype]
  const [copied, setCopied] = useState(false)

  function copyAddress() {
    navigator.clipboard.writeText(profile.address)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const confidencePct = Math.round(profile.confidence * 100)

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.19, 1, 0.22, 1] }}
      className="relative overflow-hidden rounded-3xl"
      style={{
        background: `linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)`,
        border: '1px solid rgba(255,255,255,0.08)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
      }}
    >
      {/* Holographic shimmer layer */}
      <motion.div
        className="absolute inset-0 pointer-events-none rounded-3xl opacity-0"
        animate={{ opacity: [0, 0.06, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          background: `linear-gradient(135deg, ${meta.color}40, transparent 40%, rgba(129,92,248,0.2) 70%, transparent)`,
          backgroundSize: '200% 200%',
        }}
      />

      {/* Archetype color top accent line */}
      <div
        className="absolute top-0 left-0 right-0 h-px"
        style={{
          background: `linear-gradient(90deg, transparent 0%, ${meta.color}80 30%, ${meta.color} 50%, ${meta.color}80 70%, transparent 100%)`,
        }}
      />

      <div className="relative p-6">
        {/* Header row */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <ArchetypeBadge archetype={profile.primary_archetype} size="lg" />

            {/* Wallet address */}
            <button
              onClick={copyAddress}
              className="flex items-center gap-1.5 mt-3 text-xs text-zinc-600 hover:text-zinc-400 transition-colors group"
            >
              <span className="font-mono truncate max-w-[180px]">
                {profile.address.slice(0, 6)}…{profile.address.slice(-4)}
              </span>
              <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
              {copied && <span className="text-sky-400 text-xs">Copied</span>}
            </button>

            <p className="text-zinc-500 text-sm mt-3 max-w-lg leading-relaxed">
              {profile.summary}
            </p>
          </div>

          {/* Confidence ring */}
          <div className="flex flex-col items-center gap-1 shrink-0">
            <div className="relative w-16 h-16">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 64 64">
                <circle
                  cx="32"
                  cy="32"
                  r="28"
                  fill="none"
                  stroke="rgba(255,255,255,0.06)"
                  strokeWidth="4"
                />
                <motion.circle
                  cx="32"
                  cy="32"
                  r="28"
                  fill="none"
                  stroke={meta.color}
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 28}`}
                  initial={{ strokeDashoffset: 2 * Math.PI * 28 }}
                  animate={{
                    strokeDashoffset:
                      2 * Math.PI * 28 * (1 - profile.confidence),
                  }}
                  transition={{ duration: 1.2, delay: 0.4, ease: [0.19, 1, 0.22, 1] }}
                  style={{ filter: `drop-shadow(0 0 6px ${meta.color}80)` }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span
                  className="text-sm font-bold"
                  style={{ color: meta.color }}
                >
                  {confidencePct}%
                </span>
              </div>
            </div>
            <span className="text-[10px] text-zinc-600 uppercase tracking-wider">
              Confidence
            </span>
          </div>
        </div>

        {/* Secondary archetype */}
        {profile.secondary_archetype && (
          <div className="mt-4 flex items-center gap-2">
            <span className="text-xs text-zinc-600">Also:</span>
            <span className="text-xs text-zinc-500 border border-white/8 px-2.5 py-0.5 rounded-full glass">
              {ARCHETYPE_META[profile.secondary_archetype]?.emoji}{' '}
              {ARCHETYPE_META[profile.secondary_archetype]?.label}
            </span>
          </div>
        )}

        {/* Dimension bars */}
        <div className="mt-6 space-y-2.5">
          {Object.entries(profile.dimensions).map(([dim, score], i) => (
            <DimensionBar key={dim} label={dim} score={score as number} delay={i * 0.05} />
          ))}
        </div>

        {/* Flags */}
        {(profile.sybil_flagged || profile.copytrade_flagged) && (
          <div className="mt-5 flex gap-2 flex-wrap">
            {profile.sybil_flagged && (
              <span className="flex items-center gap-1.5 text-xs bg-red-500/10 text-red-400 border border-red-500/20 px-3 py-1 rounded-full">
                <ShieldAlert className="w-3 h-3" />
                Sybil Flagged
              </span>
            )}
            {profile.copytrade_flagged && (
              <span className="flex items-center gap-1.5 text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 px-3 py-1 rounded-full">
                👑 Copy-Trade Detected
              </span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}
