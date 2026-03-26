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
    { subject: 'Sophistication', value: dimensions.sophistication },
    { subject: 'Originality', value: dimensions.originality },
    { subject: 'Consistency', value: dimensions.consistency },
  ]

  return (
    <ResponsiveContainer width="100%" height={240}>
      <RechartsRadar data={data}>
        <PolarGrid stroke="#374151" />
        <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 11 }} />
        <Radar
          name="dimensions"
          dataKey="value"
          stroke="#0ea5e9"
          fill="#0ea5e9"
          fillOpacity={0.2}
          strokeWidth={2}
        />
      </RechartsRadar>
    </ResponsiveContainer>
  )
}
