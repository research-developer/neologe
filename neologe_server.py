#!/usr/bin/env python3
"""
Neologe - Neologism Registration API
A simplified implementation using only Python standard library
"""

import json
import sqlite3
import hashlib
import secrets
import hmac
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import threading
import os


class Database:
    def __init__(self, db_path="neologe.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Neologisms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS neologisms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                user_definition TEXT NOT NULL,
                context TEXT,
                status TEXT DEFAULT 'pending',
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # LLM Responses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS llm_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                neologism_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                response_data TEXT NOT NULL,
                confidence INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (neologism_id) REFERENCES neologisms (id)
            )
        ''')
        
        # Evaluations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                neologism_id INTEGER NOT NULL,
                conflicts_detected TEXT,
                resolution_required INTEGER DEFAULT 0,
                evaluator_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (neologism_id) REFERENCES neologisms (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)


class AuthService:
    SECRET_KEY = "neologe-secret-key-change-in-production"
    
    @staticmethod
    def hash_password(password):
        salt = secrets.token_hex(16)
        pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return salt + pwdhash.hex()
    
    @staticmethod
    def verify_password(stored_password, provided_password):
        salt = stored_password[:32]
        stored_hash = stored_password[32:]
        pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return pwdhash.hex() == stored_hash
    
    @staticmethod
    def create_token(username):
        payload = {
            'username': username,
            'exp': int(time.time()) + 3600  # 1 hour expiry
        }
        message = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            AuthService.SECRET_KEY.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"{message}.{signature}"
    
    @staticmethod
    def verify_token(token):
        try:
            parts = token.split('.')
            if len(parts) != 2:
                return None
            
            message, signature = parts
            expected_sig = hmac.new(
                AuthService.SECRET_KEY.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_sig):
                return None
            
            payload = json.loads(message)
            if payload['exp'] < time.time():
                return None
            
            return payload['username']
        except:
            return None


class LLMService:
    """Mock LLM service - in production this would call real LLM APIs"""
    
    @staticmethod
    def get_mock_definition(word, user_definition, provider="mock"):
        """Generate a mock LLM response"""
        return {
            "word": word,
            "definition": f"A {provider} definition: {user_definition}",
            "part_of_speech": "noun",
            "etymology": f"Possibly derived from existing linguistic patterns",
            "variations": {
                "plural": f"{word}s",
                "adjective": f"{word}ish"
            },
            "usage_examples": [f"The {word} was quite remarkable."],
            "confidence": 0.8
        }
    
    @staticmethod
    def get_definitions(word, user_definition, context=None):
        """Get definitions from mock LLM providers"""
        providers = ["openai", "anthropic", "google"]
        responses = []
        
        for provider in providers:
            try:
                response_data = LLMService.get_mock_definition(word, user_definition, provider)
                responses.append({
                    "provider": provider,
                    "response": response_data,
                    "success": True
                })
            except Exception as e:
                responses.append({
                    "provider": provider,
                    "error": str(e),
                    "success": False
                })
        
        return responses
    
    @staticmethod
    def evaluate_conflicts(word, responses):
        """Mock conflict evaluation"""
        conflicts = []
        
        # Simple mock conflict detection
        definitions = [r["response"]["definition"] for r in responses if r["success"]]
        if len(set(definitions)) > 1:
            conflicts.append("Different definitions provided by LLM providers")
        
        return {
            "conflicts_detected": conflicts,
            "resolution_required": len(conflicts) > 0,
            "overall_confidence": 0.7,
            "recommended_definition": definitions[0] if definitions else "No definition available",
            "notes": f"Evaluated {len(responses)} responses for word '{word}'"
        }


class NeologeHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, database=None, **kwargs):
        self.database = database
        super().__init__(*args, **kwargs)
    
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_headers()
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            self._handle_root()
        elif path == '/health':
            self._handle_health()
        elif path.startswith('/neologisms'):
            self._handle_get_neologisms(path)
        else:
            self._send_error(404, "Not Found")
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON")
            return
        
        if path == '/auth/register':
            self._handle_register(data)
        elif path == '/auth/login':
            self._handle_login(data)
        elif path == '/neologisms':
            self._handle_create_neologism(data)
        elif path.startswith('/neologisms/') and path.endswith('/resolve'):
            neologism_id = path.split('/')[-2]
            self._handle_resolve_conflict(neologism_id, data)
        else:
            self._send_error(404, "Not Found")
    
    def _handle_root(self):
        self._set_headers()
        response = {
            "message": "Welcome to Neologe API",
            "version": "1.0.0",
            "endpoints": {
                "POST /auth/register": "Register a new user",
                "POST /auth/login": "User login",
                "POST /neologisms": "Submit a new neologism",
                "GET /neologisms": "List user's neologisms",
                "GET /neologisms/{id}": "Get neologism details",
                "POST /neologisms/{id}/resolve": "Resolve conflicts"
            }
        }
        self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
    
    def _handle_health(self):
        self._set_headers()
        self.wfile.write(json.dumps({"status": "healthy"}).encode('utf-8'))
    
    def _handle_register(self, data):
        if not all(key in data for key in ['username', 'email', 'password']):
            self._send_error(400, "Missing required fields")
            return
        
        conn = self.database.get_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", 
                      (data['username'], data['email']))
        if cursor.fetchone():
            self._send_error(400, "Username or email already exists")
            conn.close()
            return
        
        # Create user
        password_hash = AuthService.hash_password(data['password'])
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (data['username'], data['email'], password_hash)
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self._set_headers(201)
        response = {
            "id": user_id,
            "username": data['username'],
            "email": data['email']
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def _handle_login(self, data):
        if not all(key in data for key in ['username', 'password']):
            self._send_error(400, "Missing username or password")
            return
        
        conn = self.database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (data['username'],))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not AuthService.verify_password(result[0], data['password']):
            self._send_error(401, "Invalid credentials")
            return
        
        token = AuthService.create_token(data['username'])
        self._set_headers()
        response = {
            "access_token": token,
            "token_type": "bearer"
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def _get_current_user(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        username = AuthService.verify_token(token)
        if not username:
            return None
        
        conn = self.database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {"id": result[0], "username": result[1], "email": result[2]}
        return None
    
    def _handle_create_neologism(self, data):
        user = self._get_current_user()
        if not user:
            self._send_error(401, "Authentication required")
            return
        
        if not all(key in data for key in ['word', 'user_definition']):
            self._send_error(400, "Missing word or definition")
            return
        
        conn = self.database.get_connection()
        cursor = conn.cursor()
        
        # Create neologism
        cursor.execute(
            "INSERT INTO neologisms (word, user_definition, context, user_id, status) VALUES (?, ?, ?, ?, 'pending')",
            (data['word'], data['user_definition'], data.get('context'), user['id'])
        )
        neologism_id = cursor.lastrowid
        
        try:
            # Get LLM responses
            llm_responses = LLMService.get_definitions(
                data['word'], data['user_definition'], data.get('context')
            )
            
            successful_responses = []
            for response in llm_responses:
                if response["success"]:
                    cursor.execute(
                        "INSERT INTO llm_responses (neologism_id, provider, response_data, confidence) VALUES (?, ?, ?, ?)",
                        (neologism_id, response["provider"], json.dumps(response["response"]), 
                         int(response["response"]["confidence"] * 100))
                    )
                    successful_responses.append(response)
            
            # Evaluate conflicts
            if len(successful_responses) >= 2:
                evaluation = LLMService.evaluate_conflicts(data['word'], successful_responses)
                cursor.execute(
                    "INSERT INTO evaluations (neologism_id, conflicts_detected, resolution_required, evaluator_response) VALUES (?, ?, ?, ?)",
                    (neologism_id, json.dumps(evaluation.get("conflicts_detected", [])), 
                     1 if evaluation.get("resolution_required", False) else 0,
                     json.dumps(evaluation))
                )
                
                status = "conflict" if evaluation.get("resolution_required", False) else "evaluated"
                cursor.execute("UPDATE neologisms SET status = ? WHERE id = ?", (status, neologism_id))
            
            conn.commit()
            
        except Exception as e:
            cursor.execute("UPDATE neologisms SET status = 'llm_error' WHERE id = ?", (neologism_id,))
            conn.commit()
        
        # Get the created neologism
        cursor.execute("SELECT * FROM neologisms WHERE id = ?", (neologism_id,))
        result = cursor.fetchone()
        conn.close()
        
        self._set_headers(201)
        response = {
            "id": result[0],
            "word": result[1],
            "user_definition": result[2],
            "context": result[3],
            "status": result[4],
            "user_id": result[5],
            "created_at": result[6],
            "updated_at": result[7]
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def _handle_get_neologisms(self, path):
        user = self._get_current_user()
        if not user:
            self._send_error(401, "Authentication required")
            return
        
        conn = self.database.get_connection()
        cursor = conn.cursor()
        
        if path == '/neologisms':
            # List all neologisms for user
            cursor.execute(
                "SELECT id, word, status, created_at FROM neologisms WHERE user_id = ? ORDER BY created_at DESC",
                (user['id'],)
            )
            results = cursor.fetchall()
            neologisms = [
                {"id": r[0], "word": r[1], "status": r[2], "created_at": r[3]}
                for r in results
            ]
        else:
            # Get specific neologism
            neologism_id = path.split('/')[-1]
            cursor.execute(
                "SELECT * FROM neologisms WHERE id = ? AND user_id = ?",
                (neologism_id, user['id'])
            )
            result = cursor.fetchone()
            if not result:
                conn.close()
                self._send_error(404, "Neologism not found")
                return
            
            neologisms = {
                "id": result[0],
                "word": result[1],
                "user_definition": result[2],
                "context": result[3],
                "status": result[4],
                "user_id": result[5],
                "created_at": result[6],
                "updated_at": result[7]
            }
        
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps(neologisms).encode('utf-8'))
    
    def _handle_resolve_conflict(self, neologism_id, data):
        user = self._get_current_user()
        if not user:
            self._send_error(401, "Authentication required")
            return
        
        conn = self.database.get_connection()
        cursor = conn.cursor()
        
        # Verify neologism exists and belongs to user
        cursor.execute(
            "SELECT status FROM neologisms WHERE id = ? AND user_id = ?",
            (neologism_id, user['id'])
        )
        result = cursor.fetchone()
        if not result:
            conn.close()
            self._send_error(404, "Neologism not found")
            return
        
        if result[0] != 'conflict':
            conn.close()
            self._send_error(400, "Neologism is not in conflict status")
            return
        
        # Update evaluation with resolution
        cursor.execute(
            "UPDATE evaluations SET evaluator_response = json_set(evaluator_response, '$.user_resolution', ?) WHERE neologism_id = ?",
            (json.dumps(data), neologism_id)
        )
        
        # Update neologism status
        cursor.execute("UPDATE neologisms SET status = 'resolved' WHERE id = ?", (neologism_id,))
        
        conn.commit()
        conn.close()
        
        self._set_headers()
        self.wfile.write(json.dumps({"message": "Conflict resolved successfully"}).encode('utf-8'))
    
    def _send_error(self, status, message):
        self._set_headers(status)
        response = {"error": message}
        self.wfile.write(json.dumps(response).encode('utf-8'))


def create_handler_class(database):
    class Handler(NeologeHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, database=database, **kwargs)
    return Handler


def main():
    # Initialize database
    database = Database()
    
    # Create server
    handler_class = create_handler_class(database)
    server = HTTPServer(('localhost', 8000), handler_class)
    
    print("Starting Neologe API server on http://localhost:8000")
    print("API Documentation available at /")
    print("Health check available at /health")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    main()