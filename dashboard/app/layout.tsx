import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'WalletDNA — Myers-Briggs for Wallets',
  description:
    'On-chain personality profiling. Classify crypto wallet behavior into trading archetypes.',
  openGraph: {
    title: 'WalletDNA',
    description: 'Discover your on-chain personality',
    images: ['/og/default.png'],
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-black text-zinc-100 min-h-screen font-sans antialiased">
        {children}
      </body>
    </html>
  )
}
