# Neologe - Neologism Registration API

An API-backed system that allows registered users to submit neologisms, which are then evaluated by multiple LLM providers and reviewed for conflicts.

## Features

- ✅ User registration and authentication
- ✅ Neologism submission and management  
- ✅ Integration with multiple LLM providers (OpenAI, Anthropic, Google)
- ✅ Automated conflict detection and resolution requests
- ✅ JSON-templated response format for word definitions
- ✅ SQLite database with proper schema
- ✅ Token-based authentication
- ✅ RESTful API design

## Quick Start

1. **Start the server:**
   ```bash
   python neologe_server.py
   ```

2. **Try the example client:**
   ```bash
   python example_client.py
   ```

3. **Run tests:**
   ```bash
   python test_api.py
   ```

## API Endpoints

- `POST /auth/register` - Register a new user
- `POST /auth/login` - User login
- `POST /neologisms/` - Submit a new neologism
- `GET /neologisms/` - List user's neologisms
- `GET /neologisms/{id}` - Get neologism details
- `POST /neologisms/{id}/resolve` - Resolve conflicts for a neologism

## How It Works

1. **User submits a neologism** with their definition and optional context
2. **Three LLM providers** (OpenAI, Anthropic, Google) analyze the word independently
3. **Each provider responds** with a standardized JSON format containing:
   - Definition, part of speech, etymology
   - Word variations (plural, adjective forms, etc.)
   - Usage examples and confidence score
4. **A single LLM evaluates** the three responses for conflicts
5. **If conflicts exist**, the user is notified and can resolve them
6. **Final status** is updated based on evaluation results

## LLM Response Format

```json
{
  "word": "technophilic",
  "definition": "Having a strong affinity for technology",
  "part_of_speech": "adjective",
  "etymology": "From Greek 'techno-' (art, skill) + 'philic' (loving)",
  "variations": {
    "noun": "technophile",
    "adverb": "technophilically"
  },
  "usage_examples": ["She has a technophilic approach to problem-solving."],
  "confidence": 0.92
}
```

## Example Usage

```python
from neologe_client import NeologeClient

# Initialize client
client = NeologeClient("http://localhost:8000")

# Register and login
client.register("wordsmith", "user@example.com", "password")
client.login("wordsmith", "password")

# Submit a neologism
result = client.submit_neologism(
    word="digitality",
    definition="The quality or state of being digital",
    context="Used in discussions about digital transformation"
)

# Check status and resolve conflicts if needed
if result['status'] == 'conflict':
    client.resolve_conflict(result['id'], "accept_consensus")
```

## Documentation

- See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed API documentation
- Run the server and visit `http://localhost:8000/` for endpoint reference

## Architecture

- **Backend**: Python with built-in libraries (http.server, sqlite3, json)
- **Database**: SQLite for development (easily replaceable with PostgreSQL/MySQL)
- **Authentication**: HMAC-based tokens with password hashing
- **LLM Integration**: HTTP clients for OpenAI, Anthropic, and Google APIs
- **Conflict Resolution**: Automated analysis with user override capabilities

## Status Values

- `pending` - Initial submission
- `evaluated` - LLM analysis complete, no conflicts
- `conflict` - Conflicts detected, user resolution required
- `resolved` - User has resolved conflicts
- `llm_error` - Error during LLM processing

## Production Notes

This implementation uses Python's built-in libraries for maximum compatibility. For production use, consider:

- Replace `http.server` with a proper WSGI server (Gunicorn, uvicorn)
- Use production database (PostgreSQL, MySQL)
- Configure real LLM API keys in `.env` file
- Add rate limiting, logging, and monitoring
- Implement proper CORS and security headers
