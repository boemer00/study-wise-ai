#!/usr/bin/env python3
"""
Create auth_users table in Supabase for persistent user storage
"""

import sys
sys.path.append('.')

from src.supabase_client import get_supabase_client

def create_auth_table():
    """Create auth_users table in Supabase."""
    try:
        supabase = get_supabase_client()
        
        # Try to create the table using SQL
        sql = """
        CREATE TABLE IF NOT EXISTS auth_users (
            id UUID PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create index on email for faster lookups
        CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth_users(email);
        """
        
        result = supabase.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ auth_users table created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create table: {e}")
        print("💡 You may need to create this table manually in Supabase dashboard:")
        print("""
CREATE TABLE auth_users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_auth_users_email ON auth_users(email);
        """)
        return False

if __name__ == "__main__":
    create_auth_table()