'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'

const NAV_LINKS = [
  { href: '/#how-it-works', label: 'How it works' },
  { href: '/#archetypes', label: 'Archetypes' },
  { href: '/#pricing', label: 'Pricing' },
]

export function NavBar() {
  const pathname = usePathname()
  const isHome = pathname === '/'

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.19, 1, 0.22, 1] }}
      className="fixed top-0 left-0 right-0 z-50"
      style={{
        background: 'rgba(0,0,0,0.75)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      <div className="max-w-5xl mx-auto px-5 h-14 flex items-center justify-between gap-6">
        {/* Logo */}
        <Link href="/" className="shrink-0">
          <span className="text-sm font-bold tracking-tight text-zinc-100">
            Wallet<span className="text-gradient-dna">DNA</span>
          </span>
        </Link>

        {/* Nav links — hidden on mobile */}
        {isHome && (
          <nav className="hidden md:flex items-center gap-7 flex-1 justify-center">
            {NAV_LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="text-xs font-medium text-zinc-500 hover:text-zinc-300 transition-colors duration-150"
              >
                {l.label}
              </a>
            ))}
          </nav>
        )}

        {/* CTA */}
        <div className="flex items-center gap-3 shrink-0">
          {!isHome && (
            <Link
              href="/"
              className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors duration-150"
            >
              ← Home
            </Link>
          )}
          <a
            href="#search"
            className="hidden sm:inline-flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-white transition-colors duration-150"
            style={{ boxShadow: '0 0 20px rgba(14,165,233,0.25)' }}
          >
            Analyze Wallet
          </a>
        </div>
      </div>
    </motion.header>
  )
}
