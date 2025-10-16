'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { GraphicsTab } from '@/components/graphics/GraphicsTab';
import { ArchiveTab } from '@/components/archive/ArchiveTab';
import { RefreshCw } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function DashboardPage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('graphics');

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex items-center gap-3 text-muted-foreground">
          <RefreshCw className="h-6 w-6 animate-spin" />
          <span>Loading dashboard...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <DashboardLayout>
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 bg-card p-1 rounded-xl gal-card">
          <TabsTrigger
            value="graphics"
            className="flex items-center gap-2 data-[state=active]:gal-button-primary data-[state=active]:text-white text-muted-foreground hover:text-foreground transition-all duration-200 rounded-lg"
          >
            <span className="text-yellow-300">✨</span>
            Active Graphics
          </TabsTrigger>
          <TabsTrigger
            value="archive"
            className="flex items-center gap-2 data-[state=active]:gal-button-primary data-[state=active]:text-white text-muted-foreground hover:text-foreground transition-all duration-200 rounded-lg"
          >
            <span className="text-orange-300">🗂️</span>
            Archived Graphics
          </TabsTrigger>
        </TabsList>

        <TabsContent value="graphics" className="mt-6">
          <GraphicsTab />
        </TabsContent>

        <TabsContent value="archive" className="mt-6">
          <ArchiveTab />
        </TabsContent>
      </Tabs>
    </DashboardLayout>
  );
}
