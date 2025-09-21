#!/usr/bin/env python3
"""
Test script for Neologe API
"""

import json
import urllib.request
import urllib.parse
import time


class NeologeAPIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None
    
    def _make_request(self, method, endpoint, data=None, headers=None):
        url = f"{self.base_url}{endpoint}"
        
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        if self.token and 'Authorization' not in headers:
            headers['Authorization'] = f'Bearer {self.token}'
        
        req_data = None
        if data:
            req_data = json.dumps(data).encode('utf-8')
        
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_data = json.loads(error_body)
                print(f"HTTP {e.code} Error: {error_data}")
            except:
                print(f"HTTP {e.code} Error: {error_body}")
            return None
    
    def register(self, username, email, password):
        return self._make_request('POST', '/auth/register', {
            'username': username,
            'email': email,
            'password': password
        })
    
    def login(self, username, password):
        result = self._make_request('POST', '/auth/login', {
            'username': username,
            'password': password
        })
        if result and 'access_token' in result:
            self.token = result['access_token']
        return result
    
    def submit_neologism(self, word, definition, context=None):
        data = {
            'word': word,
            'user_definition': definition
        }
        if context:
            data['context'] = context
        return self._make_request('POST', '/neologisms', data)
    
    def list_neologisms(self):
        return self._make_request('GET', '/neologisms')
    
    def get_neologism(self, neologism_id):
        return self._make_request('GET', f'/neologisms/{neologism_id}')
    
    def resolve_conflict(self, neologism_id, choice, feedback=None):
        data = {'resolution_choice': choice}
        if feedback:
            data['user_feedback'] = feedback
        return self._make_request('POST', f'/neologisms/{neologism_id}/resolve', data)


def test_api():
    """Test the Neologe API functionality"""
    print("Testing Neologe API...")
    
    client = NeologeAPIClient()
    
    # Test health check
    print("\n1. Testing health check...")
    health = client._make_request('GET', '/health')
    print(f"Health check: {health}")
    
    # Test registration
    print("\n2. Testing user registration...")
    test_user = {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpassword123'
    }
    
    register_result = client.register(**test_user)
    print(f"Registration result: {register_result}")
    
    # Test login
    print("\n3. Testing user login...")
    login_result = client.login(test_user['username'], test_user['password'])
    print(f"Login result: {login_result}")
    
    if not login_result:
        print("Login failed, cannot continue tests")
        return
    
    # Test neologism submission
    print("\n4. Testing neologism submission...")
    neologism_data = {
        'word': 'technophilic',
        'definition': 'Having a strong affinity or love for technology and technological advancement',
        'context': 'Used to describe people who embrace new technologies enthusiastically'
    }
    
    submission_result = client.submit_neologism(**neologism_data)
    print(f"Neologism submission: {submission_result}")
    
    if submission_result:
        neologism_id = submission_result['id']
        
        # Test listing neologisms
        print("\n5. Testing neologism listing...")
        list_result = client.list_neologisms()
        print(f"Neologisms list: {list_result}")
        
        # Test getting specific neologism
        print("\n6. Testing specific neologism retrieval...")
        get_result = client.get_neologism(neologism_id)
        print(f"Specific neologism: {get_result}")
        
        # Test conflict resolution (if applicable)
        if get_result and get_result.get('status') == 'conflict':
            print("\n7. Testing conflict resolution...")
            resolve_result = client.resolve_conflict(
                neologism_id, 
                'accept_provider_1', 
                'I prefer the first definition'
            )
            print(f"Conflict resolution: {resolve_result}")
    
    print("\nAPI tests completed!")


if __name__ == "__main__":
    print("Make sure the Neologe server is running on http://localhost:8000")
    print("Run: python neologe_server.py")
    print("\nPress Enter to start tests, or Ctrl+C to cancel...")
    
    try:
        input()
        test_api()
    except KeyboardInterrupt:
        print("\nTests cancelled.")