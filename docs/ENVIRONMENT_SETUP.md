# Environment Configuration Guide

## Overview
This guide explains how to properly manage environment variables and credentials for StudyWise AI.

## Environment Files Structure

### Single `.env` File Approach (Recommended for MVP)
For your current MVP setup, use **one `.env` file** with an `ENVIRONMENT` variable to control behavior:

```bash
# Your .env file
ENVIRONMENT=development  # or staging, production
# ... rest of your variables
```

### Multiple Environment Files (Advanced)
For larger teams or complex deployments, you can use:
- `.env` - Default/shared variables
- `.env.development` - Development overrides
- `.env.staging` - Staging environment
- `.env.production` - Production secrets (managed by deployment platform)

## Security Best Practices

### ✅ DO:
1. **Use environment-specific API keys** when possible
2. **Rotate exposed credentials immediately**
3. **Use least-privilege keys** (anon vs service role)
4. **Store production secrets in deployment platform** (Vercel, Railway, etc.)
5. **Keep `.env.example` updated** but without real values

### ❌ DON'T:
1. **Never commit `.env` files** to git
2. **Don't share production keys** in development
3. **Don't hardcode credentials** in source code
4. **Don't use production databases** for testing

## Environment Variables by Context

### Development Environment
```bash
ENVIRONMENT=development
OPENAI_API_KEY=sk-proj-your-dev-key...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key...  # Use anon key for frontend
WEAVIATE_URL=http://localhost:8080  # Local instance
```

### Production Environment
```bash
ENVIRONMENT=production
OPENAI_API_KEY=sk-proj-your-prod-key...
SUPABASE_SERVICE_ROLE_KEY=your-service-key...  # Service role for backend
SECRET_KEY=your-generated-secret...  # Required for JWT
```

## Immediate Action Required

### 🚨 Rotate These Keys Now:
1. **OpenAI API Keys** - Generate new keys in OpenAI dashboard
2. **Supabase Keys** - Regenerate in Supabase dashboard
3. **Weaviate API Key** - Create new key in Weaviate console
4. **Pinecone Key** - Generate new key if still using

### Steps to Secure:
1. Log into each service (OpenAI, Supabase, Weaviate)
2. Generate new API keys
3. Update your local `.env` file
4. Delete/revoke the old exposed keys
5. Update any deployed applications with new keys

## Frontend Environment Variables

Create `/Users/renatoboemer/code/developer/study-wise-frontend/.env`:
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

## Deployment Considerations

### Local Development
- Use `.env` file with development keys
- Can use demo/test mode fallbacks

### Production Deployment
- Set environment variables in deployment platform
- Use service role keys for backend operations
- Use anon keys for frontend (less privileged)
- Enable strict authentication (no demo fallbacks)

## Key Management by Service

| Service | Development | Production | Notes |
|---------|-------------|------------|--------|
| OpenAI | Personal key | Separate prod key | Consider usage limits |
| Supabase | Anon key usually sufficient | Service role for backend | Different privilege levels |
| Weaviate | Local instance or shared | Dedicated cluster | Performance implications |
| Secret Key | Any secure string | Cryptographically secure | For JWT signing |

This approach keeps your setup simple while maintaining security best practices.