import React from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ConfidenceIndicator } from './ConfidenceIndicator';
import { Clock, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Submission {
  id: number;
  tournament_id: string;
  round_name: string;
  lobby_number: number;
  image_url: string;
  status: string;
  overall_confidence: number;
  created_at: string;
  placements: any[];
  issues?: string[];
}

interface SubmissionListProps {
  submissions: Submission[];
  selectedId?: number;
  onSelect: (submission: Submission) => void;
  isLoading?: boolean;
}

export function SubmissionList({
  submissions,
  selectedId,
  onSelect,
  isLoading = false,
}: SubmissionListProps) {
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <Card key={i} className="p-4 animate-pulse">
            <div className="h-6 bg-muted rounded mb-2"></div>
            <div className="h-4 bg-muted rounded w-2/3"></div>
          </Card>
        ))}
      </div>
    );
  }

  if (submissions.length === 0) {
    return (
      <Card className="p-8 text-center">
        <div className="text-muted-foreground">
          <Clock className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p className="font-medium">No submissions found</p>
          <p className="text-sm mt-1">Pending reviews will appear here</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {submissions.map((submission) => (
        <Card
          key={submission.id}
          className={cn(
            'p-4 cursor-pointer transition-all hover:shadow-md',
            selectedId === submission.id && 'ring-2 ring-primary bg-accent'
          )}
          onClick={() => onSelect(submission)}
        >
          <div className="space-y-3">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h4 className="font-semibold truncate">
                  {submission.round_name} - Lobby {submission.lobby_number}
                </h4>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                  <Clock className="h-3 w-3" />
                  {formatTimestamp(submission.created_at)}
                </div>
              </div>
            </div>

            {/* Confidence */}
            <div className="flex items-center justify-between">
              <ConfidenceIndicator
                confidence={{ overall: submission.overall_confidence }}
                showBreakdown={false}
              />
              <span className="text-xs text-muted-foreground">
                {submission.placements.length} players
              </span>
            </div>

            {/* Issues */}
            {submission.issues && submission.issues.length > 0 && (
              <div className="flex items-start gap-2 text-xs text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-950 rounded p-2">
                <AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" />
                <span className="flex-1">{submission.issues[0]}</span>
                {submission.issues.length > 1 && (
                  <Badge variant="outline" className="text-xs">
                    +{submission.issues.length - 1}
                  </Badge>
                )}
              </div>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
}
