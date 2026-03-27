'use client'

import {
  RadarChart as RechartsRadar,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts'
import type { Dimensions } from '@/lib/types'

interface Props {
  dimensions: Dimensions
}

export function RadarChart({ dimensions }: Props) {
  const data = [
    { subject: 'Speed', value: dimensions.speed },
    { subject: 'Conviction', value: dimensions.conviction },
    { subject: 'Risk', value: dimensions.risk_appetite },
    { subject: 'Sophist.', value: dimensions.sophistication },
    { subject: 'Originality', value: dimensions.originality },
    { subject: 'Consistency', value: dimensions.consistency },
  ]

  return (
    <ResponsiveContainer width="100%" height={240}>
      <RechartsRadar data={data}>
        <PolarGrid
          stroke="rgba(255,255,255,0.06)"
          strokeDasharray="3 3"
        />
        <PolarAngleAxis
          dataKey="subject"
          tick={{
            fill: 'rgba(255,255,255,0.35)',
            fontSize: 10,
            fontFamily: 'var(--font-inter)',
          }}
          tickLine={false}
        />
        <Radar
          name="dimensions"
          dataKey="value"
          stroke="#0ea5e9"
          fill="#0ea5e9"
          fillOpacity={0.12}
          strokeWidth={1.5}
          dot={{ fill: '#0ea5e9', r: 3, strokeWidth: 0 }}
        />
      </RechartsRadar>
    </ResponsiveContainer>
  )
}
