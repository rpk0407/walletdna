'use client'

import { motion } from 'framer-motion'
import { WalletSearch } from '@/components/WalletSearch'

const ARCHETYPES = [
  {
    name: 'sniper',
    emoji: '🐺',
    label: 'The Sniper',
    description: 'Fast entry, quick exit',
    color: '#ef4444',
  },
  {
    name: 'conviction_holder',
    emoji: '💎',
    label: 'Conviction Holder',
    description: 'Long holds, high confidence',
    color: '#3b82f6',
  },
  {
    name: 'degen',
    emoji: '🎰',
    label: 'The Degen',
    description: 'High frequency, new tokens',
    color: '#f59e0b',
  },
  {
    name: 'researcher',
    emoji: '🧠',
    label: 'The Researcher',
    description: 'Protocol diversity, early adopter',
    color: '#8b5cf6',
  },
  {
    name: 'follower',
    emoji: '👑',
    label: 'The Follower',
    description: 'Mirrors whale wallets',
    color: '#6b7280',
  },
  {
    name: 'extractor',
    emoji: '🕷',
    label: 'The Extractor',
    description: 'Sybil patterns, airdrop farming',
    color: '#dc2626',
  },
]

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.6 },
  },
}

const cardItem = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.4, ease: [0.19, 1, 0.22, 1] },
  },
}

export default function HomePage() {
  return (
    <main className="relative flex flex-col items-center justify-center min-h-screen px-4 overflow-hidden">
      {/* Background glow orb */}
      <div className="pointer-events-none absolute top-[-200px] left-1/2 -translate-x-1/2 w-[700px] h-[400px] rounded-full bg-sky-500/5 blur-3xl" />

      {/* Hero */}
      <div className="text-center mb-14 z-10">
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.19, 1, 0.22, 1] }}
          className="inline-flex items-center gap-2 text-xs font-medium text-zinc-500 border border-white/8 rounded-full px-4 py-1.5 mb-6 glass"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse-glow" />
          On-chain Personality Intelligence
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1, ease: [0.19, 1, 0.22, 1] }}
          className="text-6xl sm:text-7xl font-bold tracking-tight mb-5 leading-none"
        >
          Wallet
          <span className="text-gradient-dna">DNA</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2, ease: [0.19, 1, 0.22, 1] }}
          className="text-lg text-zinc-500 max-w-md mx-auto leading-relaxed"
        >
          Myers-Briggs for Wallets.
          <br />
          Discover your on-chain personality.
        </motion.p>
      </div>

      {/* Search */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.35, ease: [0.19, 1, 0.22, 1] }}
        className="z-10 w-full"
      >
        <WalletSearch />
      </motion.div>

      {/* Archetypes grid */}
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="mt-16 grid grid-cols-2 md:grid-cols-3 gap-3 max-w-2xl w-full z-10"
      >
        {ARCHETYPES.map((a) => (
          <motion.div
            key={a.name}
            variants={cardItem}
            whileHover={{
              scale: 1.03,
              transition: { duration: 0.2, ease: [0.19, 1, 0.22, 1] },
            }}
            className="group relative glass rounded-2xl p-4 text-center cursor-default overflow-hidden"
            style={{ '--archetype-color': a.color } as React.CSSProperties}
          >
            {/* Hover glow */}
            <div
              className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl"
              style={{
                background: `radial-gradient(circle at 50% 0%, ${a.color}15 0%, transparent 70%)`,
              }}
            />
            {/* Top border accent */}
            <div
              className="absolute top-0 left-1/2 -translate-x-1/2 w-16 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              style={{ background: `linear-gradient(90deg, transparent, ${a.color}, transparent)` }}
            />

            <div className="text-3xl mb-2 relative">{a.emoji}</div>
            <div className="font-semibold text-sm text-zinc-200 relative">{a.label}</div>
            <div className="text-xs text-zinc-600 mt-1 relative">{a.description}</div>
          </motion.div>
        ))}
      </motion.div>

      {/* Bottom fade */}
      <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent" />
    </main>
  )
}
