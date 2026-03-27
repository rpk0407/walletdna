'use client'

import { motion } from 'framer-motion'

interface Props {
  label: string
  score: number // 0-100
  delay?: number
}

const DIMENSION_META: Record<string, { color: string; label: string }> = {
  speed: { color: '#ef4444', label: 'Speed' },
  conviction: { color: '#3b82f6', label: 'Conviction' },
  risk_appetite: { color: '#f59e0b', label: 'Risk' },
  sophistication: { color: '#8b5cf6', label: 'Sophistication' },
  originality: { color: '#10b981', label: 'Originality' },
  consistency: { color: '#6b7280', label: 'Consistency' },
}

export function DimensionBar({ label, score, delay = 0 }: Props) {
  const meta = DIMENSION_META[label] ?? { color: '#0ea5e9', label: label }
  const displayLabel = meta.label

  return (
    <div className="flex items-center gap-3 group">
      <span className="text-xs text-zinc-600 w-24 shrink-0">{displayLabel}</span>

      <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{
            duration: 0.8,
            delay: 0.3 + delay,
            ease: [0.19, 1, 0.22, 1],
          }}
          style={{
            backgroundColor: meta.color,
            boxShadow: `0 0 8px ${meta.color}60`,
          }}
        />
      </div>

      <motion.span
        className="text-xs font-mono text-zinc-500 w-7 text-right"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 + delay }}
      >
        {score}
      </motion.span>
    </div>
  )
}
