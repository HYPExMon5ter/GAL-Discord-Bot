'use client';

import { useState, useEffect, ReactNode } from 'react';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LogOut, Settings, Users, Lock, Palette, Sparkles, Archive, Package } from 'lucide-react';

interface DashboardLayoutProps {
  children: ReactNode;
  activeTab?: string;
  onTabChange?: (tab: string) => void;
}

export function DashboardLayout({ 
  children, 
  activeTab = 'graphics', 
  onTabChange 
}: DashboardLayoutProps) {
  const { username, logout } = useAuth();
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const handleTabChange = (value: string) => {
    if (onTabChange) {
      onTabChange(value);
    }
  };

  return (
    <div className="min-h-screen bg-background gal-scrollbar flex flex-col">
      {/* Header */}
      <header className="border-b border-border/20 bg-card/80 backdrop-blur supports-[backdrop-filter]:bg-card/60 gal-card flex-shrink-0">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 gal-gradient-primary rounded-xl flex items-center justify-center text-white font-bold text-xl gal-glow-primary">
                  GAL
                </div>
                <div>
                  <h1 className="text-3xl font-bold gal-gradient-text">Live Graphics Dashboard</h1>
                  <p className="text-sm text-muted-foreground">Guardian Angel League</p>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <Badge variant="secondary" className="flex items-center gap-1 bg-gradient-to-r from-green-500 to-emerald-600 text-white border-0">
                <Lock className="h-3 w-3" />
                Online
              </Badge>
              
              <Button
                variant="destructive"
                size="sm"
                onClick={logout}
                className="flex items-center gap-2 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 shadow-md hover:shadow-lg transition-all duration-200"
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full h-full">
          <TabsList className="grid w-full grid-cols-2 bg-card p-1 rounded-xl shadow-lg gal-card">
            <TabsTrigger 
              value="graphics" 
              className="flex items-center gap-2 data-[state=active]:gal-button-primary data-[state=active]:text-white text-muted-foreground hover:text-foreground transition-all duration-200 rounded-lg"
            >
              <span className="text-yellow-300">🎨</span> Active Graphics
            </TabsTrigger>
            <TabsTrigger 
              value="archive" 
              className="flex items-center gap-2 data-[state=active]:gal-button-primary data-[state=active]:text-white text-muted-foreground hover:text-foreground transition-all duration-200 rounded-lg"
            >
              <span className="text-orange-300">📦</span> Archived Graphics
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="graphics" className="mt-6">
            {children}
          </TabsContent>
          
          <TabsContent value="archive" className="mt-6">
            {children}
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="flex-shrink-0 border-t border-border/20 bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/60 mt-auto">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-muted-foreground">
            <p className="text-center sm:text-left">© Guardian Angel League — Live Graphics Dashboard</p>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-center sm:text-right">System Online</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
