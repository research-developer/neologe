# Neologe API Documentation

## Overview

Neologe is an API-backed system that allows registered users to submit neologisms (new words), which are then evaluated by multiple LLM providers and reviewed for conflicts.

## Architecture

The system implements the following workflow:

1. **User Registration/Authentication**: Users register and authenticate to submit neologisms
2. **Neologism Submission**: Users submit new words with definitions and optional context
3. **LLM Evaluation**: Three LLM providers analyze the word and provide standardized definitions
4. **Conflict Detection**: A separate LLM evaluates differences between provider responses
5. **Resolution Process**: If conflicts are detected, users are notified and can resolve them

## API Endpoints

### Authentication

#### Register User
```
POST /auth/register
Content-Type: application/json

{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

#### Login
```
POST /auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}

Response:
{
  "access_token": "string",
  "token_type": "bearer"
}
```

### Neologisms

#### Submit Neologism
```
POST /neologisms
Authorization: Bearer <token>
Content-Type: application/json

{
  "word": "string",
  "user_definition": "string",
  "context": "string" (optional)
}
```

#### List User's Neologisms
```
GET /neologisms
Authorization: Bearer <token>

Response:
[
  {
    "id": 1,
    "word": "string",
    "status": "string",
    "created_at": "timestamp"
  }
]
```

#### Get Neologism Details
```
GET /neologisms/{id}
Authorization: Bearer <token>

Response:
{
  "id": 1,
  "word": "string",
  "user_definition": "string",
  "context": "string",
  "status": "string",
  "user_id": 1,
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

#### Resolve Conflict
```
POST /neologisms/{id}/resolve
Authorization: Bearer <token>
Content-Type: application/json

{
  "resolution_choice": "string",
  "user_feedback": "string" (optional)
}
```

## Status Values

- `pending`: Initial status when neologism is submitted
- `evaluated`: LLM evaluation completed without conflicts
- `conflict`: Conflicts detected between LLM responses, requires user resolution
- `resolved`: User has resolved conflicts
- `llm_error`: Error occurred during LLM processing

## LLM Response Format

Each LLM provider responds with a standardized JSON format:

```json
{
  "word": "example",
  "definition": "A representative case or illustration",
  "part_of_speech": "noun",
  "etymology": "From Latin exemplum",
  "variations": {
    "plural": "examples",
    "adjective": "exemplary"
  },
  "usage_examples": ["This is an example sentence."],
  "confidence": 0.95
}
```

## Running the Server

1. Start the server:
   ```bash
   python neologe_server.py
   ```

2. The API will be available at `http://localhost:8000`

3. API documentation is available at the root endpoint `/`

## Example Usage

See `example_client.py` for a complete example of how to use the API.

## Database Schema

The system uses SQLite with the following tables:

- `users`: User accounts and authentication
- `neologisms`: Submitted words and their metadata
- `llm_responses`: Responses from LLM providers
- `evaluations`: Conflict analysis and resolution data

## Security Features

- Password hashing using PBKDF2 with salt
- JWT-like token authentication with HMAC signatures
- User isolation (users can only access their own neologisms)
- Input validation and sanitization

## Production Considerations

For production deployment, consider:

1. Replace the simple HTTP server with a proper WSGI server (e.g., Gunicorn)
2. Use a production database (PostgreSQL, MySQL)
3. Configure proper API keys for LLM providers
4. Implement rate limiting and proper CORS policies
5. Add comprehensive logging and monitoring
6. Use HTTPS and secure the secret key
7. Add input validation and sanitization
8. Implement proper error handling and user feedback