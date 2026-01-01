import React from 'react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Info } from 'lucide-react';

interface ConfidenceScore {
  overall: number;
  classification?: number;
  ocrConsensus?: number;
  playerMatch?: number;
  structural?: number;
}

interface ConfidenceIndicatorProps {
  confidence: ConfidenceScore;
  showBreakdown?: boolean;
}

export function ConfidenceIndicator({ 
  confidence, 
  showBreakdown = true 
}: ConfidenceIndicatorProps) {
  const { overall } = confidence;

  // Determine confidence level
  const getConfidenceLevel = (score: number) => {
    if (score >= 0.9) return { level: 'high', color: 'bg-green-500', emoji: '🟢', label: 'High' };
    if (score >= 0.7) return { level: 'medium', color: 'bg-yellow-500', emoji: '🟡', label: 'Medium' };
    return { level: 'low', color: 'bg-red-500', emoji: '🔴', label: 'Low' };
  };

  const confidenceInfo = getConfidenceLevel(overall);

  // Format percentage
  const formatPercent = (value?: number) => {
    if (value === undefined) return 'N/A';
    return `${Math.round(value * 100)}%`;
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="inline-flex items-center gap-2 cursor-help">
            <Badge 
              variant="outline"
              className={`px-3 py-1 font-semibold border-2 ${
                confidenceInfo.level === 'high' 
                  ? 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950 dark:text-green-300'
                  : confidenceInfo.level === 'medium'
                  ? 'border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-950 dark:text-yellow-300'
                  : 'border-red-500 text-red-700 bg-red-50 dark:bg-red-950 dark:text-red-300'
              }`}
            >
              <span className="mr-1">{confidenceInfo.emoji}</span>
              {formatPercent(overall)} {confidenceInfo.label}
            </Badge>
            
            {showBreakdown && (
              <Info className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </TooltipTrigger>
        
        {showBreakdown && (
          <TooltipContent side="bottom" className="w-64 p-4">
            <div className="space-y-2">
              <div className="font-semibold border-b pb-2 mb-2">
                Confidence Breakdown
              </div>
              
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Overall:</span>
                  <span className="font-medium">{formatPercent(overall)}</span>
                </div>
                
                {confidence.classification !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Classification:</span>
                    <span className="font-medium">{formatPercent(confidence.classification)}</span>
                  </div>
                )}
                
                {confidence.ocrConsensus !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">OCR Consensus:</span>
                    <span className="font-medium">{formatPercent(confidence.ocrConsensus)}</span>
                  </div>
                )}
                
                {confidence.playerMatch !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Player Matching:</span>
                    <span className="font-medium">{formatPercent(confidence.playerMatch)}</span>
                  </div>
                )}
                
                {confidence.structural !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Structural:</span>
                    <span className="font-medium">{formatPercent(confidence.structural)}</span>
                  </div>
                )}
              </div>
              
              <div className="text-xs text-muted-foreground mt-3 pt-2 border-t">
                {confidenceInfo.level === 'high' && '✅ Auto-validation eligible'}
                {confidenceInfo.level === 'medium' && '⚠️ Manual review recommended'}
                {confidenceInfo.level === 'low' && '❌ Manual review required'}
              </div>
            </div>
          </TooltipContent>
        )}
      </Tooltip>
    </TooltipProvider>
  );
}
