#!/usr/bin/env python3
"""
StudyWise AI Full Stack Startup Guide
Instructions for running both backend and frontend
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🚀 StudyWise AI Full Stack Setup Guide")
    print("=" * 50)
    
    # Check backend status
    print("\n📡 BACKEND STATUS:")
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✅ Backend is running at http://localhost:8000")
            print("📚 API Docs: http://localhost:8000/docs")
        else:
            print("❌ Backend is not responding correctly")
    except:
        print("❌ Backend is not running")
        print("💡 To start backend, run: python start_backend.py")
    
    # Frontend instructions
    print("\n🌐 FRONTEND SETUP:")
    frontend_path = Path("../study-wise-frontend")
    if frontend_path.exists():
        print(f"✅ Frontend found at: {frontend_path.absolute()}")
        print("\n📋 To start the frontend:")
        print("1. Open a new terminal")
        print("2. cd ../study-wise-frontend")
        print("3. npm install (if not done already)")
        print("4. npm run dev")
        print("5. Open http://localhost:5173 (or whatever port Vite shows)")
    else:
        print("❌ Frontend not found at ../study-wise-frontend")
        print("💡 Make sure the frontend directory is in the right location")
    
    print("\n🧪 TESTING THE PLATFORM:")
    print("1. Register a new user or login")
    print("2. Upload a PDF document")
    print("3. Generate flashcards")
    print("4. Try the chat functionality")
    
    print("\n🛠️ USEFUL ENDPOINTS:")
    print("- API Health: http://localhost:8000/health")
    print("- List Documents: http://localhost:8000/api/v1/documents/")
    print("- Admin Stats: http://localhost:8000/api/v1/admin/stats")
    print("- System Info: http://localhost:8000/api/v1/system/info")
    
    print("\n🧹 CLEANUP COMMANDS:")
    print("- Clean demo user: python scripts/cleanup_weaviate_user.py")
    print("- Clean all data: python scripts/cleanup_user_data.py --user-id USER_ID --confirm")
    
    print("\n📊 QUICK API TEST:")
    print("Try these curl commands:")
    print("curl http://localhost:8000/")
    print("curl http://localhost:8000/api/v1/system/info")

if __name__ == "__main__":
    main()