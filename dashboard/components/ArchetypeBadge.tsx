import type { ArchetypeName } from '@/lib/types'
import { ARCHETYPE_META } from '@/lib/types'
import { clsx } from 'clsx'

interface Props {
  archetype: ArchetypeName
  size?: 'sm' | 'md' | 'lg'
}

export function ArchetypeBadge({ archetype, size = 'md' }: Props) {
  const meta = ARCHETYPE_META[archetype]

  return (
    <div className={clsx('flex items-center gap-2', size === 'lg' && 'gap-3')}>
      <span className={clsx(size === 'sm' && 'text-xl', size === 'md' && 'text-2xl', size === 'lg' && 'text-4xl')}>
        {meta.emoji}
      </span>
      <div>
        <div
          className={clsx(
            'font-bold',
            size === 'sm' && 'text-sm',
            size === 'md' && 'text-base',
            size === 'lg' && 'text-2xl',
          )}
          style={{ color: meta.color }}
        >
          {meta.label}
        </div>
        <div className={clsx('text-gray-500', size === 'sm' && 'text-xs', size === 'md' && 'text-xs', size === 'lg' && 'text-sm')}>
          {archetype.replace('_', ' ')}
        </div>
      </div>
    </div>
  )
}
