'use client'

import { motion } from 'framer-motion'
import type { WalletProfile } from '@/lib/types'
import { ARCHETYPE_META } from '@/lib/types'
import { ArchetypeBadge } from './ArchetypeBadge'
import { DimensionBar } from './DimensionBar'

interface Props {
  profile: WalletProfile
}

export function PersonalityCard({ profile }: Props) {
  const meta = ARCHETYPE_META[profile.primary_archetype]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-900 rounded-2xl p-6 border border-gray-800"
    >
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <ArchetypeBadge archetype={profile.primary_archetype} size="lg" />
          <p className="text-gray-400 text-sm mt-3 max-w-lg">{profile.summary}</p>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500">Confidence</div>
          <div className="text-2xl font-bold" style={{ color: meta.color }}>
            {Math.round(profile.confidence * 100)}%
          </div>
        </div>
      </div>

      <div className="mt-6 space-y-2">
        {Object.entries(profile.dimensions).map(([dim, score]) => (
          <DimensionBar key={dim} label={dim} score={score as number} />
        ))}
      </div>

      {(profile.sybil_flagged || profile.copytrade_flagged) && (
        <div className="mt-4 flex gap-2 flex-wrap">
          {profile.sybil_flagged && (
            <span className="text-xs bg-red-900/40 text-red-400 border border-red-800 px-3 py-1 rounded-full">
              \uD83D\uDD77 Sybil Flagged
            </span>
          )}
          {profile.copytrade_flagged && (
            <span className="text-xs bg-yellow-900/40 text-yellow-400 border border-yellow-800 px-3 py-1 rounded-full">
              \uD83D\uDC11 Copy-Trade Detected
            </span>
          )}
        </div>
      )}
    </motion.div>
  )
}
