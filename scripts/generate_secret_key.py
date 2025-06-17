#!/usr/bin/env python3
"""
Secure secret key generator for StudyWise AI production deployment.

Usage:
    python scripts/generate_secret_key.py
    
This script generates a cryptographically secure secret key suitable for production use.
"""

import secrets
import sys

def generate_secret_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure secret key.
    
    Args:
        length: Length of the secret key in bytes
        
    Returns:
        URL-safe base64 encoded secret key
    """
    return secrets.token_urlsafe(length)

def main():
    """Generate and print a secure secret key."""
    secret_key = generate_secret_key()
    
    print("=" * 60)
    print("🔐 StudyWise AI - Production Secret Key Generator")
    print("=" * 60)
    print()
    print("Generated secure secret key:")
    print(f"SECRET_KEY={secret_key}")
    print()
    print("📝 Add this to your production environment:")
    print("  1. Copy the SECRET_KEY line above")
    print("  2. Add it to your production .env file")
    print("  3. Set ENVIRONMENT=production")
    print()
    print("⚠️  Security Notes:")
    print("  - Keep this key secret and secure")
    print("  - Never commit this key to version control")
    print("  - Use different keys for different environments")
    print("  - Store in secure environment variable management")
    print("=" * 60)

if __name__ == "__main__":
    main()