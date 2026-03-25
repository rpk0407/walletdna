'use client'

interface Props {
  address: string
  chain: string
}

// 7 days x 24 hours heatmap placeholder
export function TransactionHeatmap({ address, chain }: Props) {
  // TODO: fetch hourly activity data from /v1/wallet/{address}/activity
  const hours = Array.from({ length: 24 }, (_, h) => h)
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-1">
        <div className="flex flex-col gap-1 pt-5">
          {days.map((d) => (
            <div key={d} className="text-xs text-gray-500 h-4 flex items-center">{d}</div>
          ))}
        </div>
        <div className="flex flex-col gap-1">
          <div className="flex gap-1">
            {hours.map((h) => (
              <div key={h} className="text-xs text-gray-600 w-4 text-center">{h % 6 === 0 ? h : ''}</div>
            ))}
          </div>
          {days.map((d) => (
            <div key={d} className="flex gap-1">
              {hours.map((h) => {
                const intensity = Math.random()  // Replace with real data
                return (
                  <div
                    key={h}
                    className="w-4 h-4 rounded-sm"
                    style={{ backgroundColor: `rgba(14, 165, 233, ${intensity * 0.8})` }}
                  />
                )
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
