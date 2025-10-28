'use client';

import React from 'react';
import type { BackgroundConfig } from '@/lib/canvas/types';

interface BackgroundRendererProps {
  background: BackgroundConfig | null;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

export function BackgroundRenderer({ background, style, children }: BackgroundRendererProps) {
  if (!background) {
    return (
      <div 
        className="bg-gray-900 flex items-center justify-center w-full h-full relative"
        style={style}
      >
        <div className="text-gray-400 text-center select-none">
          <p className="text-xl font-medium mb-2">No Background</p>
          <p className="text-sm">Upload an image to get started</p>
          <p className="text-xs mt-4 text-gray-500">
            Use the &quot;Upload Background&quot; button in the sidebar
          </p>
        </div>
        {/* Children (elements) should be visible even without background */}
        {children && (
          <div className="absolute inset-0 flex items-center justify-center">
            {children}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      style={{
        width: background.width,
        height: background.height,
        backgroundImage: `url(${background.imageUrl})`,
        backgroundSize: 'contain',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        backgroundColor: '#1a1a1a',
        position: 'relative',
        ...style,
      }}
    >
      {children}
    </div>
  );
}
