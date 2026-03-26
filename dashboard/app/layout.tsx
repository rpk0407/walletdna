import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'WalletDNA — Myers-Briggs for Wallets',
  description: 'On-chain personality profiling. Classify crypto wallet behavior into trading archetypes.',
  openGraph: {
    title: 'WalletDNA',
    description: 'Discover your on-chain personality',
    images: ['/og/default.png'],
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen font-mono antialiased">
        {children}
      </body>
    </html>
  )
}
