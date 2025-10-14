import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/hooks/use-auth'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'GAL Live Graphics Dashboard',
  description: 'Guardian Angel League Live Graphics Dashboard v2.0',
  keywords: ['GAL', 'Guardian Angel League', 'Live Graphics', 'Broadcasting', 'Dashboard'],
  authors: [{ name: 'Guardian Angel League' }],
  viewport: 'width=device-width, initial-scale=1',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
