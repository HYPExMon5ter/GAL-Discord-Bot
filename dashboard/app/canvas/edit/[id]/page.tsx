'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { CanvasEditor } from '@/components/canvas/CanvasEditor';
import { useGraphics } from '@/hooks/use-graphics';
import { Graphic } from '@/types';
import { AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

export default function CanvasEditPage() {
  const params = useParams();
  const router = useRouter();
  const { getGraphic, updateGraphic, refetch } = useGraphics();

  // Generate unique session ID for this editor instance
  const sessionId = useRef<string>(crypto.randomUUID());

  const [graphic, setGraphic] = useState<Graphic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const graphicId = params.id as string;

  useEffect(() => {
    const loadGraphic = async () => {
      if (!graphicId) {
        setError('No graphic ID provided');
        setLoading(false);
        return;
      }

      try {
        const data = await getGraphic(parseInt(graphicId, 10));
        if (data) {
          setGraphic(data);
        } else {
          setError('Graphic not found');
        }
      } catch (err) {
        console.error('Failed to load graphic:', err);
        setError('Failed to load graphic');
      } finally {
        setLoading(false);
      }
    };

    loadGraphic();
  }, [graphicId, getGraphic]);

  const handleSave = async (data: { title: string; event_name: string; data_json: string }): Promise<boolean> => {
    if (!graphic) return false;

    try {
      await updateGraphic(graphic.id, {
        title: data.title,
        event_name: data.event_name,
        data_json: data.data_json,
      });
      return true;
    } catch (error) {
      console.error('Failed to save graphic:', error);
      return false;
    }
  };

  const handleClose = () => {
    refetch().catch(err => console.error('Failed to refresh graphics after closing editor', err));
    router.push('/dashboard');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="w-96">
          <CardContent className="pt-6">
            <div className="flex items-center justify-center gap-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span>Loading graphic...</span>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !graphic) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="w-96">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-red-600">
              <AlertCircle className="h-8 w-8" />
              <div>
                <p className="font-medium">Error</p>
                <p className="text-sm">{error || 'Graphic not found'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <CanvasEditor
      graphic={graphic}
      onSave={handleSave}
      onClose={handleClose}
      sessionId={sessionId.current}
    />
  );
}
