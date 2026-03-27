'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Search, ChevronDown, Loader2 } from 'lucide-react'

const CHAINS = [
  { value: 'solana', label: 'SOL' },
  { value: 'ethereum', label: 'ETH' },
  { value: 'base', label: 'BASE' },
  { value: 'arbitrum', label: 'ARB' },
]

export function WalletSearch() {
  const [address, setAddress] = useState('')
  const [chain, setChain] = useState('solana')
  const [loading, setLoading] = useState(false)
  const [focused, setFocused] = useState(false)
  const router = useRouter()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = address.trim()
    if (!trimmed) return
    setLoading(true)
    router.push(`/wallet/${trimmed}?chain=${chain}`)
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-xl mx-auto">
      {/* Pill-shaped floating bar */}
      <div
        className="relative flex items-center glass-md rounded-2xl transition-all duration-300"
        style={{
          boxShadow: focused
            ? '0 0 0 1px rgba(14,165,233,0.5), 0 0 24px rgba(14,165,233,0.15), 0 8px 32px rgba(0,0,0,0.4)'
            : '0 0 0 1px rgba(255,255,255,0.06), 0 8px 32px rgba(0,0,0,0.3)',
        }}
      >
        {/* Search icon */}
        <div className="pl-4 pr-2 text-zinc-500 shrink-0">
          <Search className="w-4 h-4" />
        </div>

        {/* Address input */}
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Paste any wallet address..."
          className="flex-1 bg-transparent py-3.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none min-w-0"
        />

        {/* Chain selector */}
        <div className="relative shrink-0 px-2">
          <div className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white/5 border border-white/8 cursor-pointer hover:bg-white/8 transition-colors">
            <select
              value={chain}
              onChange={(e) => setChain(e.target.value)}
              className="bg-transparent text-xs font-medium text-zinc-400 focus:outline-none cursor-pointer appearance-none pr-4"
            >
              {CHAINS.map((c) => (
                <option key={c.value} value={c.value} className="bg-zinc-900">
                  {c.label}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3 h-3 text-zinc-600 absolute right-3 pointer-events-none" />
          </div>
        </div>

        {/* Submit button */}
        <div className="pr-2">
          <button
            type="submit"
            disabled={!address.trim() || loading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold transition-all duration-200 active:scale-95"
            style={{
              boxShadow: address.trim()
                ? '0 0 16px rgba(14,165,233,0.4)'
                : 'none',
            }}
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              'Analyze'
            )}
          </button>
        </div>
      </div>

      {/* Hint text */}
      <p className="text-center text-xs text-zinc-700 mt-3">
        Supports Solana, Ethereum, Base, and Arbitrum wallets
      </p>
    </form>
  )
}
