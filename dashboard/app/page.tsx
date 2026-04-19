'use client'

import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'
import { WalletSearch } from '@/components/WalletSearch'
import {
  Zap,
  ScanLine,
  BarChart3,
  Globe,
  ShieldCheck,
  ArrowRight,
  Check,
} from 'lucide-react'

// ─── Data ────────────────────────────────────────────────────────────────────

const STATS = [
  { value: '50K+', label: 'Wallets analyzed' },
  { value: '6', label: 'Archetypes' },
  { value: '4', label: 'Chains supported' },
  { value: '< 8s', label: 'Analysis time' },
]

const HOW_IT_WORKS = [
  {
    icon: ScanLine,
    step: '01',
    title: 'Paste any wallet',
    body: 'Drop a Solana, Ethereum, Base, or Arbitrum address. No sign-up, no KYC — just a wallet.',
  },
  {
    icon: BarChart3,
    step: '02',
    title: 'AI analyzes behavior',
    body: 'Our LangGraph pipeline ingests transactions, extracts 6 behavioral dimensions, and runs HDBSCAN clustering.',
  },
  {
    icon: Zap,
    step: '03',
    title: 'Get your archetype',
    body: 'Receive a complete personality profile with confidence score, behavioral radar, and a shareable card.',
  },
]

const ARCHETYPES = [
  {
    name: 'sniper',
    emoji: '🐺',
    label: 'The Sniper',
    description: 'Enters fast, exits faster. Precision timing on token launches with minimal holding periods.',
    traits: ['High entry speed', 'Low hold duration', 'Precise execution'],
    color: '#ef4444',
    dim: 'speed · precision',
  },
  {
    name: 'conviction_holder',
    emoji: '💎',
    label: 'Conviction Holder',
    description: 'Buys and holds with high confidence. Rarely trades, but when they do — it counts.',
    traits: ['Long hold periods', 'Low frequency', 'High conviction'],
    color: '#3b82f6',
    dim: 'conviction · patience',
  },
  {
    name: 'degen',
    emoji: '🎰',
    label: 'The Degen',
    description: 'Maximum frequency, maximum chaos. First into new tokens, high risk, high reward.',
    traits: ['Extreme frequency', 'New token bias', 'High risk appetite'],
    color: '#f59e0b',
    dim: 'risk · frequency',
  },
  {
    name: 'researcher',
    emoji: '🧠',
    label: 'The Researcher',
    description: 'Protocol diversity signals deep ecosystem knowledge. Early adopter, not a follower.',
    traits: ['Protocol diversity', 'Early adoption', 'Sophisticated'],
    color: '#8b5cf6',
    dim: 'sophistication · originality',
  },
  {
    name: 'follower',
    emoji: '👑',
    label: 'The Follower',
    description: 'Mirrors whale wallets with a 3–72h lag. High token overlap with known influencers.',
    traits: ['Whale shadowing', 'Delayed entry', 'Token overlap'],
    color: '#6b7280',
    dim: 'consistency · mimicry',
  },
  {
    name: 'extractor',
    emoji: '🕷',
    label: 'The Extractor',
    description: 'Airdrop farmer. Sybil cluster patterns, coordinated fund flows, multi-wallet behavior.',
    traits: ['Sybil patterns', 'Airdrop focus', 'Cluster behavior'],
    color: '#dc2626',
    dim: 'extraction · scale',
  },
]

const PRICING = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'For curious traders',
    features: ['5 wallet lookups / day', '4 chains supported', 'Personality card', 'Shareable profile link'],
    cta: 'Get started',
    highlighted: false,
  },
  {
    name: 'Pro',
    price: '$29',
    period: 'per month',
    description: 'For serious analysts',
    features: [
      'Unlimited wallet lookups',
      'Historical archetype tracking',
      'Wallet watchlist & alerts',
      'Bulk batch analysis (CSV)',
      'Priority processing',
      'API access (100K calls/mo)',
    ],
    cta: 'Start free trial',
    highlighted: true,
  },
  {
    name: 'Team',
    price: '$99',
    period: 'per month',
    description: 'For funds & research teams',
    features: [
      'Everything in Pro',
      '5 team seats',
      'Unlimited API access',
      'Custom archetype weights',
      'White-label reports',
      'Slack & webhook alerts',
    ],
    cta: 'Contact us',
    highlighted: false,
  },
]

// ─── Animation helpers ────────────────────────────────────────────────────────

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.19, 1, 0.22, 1] } },
}

const stagger = (delay = 0.08) => ({
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: delay } },
})

