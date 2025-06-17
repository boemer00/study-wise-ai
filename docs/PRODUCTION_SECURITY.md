# 🔐 StudyWise AI - Production Security Guide

## Secret Key Management

### Overview

StudyWise AI uses environment-based secret management with automatic validation to ensure production security.

### Configuration Behavior

| Environment | Secret Key Source | Validation |
|-------------|------------------|------------|
| `development` | Auto-generated secure key | ✅ Always valid |
| `staging` | Auto-generated secure key | ✅ Always valid |
| `production` | **REQUIRED** environment variable | ❌ Fails if not provided |

### Setting Up Production Secrets

#### 1. Generate a Secure Secret Key

```bash
# Using the provided script
python scripts/generate_secret_key.py

# Or manually
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 2. Configure Production Environment

```bash
# In your production .env file or environment variables
ENVIRONMENT=production
SECRET_KEY=your_generated_secret_key_here
```

#### 3. Verify Configuration

```bash
# Test that production validation works
python -c "
import os
os.environ['ENVIRONMENT'] = 'production'
os.environ['SECRET_KEY'] = 'your_secret_key'
from api.core.config import get_settings
settings = get_settings()
print('✅ Production configuration valid')
"
```

### Security Best Practices

#### ✅ Do's
- **Generate unique keys** for each environment (dev, staging, prod)
- **Use the provided script** for cryptographically secure key generation
- **Store keys in secure environment variable management** (AWS Secrets Manager, Azure Key Vault, etc.)
- **Rotate keys periodically** (quarterly recommended)
- **Use different keys** for different services/deployments

#### ❌ Don'ts
- **Never commit secret keys** to version control
- **Don't reuse keys** across environments
- **Don't use simple/predictable keys** 
- **Don't store keys in plain text files** on production servers
- **Don't share keys** via email/chat/documentation

### Environment Variables Required for Production

```bash
# Required
ENVIRONMENT=production
SECRET_KEY=your_secure_secret_key

# Database (Required)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# AI Services (Required)
OPENAI_API_KEY=your_openai_key

# Vector Database (Required)
WEAVIATE_URL=your_weaviate_url
WEAVIATE_API_KEY=your_weaviate_key
```

### Production Deployment Checklist

- [ ] Generate unique secret key using `scripts/generate_secret_key.py`
- [ ] Set `ENVIRONMENT=production` in environment variables
- [ ] Set `SECRET_KEY` in secure environment variable storage
- [ ] Verify all required environment variables are set
- [ ] Test configuration validation before deployment
- [ ] Document key rotation procedures
- [ ] Set up monitoring for configuration errors

### Key Rotation Procedure

1. **Generate new secret key**:
   ```bash
   python scripts/generate_secret_key.py
   ```

2. **Update environment variables** in your deployment system

3. **Deploy with zero downtime** (rolling update recommended)

4. **Verify all services** are using the new key

5. **Invalidate old sessions** (users will need to re-authenticate)

### Troubleshooting

#### Error: "SECRET_KEY environment variable is required in production"

**Cause**: Production environment detected but no SECRET_KEY provided.

**Solution**:
1. Generate a secret key: `python scripts/generate_secret_key.py`
2. Set the environment variable: `export SECRET_KEY=your_key`
3. Restart the application

#### Error: Configuration validation failed

**Cause**: Invalid environment configuration.

**Solution**:
1. Check all required environment variables are set
2. Verify `ENVIRONMENT` is set to correct value
3. Test configuration locally before deploying

---

**🔒 Security Note**: This configuration ensures that production deployments cannot start without proper secret management, preventing accidental deployment with default/insecure keys.