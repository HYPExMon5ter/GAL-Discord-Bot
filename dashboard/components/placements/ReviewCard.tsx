import React, { useState } from 'react';
import Image from 'next/image';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PlacementEditor } from './PlacementEditor';
import { ConfidenceIndicator } from './ConfidenceIndicator';
import { Check, X, RefreshCw, Download, ZoomIn, Clock, User } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

interface Placement {
  id?: number;
  player_id?: string;
  player_name: string;
  placement: number;
  points: number;
  match_method?: string;
  validated?: boolean;
}

interface Player {
  id: string;
  name: string;
  aliases?: string[];
  match_confidence?: number;
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

interface ReviewCardProps {
  submission: Submission;
  availablePlayers: Player[];
  onApprove: (submissionId: number, placements: Placement[]) => void;
  onReject: (submissionId: number, reason?: string) => void;
  onReprocess?: (submissionId: number) => void;
  onSearchPlayers?: (query: string) => void;
  isProcessing?: boolean;
}

export function ReviewCard({
  submission,
  availablePlayers,
  onApprove,
  onReject,
  onReprocess,
  onSearchPlayers,
  isProcessing = false,
}: ReviewCardProps) {
  const [editedPlacements, setEditedPlacements] = useState<Placement[]>(submission.placements);
  const [imageZoomed, setImageZoomed] = useState(false);

  const handleApprove = () => {
    onApprove(submission.id, editedPlacements);
  };

  const handleReject = () => {
    const reason = window.prompt('Reason for rejection (optional):');
    onReject(submission.id, reason || undefined);
  };

  const handleDownload = () => {
    window.open(submission.image_url, '_blank');
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  return (
    <Card className="w-full">
      <CardHeader className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <CardTitle className="text-2xl">
              {submission.round_name} - Lobby {submission.lobby_number}
            </CardTitle>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                {formatTimestamp(submission.created_at)}
              </div>
              <div className="flex items-center gap-1">
                <User className="h-4 w-4" />
                {submission.placements.length} players
              </div>
            </div>
          </div>
          <ConfidenceIndicator
            confidence={{
              overall: submission.overall_confidence,
            }}
          />
        </div>

        {/* Issues banner */}
        {submission.issues && submission.issues.length > 0 && (
          <div className="rounded-lg border border-yellow-500 bg-yellow-50 dark:bg-yellow-950 p-3">
            <div className="text-sm font-semibold text-yellow-800 dark:text-yellow-200 mb-1">
              Issues Detected:
            </div>
            <ul className="text-sm text-yellow-700 dark:text-yellow-300 list-disc list-inside space-y-0.5">
              {submission.issues.map((issue, index) => (
                <li key={index}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Screenshot Image */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-lg">Screenshot</h3>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setImageZoomed(!imageZoomed)}
                >
                  <ZoomIn className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownload}
                >
                  <Download className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className={`relative rounded-lg border overflow-hidden bg-muted ${imageZoomed ? 'aspect-auto' : 'aspect-video'}`}>
              <Image
                src={submission.image_url}
                alt={`${submission.round_name} Lobby ${submission.lobby_number}`}
                fill={!imageZoomed}
                width={imageZoomed ? 1920 : undefined}
                height={imageZoomed ? 1080 : undefined}
                className={imageZoomed ? 'w-full h-auto' : 'object-contain'}
                unoptimized
              />
            </div>

            {imageZoomed && (
              <p className="text-xs text-muted-foreground text-center">
                Click the zoom button again to reset view
              </p>
            )}
          </div>

          {/* Right: Extracted Data */}
          <div className="space-y-3">
            <h3 className="font-semibold text-lg">Extracted Placements</h3>
            <PlacementEditor
              placements={editedPlacements}
              availablePlayers={availablePlayers}
              onChange={setEditedPlacements}
              onSearchPlayers={onSearchPlayers}
              editable={!isProcessing}
            />
          </div>
        </div>

        <Separator />

        {/* Action buttons */}
        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            {onReprocess && (
              <Button
                variant="outline"
                onClick={() => onReprocess(submission.id)}
                disabled={isProcessing}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Reprocess
              </Button>
            )}
          </div>

          <div className="flex gap-2">
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={isProcessing}
            >
              <X className="h-4 w-4 mr-2" />
              Reject
            </Button>
            <Button
              onClick={handleApprove}
              disabled={isProcessing}
              className="gal-button-primary"
            >
              <Check className="h-4 w-4 mr-2" />
              Approve
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
