// Simple mock data generator for editor preview mode
// No complexity - just placeholders for layout testing

export function generateMockData(type: 'players' | 'scores' | 'placements', count: number): string[] {
  switch (type) {
    case 'players':
      return Array.from({ length: count }, (_, i) => `Player ${i + 1}`);
    
    case 'scores':
      return Array.from({ length: count }, (_, i) => `${100 - i * 5}`);
    
    case 'placements':
      return Array.from({ length: count }, (_, i) => {
        const num = i + 1;
        const suffix = num === 1 ? 'st' : num === 2 ? 'nd' : num === 3 ? 'rd' : 'th';
        return `${num}${suffix}`;
      });
    
    default:
      return [];
  }
}
