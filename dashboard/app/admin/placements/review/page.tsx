'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { SubmissionList } from '@/components/placements/SubmissionList';
import { ReviewCard } from '@/components/placements/ReviewCard';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { RefreshCw, CheckCircle, XCircle, Clock } from 'lucide-react';
import { toast } from 'sonner';

interface Placement {
  id?: number;
  player_id?: string;
  player_name: string;
  placement: number;
  points: number;
  match_method?: string;
  validated?: boolean;
}

interface Submission {
  id: number;
  tournament_id: string;
  round_name: string;
  lobby_number: number;
  image_url: string;
  status: string;
  overall_confidence: number;
  created_at: string;
  placements: Placement[];
  issues?: string[];
}

interface Player {
  id: string;
  name: string;
  aliases?: string[];
  match_confidence?: number;
}

export default function PlacementReviewPage() {
  const { isAuthenticated, loading, apiToken } = useAuth();
  const router = useRouter();
  
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);
  const [availablePlayers, setAvailablePlayers] = useState<Player[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('pending');

  // Redirect if not authenticated
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, loading, router]);

  // Fetch pending submissions
  const fetchSubmissions = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/v1/placements/pending-review`, {
        headers: {
          Authorization: `Bearer ${apiToken}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch submissions');

      const data = await response.json();
      setSubmissions(data.submissions || []);

      // Auto-select first submission if none selected
      if (!selectedSubmission && data.submissions.length > 0) {
        setSelectedSubmission(data.submissions[0]);
      }
    } catch (error) {
      console.error('Error fetching submissions:', error);
      toast.error('Failed to load submissions');
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch available players
  const fetchPlayers = async (query: string = '') => {
    try {
      const url = query 
        ? `/api/v1/placements/players/search?q=${encodeURIComponent(query)}`
        : `/api/v1/placements/players/search?q=a`; // Get all players starting with 'a' as default

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${apiToken}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch players');

      const data = await response.json();
      setAvailablePlayers(data.players || []);
    } catch (error) {
      console.error('Error fetching players:', error);
    }
  };

  // Initial load
  useEffect(() => {
    if (isAuthenticated && apiToken) {
      fetchSubmissions();
      fetchPlayers();
    }
  }, [isAuthenticated, apiToken]);

  // Handle approve submission
  const handleApprove = async (submissionId: number, placements: Placement[]) => {
    setIsProcessing(true);
    try {
      const response = await fetch(`/api/v1/placements/validate/${submissionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiToken}`,
        },
        body: JSON.stringify({
          approved: true,
          edited_placements: placements,
        }),
      });

      if (!response.ok) throw new Error('Failed to approve submission');

      toast.success('Submission approved successfully!');
      
      // Remove from list and select next
      const remainingSubmissions = submissions.filter(s => s.id !== submissionId);
      setSubmissions(remainingSubmissions);
      setSelectedSubmission(remainingSubmissions[0] || null);
    } catch (error) {
      console.error('Error approving submission:', error);
      toast.error('Failed to approve submission');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle reject submission
  const handleReject = async (submissionId: number, reason?: string) => {
    setIsProcessing(true);
    try {
      const response = await fetch(`/api/v1/placements/validate/${submissionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiToken}`,
        },
        body: JSON.stringify({
          approved: false,
          notes: reason,
        }),
      });

      if (!response.ok) throw new Error('Failed to reject submission');

      toast.success('Submission rejected');
      
      // Remove from list and select next
      const remainingSubmissions = submissions.filter(s => s.id !== submissionId);
      setSubmissions(remainingSubmissions);
      setSelectedSubmission(remainingSubmissions[0] || null);
    } catch (error) {
      console.error('Error rejecting submission:', error);
      toast.error('Failed to reject submission');
    } finally {
      setIsProcessing(false);
    }
  };

  if (loading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex items-center gap-3 text-muted-foreground">
          <RefreshCw className="h-6 w-6 animate-spin" />
          <span>Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <DashboardLayout>
      <div className="container mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Screenshot Review</h1>
            <p className="text-muted-foreground mt-1">
              Review and approve TFT placement submissions
            </p>
          </div>
          <Button
            variant="outline"
            onClick={fetchSubmissions}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-lg border p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Clock className="h-4 w-4" />
              <span className="text-sm font-medium">Pending Review</span>
            </div>
            <div className="text-2xl font-bold">{submissions.length}</div>
          </div>
          <div className="rounded-lg border p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <CheckCircle className="h-4 w-4" />
              <span className="text-sm font-medium">Avg Confidence</span>
            </div>
            <div className="text-2xl font-bold">
              {submissions.length > 0
                ? `${Math.round((submissions.reduce((sum, s) => sum + s.overall_confidence, 0) / submissions.length) * 100)}%`
                : 'N/A'}
            </div>
          </div>
          <div className="rounded-lg border p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <XCircle className="h-4 w-4" />
              <span className="text-sm font-medium">Issues Detected</span>
            </div>
            <div className="text-2xl font-bold">
              {submissions.filter(s => s.issues && s.issues.length > 0).length}
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left sidebar: Submission list */}
          <div className="lg:col-span-3 space-y-4">
            <h2 className="font-semibold text-lg">Submissions</h2>
            <SubmissionList
              submissions={submissions}
              selectedId={selectedSubmission?.id}
              onSelect={setSelectedSubmission}
              isLoading={isLoading}
            />
          </div>

          {/* Right: Review card */}
          <div className="lg:col-span-9">
            {selectedSubmission ? (
              <ReviewCard
                submission={selectedSubmission}
                availablePlayers={availablePlayers}
                onApprove={handleApprove}
                onReject={handleReject}
                onSearchPlayers={fetchPlayers}
                isProcessing={isProcessing}
              />
            ) : (
              <div className="rounded-lg border p-12 text-center">
                <Clock className="h-16 w-16 mx-auto text-muted-foreground opacity-50 mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Submission Selected</h3>
                <p className="text-muted-foreground">
                  Select a submission from the list to review
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
