# Canvas Viewing Guide

This guide explains how to view live graphics through the CanvasView component and the routing system.

## Overview

The CanvasView component provides a read-only interface for displaying graphics with real-time tournament data. It can be accessed in two ways:

1. **Direct URL Access**: Via the `/canvas/view/{graphicId}` route
2. **Component Integration**: By embedding the CanvasView component in other pages

## Direct URL Access

### URL Pattern
```
http://localhost:3000/canvas/view/{graphicId}
```

### Parameters
- `graphicId` (required): The numeric ID of the graphic to display
  - Must be a valid integer
  - Cannot be NaN or undefined

### Examples
```bash
# View graphic with ID 1
http://localhost:3000/canvas/view/1

# View graphic with ID 42
http://localhost:3000/canvas/view/42
```

### Authentication
- **Public Endpoint**: No authentication required
- **Fallback**: If public endpoint fails, attempts authenticated access
- **Token Storage**: Uses existing auth tokens if available

## Component Integration

### Basic Usage
```tsx
import { CanvasView } from '@/components/canvas/CanvasView';

function MyComponent() {
  return (
    <CanvasView 
      graphicId={1}
      onError={(error) => console.error(error)}
      className="w-full h-full"
    />
  );
}
```

### Props Reference
```typescript
interface CanvasViewProps {
  graphicId: number;      // ID of the graphic to display (required)
  onError?: (error: string) => void;  // Error callback function (optional)
  className?: string;     // CSS className for styling (optional)
}
```

## Implementation Details

### Route Structure
The viewing route is implemented using Next.js App Router dynamic routing:

```
dashboard/app/canvas/view/[id]/page.tsx
```

This file:
1. Extracts the graphic ID from the URL parameters
2. Validates the ID (checks for NaN)
3. Renders the CanvasView component
4. Handles error states for invalid IDs

### API Endpoint Flow
1. **Primary Request**: GET `/api/graphics/{id}/view` (public endpoint)
2. **Fallback Request**: GET `/api/graphics/{id}` (authenticated endpoint)

### Data Flow
1. Route component extracts graphic ID from URL
2. CanvasView fetches graphic data from API
3. Canvas state is deserialized from JSON
4. Tournament data is fetched separately
5. Canvas renders with real-time data

## Error Handling

### Invalid Graphic ID
If the graphic ID is invalid (NaN, undefined, or not found):
- Displays error message: "Invalid Graphic ID"
- Shows user-friendly error description
- Provides guidance to check URL

### API Errors
- **404 Not Found**: Graphic doesn't exist
- **401 Unauthorized**: Authentication required for fallback
- **500 Server Error**: API processing error

### Loading States
- Shows spinner during data fetching
- Displays "Loading graphic..." message
- Handles both graphic and tournament data loading

## Development Features

### Debug Information
In development mode (NODE_ENV=development), CanvasView displays:
- Current graphic ID
- Number of elements
- Number of players
- Canvas dimensions

### Error Logging
- Detailed error logging to console
- Error callback for custom handling
- User-friendly error messages

## Performance Considerations

### Data Fetching
- Graphic data fetched on component mount
- Tournament data fetched with caching
- Automatic retry on failed requests

### Memory Management
- Component cleanup on unmount
- Proper error state handling
- No memory leaks from intervals

## Security

### Public Access
- No sensitive data in public endpoint
- Read-only access to graphics
- No edit capabilities

### Authentication
- Tokens stored securely in localStorage
- Automatic token refresh
- Secure API communication

## Troubleshooting

### Common Issues

1. **"Invalid Graphic ID" Error**
   - Check that the URL contains a valid number
   - Ensure the ID is not NaN
   - Verify the route is correct

2. **"Failed to load graphic" Error**
   - Check API backend is running
   - Verify graphic exists in database
   - Check network connection

3. **No Tournament Data**
   - Check tournament data is available
   - Verify API endpoint is working
   - Check sorting/filtering options

### Debugging Steps
1. Open browser developer tools
2. Check network tab for API requests
3. Verify API responses are successful
4. Check console for error messages
5. Verify graphic ID is valid

## Related Components

### BackgroundRenderer
- Renders canvas background
- Handles image loading
- Provides container for elements

### TextElementComponent
- Renders text elements
- Applies styling and positioning
- Handles read-only display

### DynamicListComponent
- Renders dynamic list elements
- Binds to tournament data
- Updates with real-time data

## Related Hooks

### useTournamentData
- Fetches player rankings
- Provides sorting options
- Handles data refresh

### useAuth
- Manages authentication state
- Provides token access
- Handles session management
