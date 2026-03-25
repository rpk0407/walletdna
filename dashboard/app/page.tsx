import { WalletSearch } from '@/components/WalletSearch'

export default function HomePage() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-4">
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold tracking-tight mb-4">
          Wallet<span className="text-sky-500">DNA</span>
        </h1>
        <p className="text-xl text-gray-400 max-w-lg">
          Myers-Briggs for Wallets. Discover your on-chain personality.
        </p>
      </div>

      <WalletSearch />

      <div className="mt-20 grid grid-cols-2 md:grid-cols-3 gap-6 max-w-2xl w-full text-center">
        {ARCHETYPES.map((a) => (
          <div key={a.name} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <div className="text-3xl mb-2">{a.emoji}</div>
            <div className="font-semibold text-sm">{a.label}</div>
            <div className="text-xs text-gray-500 mt-1">{a.description}</div>
          </div>
        ))}
      </div>
    </main>
  )
}

const ARCHETYPES = [
  { name: 'sniper', emoji: '\uD83D\uDC3A', label: 'The Sniper', description: 'Fast entry, quick exit' },
  { name: 'conviction_holder', emoji: '\uD83D\uDC8E', label: 'Conviction Holder', description: 'Long holds, high confidence' },
  { name: 'degen', emoji: '\uD83C\uDFB0', label: 'The Degen', description: 'High frequency, new tokens' },
  { name: 'researcher', emoji: '\uD83E\uDDE0', label: 'The Researcher', description: 'Protocol diversity, early adopter' },
  { name: 'follower', emoji: '\uD83D\uDC11', label: 'The Follower', description: 'Mirrors whale wallets' },
  { name: 'extractor', emoji: '\uD83D\uDD77', label: 'The Extractor', description: 'Sybil patterns, airdrop farming' },
]
