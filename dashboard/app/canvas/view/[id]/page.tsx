'use client';

import { useParams } from 'next/navigation';
import { CanvasView } from '@/components/canvas/CanvasView';

export default function ObsViewPage() {
  const params = useParams();
  const graphicId = Number(params?.id);
  
  // Ensure we have a valid ID before rendering
  if (isNaN(graphicId)) {
    return (
      <div className="w-screen h-screen overflow-hidden flex items-center justify-center bg-gray-900">
        <div className="text-center text-red-400">
          <p className="text-lg font-medium">Invalid Graphic ID</p>
          <p className="text-sm">Please check the URL and try again.</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="w-screen h-screen overflow-hidden">
      <CanvasView graphicId={graphicId} />
    </div>
  );
}
