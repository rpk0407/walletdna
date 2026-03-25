import { Suspense } from 'react'
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

export default async function WalletProfilePage({ params, searchParams }: Props) {
  const chain = (searchParams.chain ?? 'solana') as 'solana' | 'ethereum' | 'base' | 'arbitrum'
  const profile = await api.getProfile(params.address, chain).catch(() => null)

  if (!profile) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-4xl mb-4">\u274C</div>
          <h2 className="text-xl font-semibold">Profile not available</h2>
          <p className="text-gray-500 mt-2">This wallet may have insufficient transaction history.</p>
        </div>
      </main>
    )
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-12">
      <PersonalityCard profile={profile} />

      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Behavioral Dimensions</h3>
          <RadarChart dimensions={profile.dimensions} />
        </div>

        <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Activity Heatmap</h3>
          <TransactionHeatmap address={profile.address} chain={profile.chain} />
        </div>
      </div>

      <div className="mt-6 bg-gray-900 rounded-2xl p-6 border border-gray-800">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Archetype Evolution</h3>
        <Suspense fallback={<div className="h-48 animate-pulse bg-gray-800 rounded-xl" />}>
          <BehavioralTimeline address={profile.address} chain={profile.chain} />
        </Suspense>
      </div>
    </main>
  )
}
