import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { NavBar } from '@/components/NavBar'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'WalletDNA — Myers-Briggs for Wallets',
  description:
    'On-chain personality profiling. Classify crypto wallet behavior into 6 trading archetypes using AI-powered behavioral analysis.',
  openGraph: {
    title: 'WalletDNA — Discover Your On-Chain Personality',
    description:
      'Paste any wallet. Get your on-chain archetype in seconds.',
    images: ['/og/default.png'],
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-black text-zinc-100 min-h-screen font-sans antialiased">
        <NavBar />
        {children}
      </body>
    </html>
  )
}
