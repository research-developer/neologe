#!/usr/bin/env python3
"""
Example client for the Neologe API
Demonstrates how to use the neologism registration system
"""

import json
import urllib.request
import urllib.parse


class NeologeClient:
    """Simple client for interacting with the Neologe API"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None
    
    def _request(self, method, endpoint, data=None):
        """Make a request to the API"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        req_data = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_data = json.loads(e.read().decode('utf-8'))
            raise Exception(f"API Error {e.code}: {error_data.get('error', 'Unknown error')}")
    
    def register(self, username, email, password):
        """Register a new user"""
        return self._request('POST', '/auth/register', {
            'username': username,
            'email': email,
            'password': password
        })
    
    def login(self, username, password):
        """Login and store the access token"""
        result = self._request('POST', '/auth/login', {
            'username': username,
            'password': password
        })
        self.token = result['access_token']
        return result
    
    def submit_neologism(self, word, definition, context=None):
        """Submit a new neologism for evaluation"""
        data = {'word': word, 'user_definition': definition}
        if context:
            data['context'] = context
        return self._request('POST', '/neologisms', data)
    
    def list_neologisms(self):
        """Get list of user's neologisms"""
        return self._request('GET', '/neologisms')
    
    def get_neologism(self, neologism_id):
        """Get details of a specific neologism"""
        return self._request('GET', f'/neologisms/{neologism_id}')
    
    def resolve_conflict(self, neologism_id, choice, feedback=None):
        """Resolve conflicts for a neologism"""
        data = {'resolution_choice': choice}
        if feedback:
            data['user_feedback'] = feedback
        return self._request('POST', f'/neologisms/{neologism_id}/resolve', data)


def main():
    """Example usage of the Neologe API"""
    client = NeologeClient()
    
    print("=== Neologe API Example ===\n")
    
    # Register a user
    print("1. Registering a new user...")
    try:
        user = client.register("wordsmith", "wordsmith@example.com", "securepassword")
        print(f"✓ User registered: {user['username']}")
    except Exception as e:
        print(f"Registration failed (user may already exist): {e}")
    
    # Login
    print("\n2. Logging in...")
    try:
        login_result = client.login("wordsmith", "securepassword")
        print("✓ Login successful")
    except Exception as e:
        print(f"✗ Login failed: {e}")
        return
    
    # Submit a neologism
    print("\n3. Submitting a neologism...")
    neologism = client.submit_neologism(
        word="netiquette",
        definition="The etiquette or proper behavior expected in online communications and digital interactions",
        context="Often used when discussing appropriate behavior in emails, forums, and social media"
    )
    print(f"✓ Neologism submitted: '{neologism['word']}' (ID: {neologism['id']})")
    print(f"  Status: {neologism['status']}")
    
    # List neologisms
    print("\n4. Listing user's neologisms...")
    neologisms = client.list_neologisms()
    for n in neologisms:
        print(f"  - {n['word']} (Status: {n['status']}, Created: {n['created_at']})")
    
    # Get details of the neologism
    print(f"\n5. Getting details for neologism ID {neologism['id']}...")
    details = client.get_neologism(neologism['id'])
    print(f"  Word: {details['word']}")
    print(f"  Definition: {details['user_definition']}")
    print(f"  Context: {details['context']}")
    print(f"  Status: {details['status']}")
    
    # Resolve conflict if needed
    if details['status'] == 'conflict':
        print(f"\n6. Resolving conflict for '{details['word']}'...")
        resolution = client.resolve_conflict(
            neologism['id'],
            "accept_consensus",
            "I agree with the majority definition"
        )
        print(f"✓ {resolution['message']}")
    else:
        print(f"\n6. No conflict to resolve (status: {details['status']})")
    
    print("\n=== Example completed ===")


if __name__ == "__main__":
    print("Make sure the Neologe server is running:")
    print("python neologe_server.py")
    print()
    
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        print("Is the server running on http://localhost:8000?")