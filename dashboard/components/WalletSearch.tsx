'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export function WalletSearch() {
  const [address, setAddress] = useState('')
  const [chain, setChain] = useState('solana')
  const router = useRouter()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = address.trim()
    if (!trimmed) return
    router.push(`/wallet/${trimmed}?chain=${chain}`)
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-xl space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Paste any wallet address..."
          className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-sky-500 transition-colors"
        />
        <select
          value={chain}
          onChange={(e) => setChain(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-sky-500"
        >
          <option value="solana">Solana</option>
          <option value="ethereum">Ethereum</option>
          <option value="base">Base</option>
          <option value="arbitrum">Arbitrum</option>
        </select>
      </div>
      <button
        type="submit"
        className="w-full bg-sky-500 hover:bg-sky-400 text-white font-semibold py-3 rounded-xl transition-colors"
      >
        Analyze Wallet
      </button>
    </form>
  )
}
