# Nexus Backend

FastAPI backend for the Nexus chat application with AI-powered conversations.

## Requirements

- Python 3.10+
- Redis (optional, for caching)

## Quick Start

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file in the backend directory:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./chat_app.db

# JWT Settings
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Groq API (required for AI chat)
GROQ_API_KEY=your-groq-api-key

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
REDIS_ENABLED=false

# Environment
ENVIRONMENT=development
```

### 4. Run Database Migrations

```bash
alembic upgrade head
```

### 5. Start the Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Migrations

This project uses Alembic for database migrations. See [MIGRATIONS.md](./MIGRATIONS.md) for detailed instructions.

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Project Structure

```
backend/
├── alembic/              # Database migrations
│   └── versions/         # Migration scripts
├── app/
│   ├── api/              # API route handlers
│   ├── middleware/       # Custom middleware
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── utils/            # Utility functions
│   ├── config.py         # App configuration
│   ├── database.py       # Database setup
│   ├── exceptions.py     # Custom exceptions
│   └── main.py           # FastAPI app entry point
├── uploads/              # Uploaded files (gitignored)
├── alembic.ini           # Alembic configuration
├── requirements.txt      # Python dependencies
└── README.md
```

## Key Features

- **Authentication**: JWT-based authentication
- **Chat Sessions**: Create and manage chat sessions
- **AI Integration**: Groq API for AI-powered responses
- **File Uploads**: Support for text file attachments
- **Audio Transcription**: Voice message transcription
- **Rate Limiting**: Request rate limiting
- **IP Blocking**: Security middleware for suspicious activity

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/refresh` - Refresh access token

### Users
- `GET /api/users/me` - Get current user profile
- `PUT /api/users/me` - Update current user

### Sessions
- `GET /api/sessions/list` - List user's chat sessions
- `POST /api/sessions/create` - Create new session
- `GET /api/sessions/{id}/details` - Get session details
- `PUT /api/sessions/{id}/update` - Update session
- `DELETE /api/sessions/{id}/delete` - Delete session

### Messages
- `GET /api/sessions/{id}/messages/list` - Get session messages
- `POST /api/sessions/{id}/messages/chat` - Send message and get AI response

### Models
- `GET /api/models/list` - List available AI models

### Transcription
- `POST /api/transcribe` - Transcribe audio to text

