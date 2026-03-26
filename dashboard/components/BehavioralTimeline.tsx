'use client'

import { useEffect, useState } from 'react'
import type { Chain, TimelineEntry } from '@/lib/types'
import { api } from '@/lib/api'
import { ARCHETYPE_META } from '@/lib/types'

interface Props {
  address: string
  chain: Chain
}

export function BehavioralTimeline({ address, chain }: Props) {
  const [entries, setEntries] = useState<TimelineEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getTimeline(address, chain)
      .then((t) => setEntries(t.timeline))
      .catch(() => setEntries([]))
      .finally(() => setLoading(false))
  }, [address, chain])

  if (loading) return <div className="h-24 animate-pulse bg-gray-800 rounded-xl" />
  if (!entries.length) return <div className="text-gray-500 text-sm">No timeline data yet.</div>

  return (
    <div className="flex items-end gap-1 h-24 overflow-x-auto">
      {entries.map((entry, i) => {
        const meta = ARCHETYPE_META[entry.archetype as keyof typeof ARCHETYPE_META]
        return (
          <div
            key={i}
            className="flex flex-col items-center gap-1 shrink-0"
            title={`${entry.archetype} \u2014 ${new Date(entry.recorded_at).toLocaleDateString()}`}
          >
            <span className="text-xs">{meta?.emoji ?? '\u2753'}</span>
            <div className="w-2 rounded-t" style={{ height: '40px', backgroundColor: meta?.color ?? '#6b7280' }} />
          </div>
        )
      })}
    </div>
  )
}
