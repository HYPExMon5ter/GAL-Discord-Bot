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
      <header className="bg-card/80 backdrop-blur supports-[backdrop-filter]:bg-card/60 gal-card flex-shrink-0">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center space-x-3">
              <img 
                src="/assets/GA_Logo_Transparent_Background_White_Text.png" 
                alt="Guardian Angel League Logo" 
                className="w-14 h-14 sm:w-20 sm:h-20 rounded-xl gal-glow-primary object-cover"
              />
              <div>
                <h1 className="text-2xl sm:text-4xl font-abrau font-bold gal-text-gradient-sunset">
                  {title}
                </h1>
                <p className="text-sm sm:text-base font-montserrat text-gal-text-secondary">{subtitle}</p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-3">
              {toolbar}
              <Button
                variant="destructive"
                size="sm"
                onClick={logout}
                className="flex items-center gap-2 bg-gradient-to-r from-gal-error to-gal-error hover:from-red-600 hover:to-red-700 transition-all duration-200 rounded-gal w-full sm:w-auto"
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </Button>
            </div>
          </div>
        </div>
      </header>
      
      <div className="border-b border-border/20"></div>

      <main className="flex-grow container mx-auto px-4 py-6 w-full">
        {children}
      </main>

      <footer className="flex-shrink-0 border-t border-border/20 bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/60 mt-auto">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-muted-foreground">
            <p className="text-center sm:text-left font-montserrat">© Guardian Angel League - Live Graphics Dashboard</p>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-gal-success rounded-full animate-pulse" />
              <span className="text-center sm:text-right font-montserrat">System Online</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