function FadeUp({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode
  delay?: number
  className?: string
}) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })
  return (
    <motion.div
      ref={ref}
      variants={fadeUp}
      initial="hidden"
      animate={inView ? 'show' : 'hidden'}
      transition={{ delay }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-600 mb-3">
      {children}
    </p>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function HomePage() {
  const archetypesRef = useRef(null)
  const archetypesInView = useInView(archetypesRef, { once: true, margin: '-80px' })

  return (
    <main className="relative overflow-x-hidden">
      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center px-5 pt-20 pb-16 text-center">
        {/* Background glow */}
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[500px] rounded-full opacity-30 blur-[120px] bg-sky-600/20" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.19, 1, 0.22, 1] }}
          className="inline-flex items-center gap-2 glass px-4 py-2 rounded-full mb-8"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse-glow" />
          <span className="text-[11px] font-medium text-zinc-400 tracking-wide">
            On-chain Personality Intelligence
          </span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, delay: 0.08, ease: [0.19, 1, 0.22, 1] }}
          className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.05] mb-5 max-w-3xl"
        >
          Your Wallet Has{' '}
          <span className="text-gradient-dna">a Personality.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.18, ease: [0.19, 1, 0.22, 1] }}
          className="text-base sm:text-lg text-zinc-500 max-w-md mb-10 leading-relaxed"
        >
          Paste any wallet address. Get your on-chain archetype in seconds — powered by behavioral AI, not hype.
        </motion.p>

        {/* Search */}
        <motion.div
          id="search"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.28, ease: [0.19, 1, 0.22, 1] }}
          className="w-full max-w-xl"
        >
          <WalletSearch />
        </motion.div>

        {/* Trust chips */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.5 }}
          className="flex flex-wrap items-center justify-center gap-3 mt-8"
        >
          {['No sign-up', 'No KYC', '100% on-chain data', 'Free to start'].map((t) => (
            <span
              key={t}
              className="flex items-center gap-1.5 text-[11px] text-zinc-600"
            >
              <Check className="w-3 h-3 text-sky-600 shrink-0" />
              {t}
            </span>
          ))}
        </motion.div>
      </section>

      {/* ── Stats strip ───────────────────────────────────────────────────── */}
      <section className="border-y border-white/6">
        <div className="max-w-4xl mx-auto px-5 py-10 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {STATS.map((s, i) => (
            <FadeUp key={s.label} delay={i * 0.06}>
              <div className="text-3xl font-bold text-zinc-100 tracking-tight">{s.value}</div>
              <div className="text-xs text-zinc-600 mt-1">{s.label}</div>
            </FadeUp>
          ))}
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────────────────── */}
      <section id="how-it-works" className="max-w-4xl mx-auto px-5 py-24">
        <FadeUp className="text-center mb-14">
          <SectionLabel>How it works</SectionLabel>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-zinc-100">
            Behavioral analysis, <span className="text-zinc-500">not guesswork</span>
          </h2>
        </FadeUp>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {HOW_IT_WORKS.map((step, i) => (
            <FadeUp key={step.step} delay={i * 0.1}>
              <div
                className="relative glass rounded-2xl p-6 h-full"
                style={{ borderColor: 'rgba(255,255,255,0.07)' }}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-9 h-9 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center shrink-0">
                    <step.icon className="w-4 h-4 text-sky-400" />
                  </div>
                  <span className="text-xs font-mono text-zinc-700">{step.step}</span>
                </div>
                <h3 className="text-sm font-semibold text-zinc-200 mb-2">{step.title}</h3>
                <p className="text-sm text-zinc-600 leading-relaxed">{step.body}</p>

                {i < 2 && (
                  <div className="hidden md:flex absolute top-1/2 -right-6 -translate-y-1/2 z-10">
                    <ArrowRight className="w-3 h-3 text-zinc-700" />
                  </div>
                )}
              </div>
            </FadeUp>
          ))}
        </div>
      </section>

      {/* ── Archetypes showcase ───────────────────────────────────────────── */}
      <section id="archetypes" className="max-w-5xl mx-auto px-5 py-24">
        <FadeUp className="text-center mb-14">
          <SectionLabel>The 6 archetypes</SectionLabel>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-zinc-100">
            Which one are you?
          </h2>
          <p className="text-sm text-zinc-600 mt-3 max-w-md mx-auto">
            Every wallet is classified into one primary archetype based on 6 behavioral dimensions scored 0–100.
          </p>
        </FadeUp>

        <motion.div
          ref={archetypesRef}
          variants={stagger(0.07)}
          initial="hidden"
          animate={archetypesInView ? 'show' : 'hidden'}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {ARCHETYPES.map((a) => (
            <motion.div
              key={a.name}
              variants={fadeUp}
              whileHover={{ y: -3, transition: { duration: 0.2 } }}
              className="group relative glass rounded-2xl p-5 cursor-default overflow-hidden"
            >
              {/* Color accent top line */}
              <div
                className="absolute top-0 left-0 right-0 h-px"
                style={{
                  background: `linear-gradient(90deg, transparent, ${a.color}60, transparent)`,
                }}
              />
              {/* Hover glow */}
              <div
                className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-2xl"
                style={{
                  background: `radial-gradient(circle at 30% 0%, ${a.color}10 0%, transparent 60%)`,
                }}
              />

              <div className="flex items-start justify-between mb-4 relative">
                <span className="text-3xl">{a.emoji}</span>
                <span
                  className="text-[10px] font-mono px-2 py-0.5 rounded-full"
                  style={{
                    color: a.color,
                    background: `${a.color}15`,
                    border: `1px solid ${a.color}30`,
                  }}
                >
                  {a.dim}
                </span>
              </div>

              <h3
                className="text-sm font-bold mb-1.5 relative"
                style={{ color: a.color }}
              >
                {a.label}
              </h3>
              <p className="text-xs text-zinc-500 leading-relaxed mb-4 relative">
                {a.description}
              </p>

              <div className="flex flex-wrap gap-1.5 relative">
                {a.traits.map((t) => (
                  <span
                    key={t}
                    className="text-[10px] text-zinc-600 border border-white/6 rounded-full px-2 py-0.5"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* ── Pricing ───────────────────────────────────────────────────────── */}
      <section id="pricing" className="max-w-5xl mx-auto px-5 py-24">
        <FadeUp className="text-center mb-14">
          <SectionLabel>Pricing</SectionLabel>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-zinc-100">
            Simple, transparent pricing
          </h2>
          <p className="text-sm text-zinc-600 mt-3">
            Start free. Upgrade when you need more.
          </p>
        </FadeUp>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PRICING.map((plan, i) => (
            <FadeUp key={plan.name} delay={i * 0.08}>
              <div
                className="relative rounded-2xl p-6 h-full flex flex-col"
                style={
                  plan.highlighted
                    ? {
                        background: 'rgba(14,165,233,0.06)',
                        border: '1px solid rgba(14,165,233,0.25)',
                        boxShadow: '0 0 40px rgba(14,165,233,0.08)',
                      }
                    : {
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(255,255,255,0.07)',
                      }
                }
              >
                {plan.highlighted && (
                  <div className="absolute -top-px left-1/2 -translate-x-1/2 px-4 py-0.5 bg-sky-500 rounded-full text-[10px] font-semibold text-white">
                    Most popular
                  </div>
                )}

                <div className="mb-5">
                  <p className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-1">
                    {plan.name}
                  </p>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-4xl font-bold text-zinc-100 tracking-tight">
                      {plan.price}
                    </span>
                    <span className="text-xs text-zinc-600">/{plan.period}</span>
                  </div>
                  <p className="text-xs text-zinc-600 mt-1.5">{plan.description}</p>
                </div>

                <ul className="space-y-2.5 flex-1 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-xs text-zinc-400">
                      <Check
                        className="w-3 h-3 mt-0.5 shrink-0"
                        style={{ color: plan.highlighted ? '#0ea5e9' : '#3f3f46' }}
                      />
                      {f}
                    </li>
                  ))}
                </ul>

                <button
                  className="w-full py-2.5 rounded-xl text-sm font-semibold transition-all duration-200"
                  style={
                    plan.highlighted
                      ? {
                          background: '#0ea5e9',
                          color: '#fff',
                          boxShadow: '0 0 20px rgba(14,165,233,0.3)',
                        }
                      : {
                          background: 'rgba(255,255,255,0.06)',
                          color: '#a1a1aa',
                          border: '1px solid rgba(255,255,255,0.08)',
                        }
                  }
                >
                  {plan.cta}
                </button>
              </div>
            </FadeUp>
          ))}
        </div>
      </section>

      {/* ── CTA banner ────────────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-5 py-16 text-center">
        <FadeUp>
          <div
            className="rounded-3xl p-10 relative overflow-hidden"
            style={{
              background: 'rgba(14,165,233,0.05)',
              border: '1px solid rgba(14,165,233,0.15)',
            }}
          >
            <div className="pointer-events-none absolute inset-0 -z-10">
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full blur-3xl bg-sky-600/15" />
            </div>
            <Globe className="w-8 h-8 text-sky-500 mx-auto mb-4 opacity-80" />
            <h2 className="text-2xl sm:text-3xl font-bold text-zinc-100 tracking-tight mb-3">
              Ready to see your on-chain DNA?
            </h2>
            <p className="text-sm text-zinc-500 mb-6 max-w-sm mx-auto">
              Free for the first 5 wallets per day. No account required.
            </p>
            <a
              href="#search"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-sky-500 hover:bg-sky-400 text-white text-sm font-semibold transition-colors duration-150"
              style={{ boxShadow: '0 0 24px rgba(14,165,233,0.3)' }}
            >
              Analyze a wallet
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </FadeUp>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/6 mt-8">
        <div className="max-w-5xl mx-auto px-5 py-10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="text-sm font-semibold text-zinc-700">
            Wallet<span className="text-gradient-dna">DNA</span>
          </span>
          <div className="flex items-center gap-6">
            {['Privacy', 'Terms', 'API Docs', 'GitHub'].map((l) => (
              <a
                key={l}
                href="#"
                className="text-xs text-zinc-700 hover:text-zinc-500 transition-colors duration-150"
              >
                {l}
              </a>
            ))}
          </div>
          <p className="text-xs text-zinc-800">© 2025 WalletDNA</p>
        </div>
      </footer>
    </main>
  )
}
