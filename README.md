# Nexus - AI Chat Platform

A full-stack AI-powered chat application built with FastAPI and React.

## 🌟 Overview

Nexus is a modern chat platform that enables users to have intelligent conversations with AI models. It features secure authentication, session management, file attachments, and an extensible tool system that allows AI to interact with external services.

## ✨ Key Features

### Authentication & Security
- **JWT-based Authentication** - Secure token-based auth
- **Refresh Token System** - Long-lived sessions (30 days)
- **Access Token Rotation** - Short-lived access tokens (2 hours)
- **Automatic Token Refresh** - Seamless user experience
- **IP Blocking** - Security middleware for suspicious activity
- **Rate Limiting** - API rate limiting protection

### Chat & AI
- **Multiple AI Models** - Support for various Groq models
- **Session Management** - Create and manage chat sessions
- **Conversation History** - Persistent message history
- **File Attachments** - Upload and process text files
- **Tool Orchestration** - AI can use external tools (calculator, weather, file creation, location)
- **Markdown Rendering** - Rich text responses

### User Experience
- **Responsive Design** - Works on all devices
- **Real-time Updates** - Instant message display
- **Toast Notifications** - User feedback
- **Error Handling** - Graceful error recovery

## 🏗️ Architecture

```
nexus/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API route handlers
│   │   ├── models/   # Database models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── services/ # Business logic
│   │   ├── agents/   # AI agent orchestration
│   │   ├── tools/     # AI tools (calculator, weather, etc.)
│   │   └── utils/    # Utilities
│   └── alembic/      # Database migrations
└── frontend/         # React frontend
    ├── src/
    │   ├── components/  # React components
    │   ├── contexts/    # React contexts
    │   ├── pages/       # Page components
    │   ├── repositories/# API clients
    │   └── lib/         # Utilities
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (for backend)
- **Node.js 18+** (for frontend)
- **Redis** (optional, for caching)
- **Groq API Key** (for AI features)

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the server:
```bash
uvicorn app.main:app --reload --port 8000
```

Backend API will be available at `http://localhost:8000`
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

## 📚 Documentation

### Backend Documentation

See [backend/README.md](./backend/README.md) for detailed backend documentation including:
- API endpoints
- Database migrations
- Configuration options
- Project structure

### Frontend Documentation

See [frontend/README.md](./frontend/README.md) for detailed frontend documentation including:
- Component structure
- Authentication flow
- API integration
- Deployment guide

## 🛠️ AI Tools

Nexus includes an extensible tool system that allows AI to interact with external services:

### Available Tools

1. **Calculator** - Perform mathematical calculations
2. **Weather** - Get weather information for locations
3. **File Creation** - Create and save files
4. **Location** - Get location information from IP

### Tool Orchestration

The system uses an agent-based approach:
1. **Tool Decision**: AI decides which tools to use
2. **Tool Execution**: Tools are executed programmatically
3. **Response Formatting**: AI formats final response with tool results

## 📡 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout (revoke refresh token)
- `GET /api/auth/me` - Get current user

### Sessions
- `GET /api/sessions/list` - List user's sessions
- `POST /api/sessions/create` - Create new session
- `GET /api/sessions/{id}/details` - Get session details
- `PUT /api/sessions/{id}/update` - Update session
- `DELETE /api/sessions/{id}/delete` - Delete session

### Messages
- `GET /api/sessions/{id}/messages/list` - Get messages
- `POST /api/sessions/{id}/messages/chat` - Send message and get AI response

### Models
- `GET /api/models` - List available AI models

### Users
- `GET /api/users/profile` - Get user profile
- `PUT /api/users/profile` - Update profile
- `PUT /api/users/password` - Change password
- `DELETE /api/users/account` - Delete account

### Transcription
- `POST /api/transcribe` - Transcribe audio to text

## 🗄️ Database

The application uses SQLite by default (can be configured for PostgreSQL):

### Models

- **User** - User accounts
- **ChatSession** - Chat sessions
- **Message** - Chat messages
- **File** - File attachments
- **RefreshToken** - Refresh token storage
- **BlockedIP** - Blocked IP addresses

### Migrations

Database migrations are managed with Alembic:

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 🧪 Development

### Backend Development

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm run dev
```
