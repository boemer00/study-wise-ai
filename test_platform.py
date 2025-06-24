#!/usr/bin/env python3
"""
StudyWise AI Platform Testing Script
Demonstrates the full workflow of the platform
"""

import requests
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_platform():
    print("🧪 StudyWise AI Platform Testing")
    print("=" * 40)
    
    # Test 1: Health Check
    print("\n1️⃣ Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return
    
    # Test 2: User Registration
    print("\n2️⃣ Testing User Registration...")
    user_data = {
        "email": "testuser@studywise.ai",
        "password": "securetest123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=user_data)
        if response.status_code in [200, 201]:
            auth_data = response.json()
            print("✅ User registration successful")
            print(f"   User ID: {auth_data['user_id']}")
            token = auth_data['access_token']
            headers = {"Authorization": f"Bearer {token}"}
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return
    
    # Test 3: List Documents (should be empty for new user)
    print("\n3️⃣ Testing Document Listing...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/documents/", headers=headers)
        if response.status_code == 200:
            documents = response.json()
            print(f"✅ Document listing successful")
            print(f"   Found {len(documents.get('documents', []))} documents")
        else:
            print(f"❌ Document listing failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Document listing error: {e}")
    
    # Test 4: Document Upload (if test file exists)
    print("\n4️⃣ Testing Document Upload...")
    test_file = Path("test_python_basics.pdf")
    if test_file.exists():
        try:
            with open(test_file, 'rb') as f:
                files = {'file': (test_file.name, f, 'application/pdf')}
                data = {'title': 'Test Document', 'generate_flashcards': 'true'}
                
                response = requests.post(
                    f"{BASE_URL}/api/v1/documents/upload",
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code in [200, 201]:
                    upload_result = response.json()
                    print("✅ Document upload successful")
                    print(f"   Document ID: {upload_result.get('document_id')}")
                    print(f"   Status: {upload_result.get('status')}")
                    print(f"   Chunks created: {upload_result.get('chunks_created', 0)}")
                else:
                    print(f"❌ Document upload failed: {response.status_code}")
                    print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Document upload error: {e}")
    else:
        print(f"⚠️ Test file {test_file} not found, skipping upload test")
    
    # Test 5: List Documents Again
    print("\n5️⃣ Re-testing Document Listing...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/documents/", headers=headers)
        if response.status_code == 200:
            documents = response.json()
            print(f"✅ Document listing successful")
            print(f"   Found {len(documents.get('documents', []))} documents")
            for doc in documents.get('documents', [])[:3]:  # Show first 3
                print(f"   - {doc.get('title')} ({doc.get('status')})")
        else:
            print(f"❌ Document listing failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Document listing error: {e}")
    
    # Test 6: Flashcard Listing
    print("\n6️⃣ Testing Flashcard Listing...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/flashcards/", headers=headers)
        if response.status_code == 200:
            flashcards = response.json()
            print(f"✅ Flashcard listing successful")
            print(f"   Found {len(flashcards)} flashcards")
        else:
            print(f"❌ Flashcard listing failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Flashcard listing error: {e}")
    
    print("\n🎉 Platform testing completed!")
    print("\n💡 Next steps:")
    print("1. Start the frontend: cd ../study-wise-frontend && npm run dev")
    print("2. Open http://localhost:5173 in your browser")
    print("3. Use the credentials above to login and test the UI")
    print(f"   Email: {user_data['email']}")
    print(f"   Password: {user_data['password']}")

if __name__ == "__main__":
    test_platform()