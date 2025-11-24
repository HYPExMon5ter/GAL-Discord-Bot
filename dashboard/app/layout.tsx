import type { Metadata, Viewport } from 'next'
import { Poppins } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from 'next-themes'
import { AuthProvider } from '@/hooks/use-auth'
import { DashboardDataProvider } from '@/hooks/use-dashboard-data'
import { Toaster } from '@/components/ui/sonner'

const poppins = Poppins({ 
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  style: ['normal']
})

export const metadata: Metadata = {
  title: 'GAL Live Graphics Dashboard',
  description: 'Guardian Angel League Live Graphics Dashboard v2.0',
  keywords: ['GAL', 'Guardian Angel League', 'Live Graphics', 'Broadcasting', 'Dashboard'],
  authors: [{ name: 'Guardian Angel League' }],
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={poppins.className}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <AuthProvider>
            <DashboardDataProvider>
              {children}
              <Toaster duration={5000} />
            </DashboardDataProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
