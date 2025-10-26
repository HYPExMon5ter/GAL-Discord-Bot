'use client';

import { useRouter } from 'next/navigation';
import { CanvasView } from '@/components/canvas/CanvasView';

export default function ObsViewPage() {
  const router = useRouter();
  const graphicId = Number(router.query?.id);
  
  return (
    <div className="w-screen h-screen overflow-hidden">
      <CanvasView graphicId={graphicId} />
    </div>
  );
}
