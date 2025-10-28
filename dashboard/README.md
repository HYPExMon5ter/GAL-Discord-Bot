# GAL Live Graphics Dashboard v2.0

A modern, password-gated web portal for managing live broadcast graphics. Built with Next.js 14, TypeScript, Tailwind CSS, and shadcn/ui.

## Features

### 🔐 Authentication
- Password-based login system
- JWT token authentication
- 15-minute session timeout
- Activity logging

### 🎨 Graphics Management
- Create, edit, duplicate, and delete graphics
- Canvas editing interface with lock management
- Real-time lock status with countdown timer
- Auto-expiring locks (5 minutes)

### 📦 Archive System
- Archive graphics safely
- Restore archived content
- Admin-only permanent deletion
- Archive statistics and metadata

### 🔒 Lock Management
- Single-user edit locks per graphic
- Simple toast notifications when attempting to edit locked content
- Auto-expiring locks (5 minutes)
- No visual lock indicators in the UI

## Technology Stack

- **Frontend**: Next.js 14 + TypeScript
- **UI**: Tailwind CSS + shadcn/ui components + Sonner for notifications
- **State Management**: React Hooks + Context API
- **API Integration**: Axios with FastAPI backend
- **Authentication**: JWT tokens with secure storage

### 📢 Notifications
- Modern Sonner toast system with 5-second auto-dismiss
- Clear, concise error messages for locked graphics
- Toast notifications for all user actions (save, delete, create, etc.)

## Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn
- FastAPI backend running on localhost:8000

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd dashboard
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.local.example .env.local
```

4. Start the development server:
```bash
npm run dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
dashboard/
├── app/                    # Next.js app router
│   ├── dashboard/         # Dashboard pages
│   ├── login/            # Login page
│   ├── globals.css       # Global styles
│   ├── layout.tsx        # Root layout
│   └── page.tsx          # Home page
├── components/           # React components
│   ├── ui/              # shadcn/ui base components
│   ├── auth/            # Authentication components
│   ├── graphics/        # Graphics management
│   ├── archive/         # Archive management
│   ├── canvas/          # Canvas editor
│   ├── layout/          # Layout components
│   └── locks/           # Lock management
├── hooks/               # Custom React hooks
├── lib/                 # Utility functions
├── types/               # TypeScript type definitions
└── utils/               # Helper functions
```

## API Integration

The frontend integrates with a FastAPI backend at `localhost:8000`. Key endpoints:

- `POST /api/login` - Authentication
- `GET /api/graphics` - List graphics
- `POST /api/graphics` - Create graphic
- `PUT /api/graphics/{id}` - Update graphic
- `DELETE /api/graphics/{id}` - Delete graphic
- `POST /api/archive/{id}` - Archive graphic
- `POST /api/archive/{id}/restore` - Restore graphic
- `POST /api/lock/{graphic_id}` - Acquire edit lock
- `DELETE /api/lock/{graphic_id}` - Release edit lock

## Usage

### Login
1. Navigate to the dashboard URL
2. Enter your username and password
3. Session expires after 15 minutes of inactivity

### Managing Graphics
1. **Create**: Click "Create Graphic" to add new content
2. **Edit**: Click "Edit" on any unlocked graphic
3. **Lock System**: Only one user can edit at a time
4. **Lock Status**: Visual indicators show who is editing
5. **Auto-expiry**: Locks expire after 5 minutes

### Archive Management
1. **Archive**: Move unused graphics to archive
2. **Restore**: Bring back archived graphics
3. **Delete**: Admins can permanently delete archived items

## Development

### Available Scripts
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

### Component Development
- Use shadcn/ui components for consistency
- Follow TypeScript best practices
- Implement proper error handling
- Ensure responsive design

### State Management
- Use custom hooks for API calls
- Context API for authentication
- Local state for component interactions
- Proper loading and error states

## Security Considerations

- JWT tokens stored securely in localStorage
- Automatic session timeout
- API request/response interceptors
- Lock-based editing prevents conflicts
- Admin-only destructive operations

## Future Enhancements

- [ ] Real canvas editor implementation
- [ ] WebSocket support for live updates
- [ ] Advanced drawing tools
- [ ] Template system
- [ ] Export/import functionality
- [ ] Multi-language support
- [ ] Dark mode toggle

## Contributing

1. Follow the existing code style
2. Add TypeScript types for new components
3. Test thoroughly before submitting
4. Update documentation as needed

## License

© Guardian Angel League - All Rights Reserved
