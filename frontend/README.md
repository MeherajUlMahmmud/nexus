# Nexus Frontend

A modern React application built with Vite, TypeScript, and shadcn/ui for the Nexus AI chat platform.

## 🚀 Tech Stack

- **React 19** - Modern UI library with latest features
- **Vite 6** - Fast build tool and dev server
- **TypeScript** - Type-safe development
- **React Router 7** - Client-side routing
- **shadcn/ui** - Beautiful, accessible UI components
- **Tailwind CSS v4** - Utility-first CSS framework
- **Axios** - HTTP client for API requests
- **React Hook Form** - Form state management
- **Zod** - Schema validation
- **Sonner** - Toast notifications
- **Lucide React** - Icon library
- **React Markdown** - Markdown rendering for AI responses

## 📋 Prerequisites

- **Node.js** 18+ (recommended: 20+)
- **npm** or **yarn** or **pnpm**

## 🛠️ Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

## ⚙️ Environment Variables

Create a `.env` file in the `frontend` directory:

```env
# Backend API URL
VITE_API_URL=http://localhost:8000/api
```

## 🏃 Development

Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:5173` (or the next available port).

### Development Features

- **Hot Module Replacement (HMR)** - Instant updates during development
- **TypeScript** - Full type checking
- **ESLint** - Code linting and quality checks

## 🏗️ Build

Build for production:

```bash
npm run build
```

The production build will be in the `dist` directory, optimized and minified.

## 👀 Preview Production Build

Preview the production build locally:

```bash
npm run preview
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── auth/           # Authentication components
│   │   │   ├── AuthGuard.tsx
│   │   │   └── RegisterForm.tsx
│   │   ├── chat/           # Chat interface components
│   │   │   ├── ChatHeader.tsx
│   │   │   ├── ChatInputArea.tsx
│   │   │   ├── MessageItem.tsx
│   │   │   └── ...
│   │   ├── layout/          # Layout components
│   │   │   ├── AppLayout.tsx
│   │   │   ├── AuthLayout.tsx
│   │   │   └── ChatSidebar.tsx
│   │   └── ui/              # shadcn/ui components (53 components)
│   ├── contexts/            # React contexts
│   │   ├── AuthContext.tsx  # Authentication state
│   │   ├── ModelContext.tsx # AI model selection
│   │   └── SessionContext.tsx # Chat session management
│   ├── hooks/               # Custom React hooks
│   │   └── use-mobile.ts    # Mobile detection hook
│   ├── lib/                 # Utility functions and constants
│   │   ├── constants.ts     # API routes and app routes
│   │   ├── storage.ts       # LocalStorage utilities
│   │   ├── types.ts         # TypeScript type definitions
│   │   └── utils.ts         # Helper functions
│   ├── pages/               # Page components
│   │   ├── auth/            # Authentication pages
│   │   │   ├── LoginPage.tsx
│   │   │   └── RegisterPage.tsx
│   │   ├── chat/            # Chat pages
│   │   │   ├── ChatPage.tsx
│   │   │   └── ChatSessionPage.tsx
│   │   └── profile/         # User profile pages
│   │       ├── ProfilePage.tsx
│   │       ├── SettingsPage.tsx
│   │       └── AccountSettingsPage.tsx
│   ├── repositories/        # API client layer
│   │   ├── apiHandler.ts    # HTTP request handler with token refresh
│   │   ├── auth.ts          # Authentication API
│   │   ├── message.ts       # Messages API
│   │   ├── session.ts       # Sessions API
│   │   ├── user.ts          # User API
│   │   ├── models.ts        # AI models API
│   │   └── transcribe.ts    # Transcription API
│   ├── App.tsx              # Main app component with routing
│   ├── main.tsx             # Application entry point
│   └── index.css            # Global styles
├── public/                  # Static assets
├── index.html               # HTML template
├── vite.config.ts           # Vite configuration
├── tsconfig.json            # TypeScript configuration
├── postcss.config.mjs        # PostCSS configuration
├── components.json          # shadcn/ui configuration
└── package.json             # Dependencies and scripts
```

## ✨ Features

### Authentication
- **User Registration** - Create new accounts
- **User Login** - Secure authentication
- **Token Management** - Automatic access token refresh
  - Access tokens valid for 2 hours
  - Refresh tokens valid for 30 days
  - Automatic token refresh on 401 errors
  - Queue system for concurrent requests during refresh
- **Protected Routes** - Route guards for authenticated pages
- **Session Persistence** - Maintains login state across page refreshes

### Chat Interface
- **AI Conversations** - Chat with various AI models
- **Session Management** - Create, view, and manage chat sessions
- **Message History** - View conversation history
- **File Attachments** - Upload and attach text files to messages
- **Markdown Rendering** - Rich text rendering for AI responses
- **Message Metadata** - View tool usage and model information
- **Real-time Updates** - Instant message display

### User Experience
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Toast Notifications** - User feedback for actions
- **Loading States** - Visual feedback during API calls
- **Error Handling** - Graceful error messages and recovery

## 🔌 API Integration

The frontend communicates with the backend API through a repository pattern:

- **API Handler** (`apiHandler.ts`) - Centralized HTTP client with:
  - Automatic token injection
  - Token refresh on 401 errors
  - Request/response interceptors
  - Error handling

- **Repositories** - Domain-specific API clients:
  - `auth.ts` - Authentication endpoints
  - `message.ts` - Chat messages
  - `session.ts` - Chat sessions
  - `user.ts` - User management
  - `models.ts` - AI models
  - `transcribe.ts` - Audio transcription

## 🎨 Styling

- **Tailwind CSS v4** - Utility-first CSS
- **shadcn/ui** - Pre-built accessible components
- **CSS Variables** - Theme customization
- **Responsive Breakpoints** - Mobile-first design
