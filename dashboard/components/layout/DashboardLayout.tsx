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
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/60">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="text-4xl">🎬</div>
                <div>
                  <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Live Graphics Dashboard</h1>
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
      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="grid w-full grid-cols-2 bg-slate-800 p-1 rounded-xl shadow-lg">
            <TabsTrigger 
              value="graphics" 
              className="flex items-center gap-2 bg-slate-700 text-slate-300 data-[state=active]:bg-blue-600 data-[state=active]:text-white hover:bg-slate-600 transition-all duration-200"
            >
              <span className="text-yellow-300">🎨</span> Active Graphics
            </TabsTrigger>
            <TabsTrigger 
              value="archive" 
              className="flex items-center gap-2 bg-slate-700 text-slate-300 data-[state=active]:bg-blue-600 data-[state=active]:text-white hover:bg-slate-600 transition-all duration-200"
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
    </div>
  );
}
