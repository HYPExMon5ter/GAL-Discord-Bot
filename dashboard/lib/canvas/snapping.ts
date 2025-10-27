import type { CanvasElement } from '@/lib/canvas/types';

// Simple element snapping - no grid, just alignment
// Calculates snap positions to other elements

interface SnapThreshold {
  horizontal: number;
  vertical: number;
}

const DEFAULT_SNAP_THRESHOLD: SnapThreshold = {
  horizontal: 5,  // 5px snap tolerance (reduced for cleaner snapping)
  vertical: 5,
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

// Cache for element dimensions to avoid recalculating
const elementDimensionCache = new Map<string, { width: number; height: number }>();

// Removed snap result cache - was causing more overhead than benefit

// Global measurement container for text dimensions (created once)
let measurementContainer: HTMLDivElement | null = null;

// Get element dimensions with caching
function getElementDimensions(element: CanvasElement): { width: number; height: number } {
  if (elementDimensionCache.has(element.id)) {
    return elementDimensionCache.get(element.id)!;
  }

  let width = 100;
  let height = 30;

  if (element.type === 'text') {
    // Create or reuse measurement container
    if (!measurementContainer) {
      measurementContainer = document.createElement('div');
      measurementContainer.style.position = 'absolute';
      measurementContainer.style.visibility = 'hidden';
      measurementContainer.style.top = '-9999px';
      measurementContainer.style.left = '-9999px';
      document.body.appendChild(measurementContainer);
    }

    // Create a temporary element for measurement
    const tempDiv = document.createElement('div');
    tempDiv.style.fontSize = `${element.fontSize || 16}px`;
    tempDiv.style.fontFamily = element.fontFamily || 'sans-serif';
    tempDiv.style.whiteSpace = 'nowrap';
    tempDiv.textContent = element.content || '';
    
    measurementContainer.appendChild(tempDiv);
    const rect = tempDiv.getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    measurementContainer.removeChild(tempDiv);
  }

  const dimensions = { width, height };
  elementDimensionCache.set(element.id, dimensions);
  return dimensions;
}

export function calculateElementSnapping(
  element: CanvasElement,
  elements: CanvasElement[],
  currentPosition: { x: number; y: number },
  threshold: SnapThreshold = DEFAULT_SNAP_THRESHOLD
): SnapResult {
  const snapLines: SnapLine[] = [];
  
  // Round position first to avoid jitter
  let snappedX = Math.round(currentPosition.x);
  let snappedY = Math.round(currentPosition.y);

  // Don't snap to self
  const otherElements = elements.filter(el => el.id !== element.id);
  
  // Get element dimensions once
  const elementDims = getElementDimensions(element);

  for (const other of otherElements) {
    const otherDims = getElementDimensions(other);

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

    // Edge-to-edge snapping with actual dimensions
    // Right edge to left edge
    const rightToLeftSnap = calculateSnap(
      currentPosition.x + elementDims.width,
      other.x,
      threshold.horizontal
    );
    if (rightToLeftSnap !== null) {
      snappedX = rightToLeftSnap - elementDims.width;
      snapLines.push({ x: other.x, type: 'vertical' });
    }

    // Left edge to right edge
    const leftToRightSnap = calculateSnap(
      currentPosition.x,
      other.x + otherDims.width,
      threshold.horizontal
    );
    if (leftToRightSnap !== null) {
      snappedX = leftToRightSnap;
      snapLines.push({ x: other.x + otherDims.width, type: 'vertical' });
    }

    // Bottom edge to top edge
    const bottomToTopSnap = calculateSnap(
      currentPosition.y + elementDims.height,
      other.y,
      threshold.vertical
    );
    if (bottomToTopSnap !== null) {
      snappedY = bottomToTopSnap - elementDims.height;
      snapLines.push({ y: other.y, type: 'horizontal' });
    }

    // Top edge to bottom edge
    const topToBottomSnap = calculateSnap(
      currentPosition.y,
      other.y + otherDims.height,
      threshold.vertical
    );
    if (topToBottomSnap !== null) {
      snappedY = topToBottomSnap;
      snapLines.push({ y: other.y + otherDims.height, type: 'horizontal' });
    }
  }

  return {
    x: snappedX,
    y: snappedY,
    snapLines,
  };
}

// Clear dimension cache when elements change
export function clearDimensionCache() {
  elementDimensionCache.clear();
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
