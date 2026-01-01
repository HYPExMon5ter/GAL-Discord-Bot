'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { GraphicsTab } from '@/components/graphics/GraphicsTab';
import { ArchiveTab } from '@/components/archive/ArchiveTab';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

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

  // Create toolbar with navigation buttons
  const toolbar = (
    <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
      <Button
        variant="ghost"
        onClick={() => setActiveTab('graphics')}
        className={`gal-button-tab ${activeTab === 'graphics' ? 'active' : ''} w-full sm:w-auto`}
      >
        Active Graphics
      </Button>
      <Button
        variant="ghost"
        onClick={() => setActiveTab('archive')}
        className={`gal-button-tab ${activeTab === 'archive' ? 'active' : ''} w-full sm:w-auto`}
      >
        Archived Graphics
      </Button>
      <Button
        variant="ghost"
        onClick={() => router.push('/admin/placements/review')}
        className="gal-button-tab w-full sm:w-auto"
      >
        Screenshot Review
      </Button>
    </div>
  );

  return (
    <DashboardLayout toolbar={toolbar}>
      {activeTab === 'graphics' && <GraphicsTab />}
      {activeTab === 'archive' && <ArchiveTab />}
    </DashboardLayout>
  );
}
