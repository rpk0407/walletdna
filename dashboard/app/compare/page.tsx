import { api } from '@/lib/api'
import { PersonalityCard } from '@/components/PersonalityCard'
import { RadarChart } from '@/components/RadarChart'

export default async function ComparePage({
  searchParams,
}: {
  searchParams: { a?: string; b?: string; chain?: string }
}) {
  const chain = (searchParams.chain ?? 'solana') as 'solana' | 'ethereum' | 'base' | 'arbitrum'
  const addressA = searchParams.a
  const addressB = searchParams.b

  if (!addressA || !addressB) {
    return (
      <main className="max-w-2xl mx-auto px-4 py-12 text-center">
        <h1 className="text-2xl font-bold mb-4">Compare Wallets</h1>
        <p className="text-gray-400">Provide <code>?a=ADDRESS_A&b=ADDRESS_B</code> query params.</p>
      </main>
    )
  }

  const [profileA, profileB] = await Promise.all([
    api.getProfile(addressA, chain).catch(() => null),
    api.getProfile(addressB, chain).catch(() => null),
  ])

  return (
    <main className="max-w-5xl mx-auto px-4 py-12">
      <h1 className="text-2xl font-bold mb-8 text-center">Wallet Comparison</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {profileA ? <PersonalityCard profile={profileA} /> : <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 text-gray-500">Wallet A not found</div>}
        {profileB ? <PersonalityCard profile={profileB} /> : <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 text-gray-500">Wallet B not found</div>}
      </div>

      {profileA && profileB && (
        <div className="mt-8 grid grid-cols-2 gap-6">
          <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
            <RadarChart dimensions={profileA.dimensions} />
          </div>
          <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
            <RadarChart dimensions={profileB.dimensions} />
          </div>
        </div>
      )}
    </main>
  )
}
