interface Props {
  label: string
  score: number  // 0-100
}

const DIMENSION_COLORS: Record<string, string> = {
  speed: '#ef4444',
  conviction: '#3b82f6',
  risk_appetite: '#f59e0b',
  sophistication: '#8b5cf6',
  originality: '#10b981',
  consistency: '#6b7280',
}

export function DimensionBar({ label, score }: Props) {
  const color = DIMENSION_COLORS[label] ?? '#0ea5e9'
  const display = label.replace('_', ' ')

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-400 w-28 capitalize shrink-0">{display}</span>
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs text-gray-400 w-8 text-right">{score}</span>
    </div>
  )
}
