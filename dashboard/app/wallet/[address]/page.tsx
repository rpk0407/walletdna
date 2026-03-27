import { Suspense } from 'react'
import Link from 'next/link'
import { PersonalityCard } from '@/components/PersonalityCard'
import { RadarChart } from '@/components/RadarChart'
import { BehavioralTimeline } from '@/components/BehavioralTimeline'
import { TransactionHeatmap } from '@/components/TransactionHeatmap'
import { api } from '@/lib/api'

interface Props {
  params: { address: string }
  searchParams: { chain?: string }
}

export async function generateMetadata({ params }: Props) {
  return {
    title: `${params.address.slice(0, 8)}... — WalletDNA`,
    openGraph: {
      images: [`/api/og?address=${params.address}`],
    },
  }
}

// Bento skeleton tile
function SkeletonTile({ className }: { className?: string }) {
  return (
    <div className={`rounded-3xl overflow-hidden ${className}`}>
      <div className="skeleton h-full w-full min-h-[180px] rounded-3xl" />
    </div>
  )
}

// Section heading
function BentoLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[10px] font-semibold text-zinc-600 uppercase tracking-widest mb-4">
      {children}
    </h3>
  )
}

// Bento tile wrapper
function BentoTile({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={`rounded-3xl p-5 ${className}`}
      style={{
        background: 'rgba(255,255,255,0.03)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      {children}
    </div>
  )
}

export default async function WalletProfilePage({ params, searchParams }: Props) {
  const chain = (searchParams.chain ?? 'solana') as
    | 'solana'
    | 'ethereum'
    | 'base'
    | 'arbitrum'
  const profile = await api.getProfile(params.address, chain).catch(() => null)

  if (!profile) {
    return (
      <main className="flex items-center justify-center min-h-screen px-4">
        <div className="text-center glass rounded-3xl p-10 max-w-sm">
          <div className="text-4xl mb-4">🔍</div>
          <h2 className="text-lg font-semibold text-zinc-200">Profile unavailable</h2>
          <p className="text-zinc-500 text-sm mt-2">
            This wallet may have insufficient transaction history.
          </p>
          <Link
            href="/"
            className="inline-block mt-5 text-sm text-sky-500 hover:text-sky-400 transition-colors"
          >
            ← Try another wallet
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      {/* Back link */}
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs text-zinc-600 hover:text-zinc-400 transition-colors mb-6"
      >
        ← WalletDNA
      </Link>

      {/* Bento grid */}
      <div className="grid grid-cols-1 gap-3">
        {/* Row 1: Full-width personality card */}
        <PersonalityCard profile={profile} />

        {/* Row 2: Radar + Heatmap side by side */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <BentoTile>
            <BentoLabel>Behavioral Dimensions</BentoLabel>
            <Suspense fallback={<SkeletonTile className="h-[240px]" />}>
              <RadarChart dimensions={profile.dimensions} />
            </Suspense>
          </BentoTile>

          <BentoTile>
            <BentoLabel>Activity Heatmap</BentoLabel>
            <Suspense fallback={<SkeletonTile className="h-[180px]" />}>
              <TransactionHeatmap
                address={profile.address}
                chain={profile.chain}
              />
            </Suspense>
          </BentoTile>
        </div>

        {/* Row 3: Timeline full width */}
        <BentoTile>
          <BentoLabel>Archetype Evolution</BentoLabel>
          <Suspense
            fallback={
              <div className="skeleton h-24 rounded-2xl" />
            }
          >
            <BehavioralTimeline
              address={profile.address}
              chain={profile.chain}
            />
          </Suspense>
        </BentoTile>
      </div>
    </main>
  )
}
