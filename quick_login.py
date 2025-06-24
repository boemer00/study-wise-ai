#!/usr/bin/env python3
"""
Quick login script to get fresh JWT tokens for testing
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def quick_login(email, password):
    """Login and get fresh token"""
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful for {email}")
            print(f"User ID: {data['user_id']}")
            print(f"Token: {data['access_token']}")
            print(f"\nUse this token in Authorization header:")
            print(f"Authorization: Bearer {data['access_token']}")
            return data['access_token']
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def register_and_login(email, password):
    """Register new user and login"""
    try:
        # Try to register
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": email,
            "password": password
        })
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ Registration successful for {email}")
            print(f"User ID: {data['user_id']}")
            print(f"Token: {data['access_token']}")
            return data['access_token']
        elif response.status_code == 400 and "already registered" in response.text:
            print(f"ℹ️ User {email} already exists, trying login...")
            return quick_login(email, password)
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None

if __name__ == "__main__":
    print("🔐 StudyWise AI Quick Login")
    print("=" * 30)
    
    # Test existing user
    print("\n1️⃣ Testing existing user:")
    token1 = quick_login("test3@example.com", "test123")
    
    # Create a new user
    print("\n2️⃣ Creating new test user:")
    token2 = register_and_login("newuser@example.com", "password123")
    
    print("\n📋 Available test users:")
    print("- test3@example.com / test123")
    print("- newuser@example.com / password123")
    
    print("\n🧪 To test document upload:")
    if token2:
        print(f"""curl -X POST "http://localhost:8000/api/v1/documents/upload" \\
  -H "Authorization: Bearer {token2}" \\
  -F "file=@test_python_basics.pdf" \\
  -F "title=My Test Document" \\
  -F "generate_flashcards=true" """)