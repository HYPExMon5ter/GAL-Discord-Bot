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
        className="bg-gray-900 flex items-center justify-center"
        style={style}
      >
        <div className="text-gray-600 text-center">
          <p className="text-lg font-medium">No Background</p>
          <p className="text-sm">Upload an image to get started</p>
        </div>
        {children}
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
