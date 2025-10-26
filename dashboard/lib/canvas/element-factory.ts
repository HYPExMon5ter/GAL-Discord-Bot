import type { TextElement, DynamicElement, ElementType } from '@/lib/canvas/types';
import { DEFAULT_ELEMENT_CONFIGS } from '@/lib/canvas/types';

export function generateElementId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `element-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

export function createTextElement(overrides: Partial<TextElement> = {}): TextElement {
  const config = DEFAULT_ELEMENT_CONFIGS.text;
  return {
    id: generateElementId(),
    type: 'text',
    x: config.x,
    y: config.y,
    fontSize: config.fontSize,
    fontFamily: config.fontFamily,
    color: config.color,
    content: 'Text',
    ...overrides,
  };
}

export function createDynamicElement(
  type: 'players' | 'scores' | 'placements',
  overrides: Partial<DynamicElement> = {}
): DynamicElement {
  const config = DEFAULT_ELEMENT_CONFIGS[type];
  return {
    id: generateElementId(),
    type,
    x: config.x,
    y: config.y,
    fontSize: config.fontSize,
    fontFamily: config.fontFamily,
    color: config.color,
    spacing: 56,           // Default vertical spacing
    previewCount: 10,       // Default mock items
    ...overrides,
  };
}

export function createElement(type: ElementType, overrides: Partial<any> = {}): TextElement | DynamicElement {
  if (type === 'text') {
    return createTextElement(overrides);
  } else {
    return createDynamicElement(type, overrides);
  }
}
