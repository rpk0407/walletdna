'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { ActivityCell, Chain } from '@/lib/types'

interface Props {
  address: string
  chain: Chain
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const HOURS = Array.from({ length: 24 }, (_, h) => h)

function getColor(intensity: number): string {
  if (intensity === 0) return 'rgba(255,255,255,0.05)'
  // Sky-blue gradient: low → bright
  return `rgba(14, 165, 233, ${0.15 + intensity * 0.85})`
}

export function TransactionHeatmap({ address, chain }: Props) {
  const [cellMap, setCellMap] = useState<Map<string, ActivityCell>>(new Map())
  const [peakHour, setPeakHour] = useState<number | null>(null)
  const [peakDay, setPeakDay] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    api.getActivity(address, chain)
      .then((data) => {
        if (cancelled) return
        const map = new Map<string, ActivityCell>()
        for (const cell of data.cells) {
          map.set(`${cell.day}-${cell.hour}`, cell)
        }
        setCellMap(map)
        setPeakHour(data.peak_hour)
        setPeakDay(data.peak_day)
      })
      .catch(() => {
        // Silently fail — grid stays empty/zero
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [address, chain])

  if (loading) {
    return <div className="h-36 animate-pulse rounded-lg bg-gray-800" />
  }

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-1 min-w-max">
        {/* Day labels */}
        <div className="flex flex-col gap-1 pt-5 pr-1">
          {DAYS.map((d, i) => (
            <div
              key={d}
              className={`text-xs h-4 flex items-center w-7 ${
                i === peakDay ? 'text-sky-400 font-semibold' : 'text-gray-500'
              }`}
            >
              {d}
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-1">
          {/* Hour labels */}
          <div className="flex gap-1">
            {HOURS.map((h) => (
              <div
                key={h}
                className={`text-xs w-4 text-center ${
                  h === peakHour ? 'text-sky-400 font-semibold' : 'text-gray-600'
                }`}
              >
                {h % 6 === 0 ? h : ''}
              </div>
            ))}
          </div>

          {/* Grid */}
          {DAYS.map((_, dayIdx) => (
            <div key={dayIdx} className="flex gap-1">
              {HOURS.map((hour) => {
                const cell = cellMap.get(`${dayIdx}-${hour}`)
                const intensity = cell?.intensity ?? 0
                const count = cell?.count ?? 0
                return (
                  <div
                    key={hour}
                    title={`${DAYS[dayIdx]} ${hour}:00 UTC — ${count} txns`}
                    className="w-4 h-4 rounded-sm cursor-default transition-opacity hover:opacity-80"
                    style={{ backgroundColor: getColor(intensity) }}
                  />
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-2 mt-3">
        <span className="text-xs text-gray-600">Low</span>
        <div className="flex gap-0.5">
          {[0, 0.2, 0.4, 0.6, 0.8, 1.0].map((v) => (
            <div
              key={v}
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: getColor(v) }}
            />
          ))}
        </div>
        <span className="text-xs text-gray-600">High</span>
      </div>
    </div>
  )
}
