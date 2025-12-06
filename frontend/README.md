# Nexus Frontend

A React + Vite + TypeScript application with shadcn/ui and Tailwind CSS v4.

## Tech Stack

- **React 19** - UI library
- **Vite 6** - Build tool and dev server
- **TypeScript** - Type safety
- **React Router** - Client-side routing
- **shadcn/ui** - UI component library
- **Tailwind CSS v4** - Styling
- **Lucide React** - Icons

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
npm install
```

### Environment Variables

Create a `.env` file in the root directory:

```env
VITE_API_URL=http://localhost:8000
```

### Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Build

Build for production:

```bash
npm run build
```

The production build will be in the `dist` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/     # React components
│   │   ├── auth/       # Authentication components
│   │   ├── chat/       # Chat interface components
│   │   ├── layout/     # Layout components
│   │   └── ui/         # shadcn/ui components
│   ├── contexts/       # React contexts
│   ├── hooks/          # Custom React hooks
│   ├── lib/            # Utility functions and API client
│   ├── pages/          # Page components
│   ├── App.tsx         # Main app component with routing
│   ├── main.tsx        # Entry point
│   └── index.css       # Global styles
├── public/             # Static assets
├── index.html          # HTML template
├── vite.config.ts      # Vite configuration
├── tsconfig.json       # TypeScript configuration
└── package.json        # Dependencies
```

## Features

- User authentication (login/register)
- Chat interface with AI
- Session management
- Responsive design
- Dark mode support (via next-themes)

## API Integration

The app communicates directly with the backend API. The API base URL is configured via the `VITE_API_URL` environment variable.

All API requests include credentials (cookies) for authentication.
