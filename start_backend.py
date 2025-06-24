#!/usr/bin/env python3
"""
StudyWise AI Backend Startup Script
Starts the FastAPI backend server with proper configuration.
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Start the StudyWise AI backend server."""
    
    print("🚀 Starting StudyWise AI Backend...")
    print("📋 Configuration:")
    print(f"   Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"   OpenAI API: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"   Supabase: {'✅ Set' if os.getenv('SUPABASE_URL') else '❌ Missing'}")
    print(f"   Weaviate: {'✅ Set' if os.getenv('WEAVIATE_URL') else '❌ Missing'}")
    print()
    
    # Check for required environment variables
    required_vars = ['OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please check your .env file and add the missing variables.")
        return
    
    print("🌐 Starting server at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔧 Admin Panel: http://localhost:8000/api/v1/admin/stats")
    print()
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 StudyWise AI Backend stopped.")

if __name__ == "__main__":
    main()