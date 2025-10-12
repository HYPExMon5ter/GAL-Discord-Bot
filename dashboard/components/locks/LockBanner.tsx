'use client';

import { useState, useEffect } from 'react';
import { CanvasLock } from '@/types';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { formatTimeRemaining, formatDate } from '@/lib/utils';
import { Lock, Clock, User, AlertCircle } from 'lucide-react';

interface LockBannerProps {
  lock: CanvasLock;
  onRefresh?: () => void;
  onRelease?: () => void;
}

export function LockBanner({ lock, onRefresh, onRelease }: LockBannerProps) {
  const { username } = useAuth();
  const [timeRemaining, setTimeRemaining] = useState('');
  const [isExpired, setIsExpired] = useState(false);

  const isLockedByMe = lock.user_name === username;
  const canRelease = isLockedByMe && onRelease;

  useEffect(() => {
    const updateTime = () => {
      const remaining = formatTimeRemaining(new Date(lock.expires_at));
      setTimeRemaining(remaining);
      setIsExpired(remaining === 'Expired');
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);

    return () => clearInterval(interval);
  }, [lock.expires_at]);

  if (isExpired) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-full">
              <AlertCircle className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <p className="font-medium text-red-800">Editing Session Expired</p>
              <p className="text-sm text-red-600">
                Your editing session has ended. You can now edit this graphic.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            className="text-red-600 border-red-200 hover:bg-red-50"
          >
            Check Status
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={`${
      isLockedByMe 
        ? 'bg-green-50 border-green-200 text-green-800' 
        : 'bg-orange-50 border-orange-200 text-orange-800'
    } border rounded-lg p-4`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-full ${
            isLockedByMe ? 'bg-green-100' : 'bg-orange-100'
          }`}>
            <Lock className={`h-5 w-5 ${
              isLockedByMe ? 'text-green-600' : 'text-orange-600'
            }`} />
          </div>
          
          <div>
            <div className="flex items-center gap-2 mb-1">
              <p className="font-medium">
                {isLockedByMe ? 'You are currently editing' : `Currently being edited by ${lock.user_name}`}
              </p>
              <Badge variant="secondary" className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {timeRemaining}
              </Badge>
            </div>
            
            <div className="flex items-center gap-4 text-sm opacity-75">
              <div className="flex items-center gap-1">
                <User className="h-3 w-3" />
                {lock.user_name}
              </div>
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Started {formatDate(lock.locked_at)}
              </div>
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Expires {formatDate(lock.expires_at)}
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isLockedByMe && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRelease}
              className="text-green-600 border-green-200 hover:bg-green-50"
            >
              Finish Editing
            </Button>
          )}
          
          {onRefresh && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              className={isLockedByMe 
                ? 'text-green-600 border-green-200 hover:bg-green-50'
                : 'text-orange-600 border-orange-200 hover:bg-orange-50'
              }
            >
              Refresh
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
