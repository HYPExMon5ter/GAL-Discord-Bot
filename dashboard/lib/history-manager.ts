export interface CanvasAction {
  id: string;
  type: 'add_element' | 'update_element' | 'delete_element' | 'update_background' | 'update_settings';
  timestamp: number;
  description: string;
  data: {
    before?: any;
    after?: any;
    elementId?: string;
  };
}

export class HistoryManager {
  private history: CanvasAction[] = [];
  private currentIndex: number = -1;
  private maxHistorySize: number = 50;

  constructor() {
    // Clear history on load
    this.clear();
  }

  /**
   * Add a new action to the history
   */
  addAction(action: Omit<CanvasAction, 'id' | 'timestamp'>): void {
    // Remove any actions after current index (when undoing and then performing new action)
    this.history = this.history.slice(0, this.currentIndex + 1);

    // Create new action
    const newAction: CanvasAction = {
      id: Date.now().toString(),
      timestamp: Date.now(),
      ...action
    };

    // Add to history
    this.history.push(newAction);
    this.currentIndex++;

    // Limit history size
    if (this.history.length > this.maxHistorySize) {
      this.history.shift();
      this.currentIndex--;
    }
  }

  /**
   * Check if undo is possible
   */
  canUndo(): boolean {
    return this.currentIndex >= 0;
  }

  /**
   * Check if redo is possible
   */
  canRedo(): boolean {
    return this.currentIndex < this.history.length - 1;
  }

  /**
   * Undo the last action
   */
  undo(): CanvasAction | null {
    if (!this.canUndo()) return null;

    const action = this.history[this.currentIndex];
    this.currentIndex--;
    return action;
  }

  /**
   * Redo the next action
   */
  redo(): CanvasAction | null {
    if (!this.canRedo()) return null;

    this.currentIndex++;
    const action = this.history[this.currentIndex];
    return action;
  }

  /**
   * Get the current action history
   */
  getHistory(): CanvasAction[] {
    return [...this.history];
  }

  /**
   * Get actions that can be undone
   */
  getUndoStack(): CanvasAction[] {
    return this.history.slice(0, this.currentIndex + 1).reverse();
  }

  /**
   * Get actions that can be redone
   */
  getRedoStack(): CanvasAction[] {
    return this.history.slice(this.currentIndex + 1);
  }

  /**
   * Clear all history
   */
  clear(): void {
    this.history = [];
    this.currentIndex = -1;
  }

  /**
   * Create action types for common operations
   */
  static createActionTypes = {
    addElement: (element: any, description?: string) => ({
      type: 'add_element' as const,
      description: description || `Add ${element.type}`,
      data: {
        after: element,
        elementId: element.id
      }
    }),

    updateElement: (elementId: string, before: any, after: any, description?: string) => ({
      type: 'update_element' as const,
      description: description || `Update element`,
      data: {
        elementId,
        before,
        after
      }
    }),

    deleteElement: (element: any, description?: string) => ({
      type: 'delete_element' as const,
      description: description || `Delete ${element.type}`,
      data: {
        before: element,
        elementId: element.id
      }
    }),

    updateBackground: (before: string | null, after: string | null) => ({
      type: 'update_background' as const,
      description: after ? 'Add background image' : 'Remove background image',
      data: {
        before,
        after
      }
    }),

    updateSettings: (before: any, after: any, description?: string) => ({
      type: 'update_settings' as const,
      description: description || 'Update canvas settings',
      data: {
        before,
        after
      }
    }),

    updateElementProperty: (elementId: string, property: string, before: any, after: any) => ({
      type: 'update_element' as const,
      description: `Update element ${property}`,
      data: {
        elementId,
        before: { [property]: before },
        after: { [property]: after }
      }
    }),

    updateCanvasSettings: (property: string, before: any, after: any) => ({
      type: 'update_settings' as const,
      description: `Update canvas ${property}`,
      data: {
        before: { [property]: before },
        after: { [property]: after }
      }
    })
  };
}
