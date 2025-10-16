'use client';

import type { ReactNode } from 'react';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { LogOut } from 'lucide-react';

interface DashboardLayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  toolbar?: ReactNode;
}

export function DashboardLayout({
  children,
  title = 'Live Graphics Dashboard',
  subtitle = 'Guardian Angel League',
  toolbar,
}: DashboardLayoutProps) {
  const { logout } = useAuth();

  return (
    <div className="min-h-screen bg-background gal-scrollbar flex flex-col">
      <header className="border-b border-border/20 bg-card/80 backdrop-blur supports-[backdrop-filter]:bg-card/60 gal-card flex-shrink-0">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 gal-gradient-primary rounded-xl flex items-center justify-center text-white font-bold text-xl gal-glow-primary">
                GAL
              </div>
              <div>
                <h1 className="text-3xl font-bold gal-gradient-text">{title}</h1>
                <p className="text-sm text-muted-foreground">{subtitle}</p>
              </div>
            </div>

            <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-end">
              {toolbar}
              <Button
                variant="destructive"
                size="sm"
                onClick={logout}
                className="flex items-center gap-2 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 transition-all duration-200"
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-grow container mx-auto px-4 py-6 w-full">
        {children}
      </main>

      <footer className="flex-shrink-0 border-t border-border/20 bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/60 mt-auto relative z-[60]">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-muted-foreground">
            <p className="text-center sm:text-left">© Guardian Angel League - Live Graphics Dashboard</p>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-center sm:text-right">System Online</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
