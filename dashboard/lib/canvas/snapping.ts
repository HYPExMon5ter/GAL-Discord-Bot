import type { CanvasElement } from '@/lib/canvas/types';

// Simple element snapping - no grid, just alignment
// Calculates snap positions to other elements

interface SnapThreshold {
  horizontal: number;
  vertical: number;
}

const DEFAULT_SNAP_THRESHOLD: SnapThreshold = {
  horizontal: 8,  // 8px snap tolerance
  vertical: 8,
};

interface SnapResult {
  x: number;
  y: number;
  snapLines: SnapLine[];
}

interface SnapLine {
  x?: number;
  y?: number;
  type: 'horizontal' | 'vertical';
}

export function calculateElementSnapping(
  element: CanvasElement,
  elements: CanvasElement[],
  currentPosition: { x: number; y: number },
  threshold: SnapThreshold = DEFAULT_SNAP_THRESHOLD
): SnapResult {
  const snapLines: SnapLine[] = [];
  let snappedX = currentPosition.x;
  let snappedY = currentPosition.y;

  // Don't snap to self
  const otherElements = elements.filter(el => el.id !== element.id);

  for (const other of otherElements) {
    // Horizontal snapping (align to other elements' X positions)
    const horizontalSnapX = calculateSnap(
      currentPosition.x,
      other.x,
      threshold.horizontal
    );
    if (horizontalSnapX !== null) {
      snappedX = horizontalSnapX;
      snapLines.push({ x: horizontalSnapX, type: 'vertical' });
    }

    // Vertical snapping (align to other elements' Y positions)
    const verticalSnapY = calculateSnap(
      currentPosition.y,
      other.y,
      threshold.vertical
    );
    if (verticalSnapY !== null) {
      snappedY = verticalSnapY;
      snapLines.push({ y: verticalSnapY, type: 'horizontal' });
    }

    // Edge-to-edge snapping
    const elementWidth = 100;  // Approximate width - could be enhanced
    const elementHeight = 30;  // Approximate height
    const otherWidth = 100;
    const otherHeight = 30;

    // Right edge to left edge
    const rightToLeftSnap = calculateSnap(
      currentPosition.x + elementWidth,
      other.x,
      threshold.horizontal
    );
    if (rightToLeftSnap !== null) {
      snappedX = rightToLeftSnap - elementWidth;
      snapLines.push({ x: other.x, type: 'vertical' });
    }

    // Left edge to right edge
    const leftToRightSnap = calculateSnap(
      currentPosition.x,
      other.x + otherWidth,
      threshold.horizontal
    );
    if (leftToRightSnap !== null) {
      snappedX = leftToRightSnap;
      snapLines.push({ x: other.x + otherWidth, type: 'vertical' });
    }

    // Bottom edge to top edge
    const bottomToTopSnap = calculateSnap(
      currentPosition.y + elementHeight,
      other.y,
      threshold.vertical
    );
    if (bottomToTopSnap !== null) {
      snappedY = bottomToTopSnap - elementHeight;
      snapLines.push({ y: other.y, type: 'horizontal' });
    }

    // Top edge to bottom edge
    const topToBottomSnap = calculateSnap(
      currentPosition.y,
      other.y + otherHeight,
      threshold.vertical
    );
    if (topToBottomSnap !== null) {
      snappedY = topToBottomSnap;
      snapLines.push({ y: other.y + otherHeight, type: 'horizontal' });
    }
  }

  return {
    x: snappedX,
    y: snappedY,
    snapLines,
  };
}

// Helper to calculate if two positions should snap
function calculateSnap(current: number, target: number, threshold: number): number | null {
  const distance = Math.abs(current - target);
  if (distance <= threshold) {
    return target;
  }
  return null;
}

// Check if element is within canvas bounds
export function constrainToCanvas(
  x: number,
  y: number,
  canvasWidth: number,
  canvasHeight: number,
  elementWidth: number = 100,
  elementHeight: number = 30
): { x: number; y: number } {
  const constrainedX = Math.max(0, Math.min(x, canvasWidth - elementWidth));
  const constrainedY = Math.max(0, Math.min(y, canvasHeight - elementHeight));

  return {
    x: constrainedX,
    y: constrainedY,
  };
}
