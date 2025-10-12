'use client';

import { useState, useEffect, ReactNode } from 'react';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LogOut, Settings, Users, Lock, Palette } from 'lucide-react';

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
              <div className="flex items-center space-x-2">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Palette className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h1 className="text-xl font-bold">Live Graphics Dashboard</h1>
                  <p className="text-sm text-muted-foreground">Broadcast Graphics Management</p>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm font-medium">{username}</p>
                <p className="text-xs text-muted-foreground">
                  {currentTime.toLocaleTimeString()}
                </p>
              </div>
              
              <Badge variant="secondary" className="flex items-center gap-1">
                <Lock className="h-3 w-3" />
                Online
              </Badge>
              
              <Button
                variant="outline"
                size="sm"
                onClick={logout}
                className="flex items-center gap-2"
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
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="graphics" className="flex items-center gap-2">
              <Palette className="h-4 w-4" />
              Active Graphics
            </TabsTrigger>
            <TabsTrigger value="archive" className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Archived Graphics
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
