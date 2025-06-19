# StudyWise AI Admin Guide

## 🎛️ Admin CLI Tool

Since you don't need the frontend admin dashboard, I've created a simple command-line admin tool that provides all the essential admin functionality.

### 🚀 Quick Start

```bash
# Interactive mode (recommended)
python admin_cli.py

# Or specific commands
python admin_cli.py stats
python admin_cli.py users
python admin_cli.py health
```

### 📋 Available Commands

#### Platform Overview
```bash
python admin_cli.py stats
```
- Total users, documents, flashcards
- Daily active users
- Storage usage
- System activity metrics

#### User Management
```bash
# List recent users
python admin_cli.py users --limit 20

# Get detailed user stats
python admin_cli.py user <user-id>
```

#### System Health
```bash
python admin_cli.py health
```
- API status
- Database connectivity
- Vector database status
- AI service availability
- Response time metrics

#### Interactive Mode
```bash
python admin_cli.py interactive
```
Provides a command prompt where you can run multiple commands:
- `stats` - Platform statistics
- `users` - List users
- `user <id>` - User details
- `health` - System health
- `help` - Show commands
- `quit` - Exit

### 🔐 Authentication (Optional)

If you need admin authentication, you can provide a JWT token:

```bash
python admin_cli.py --token "your-admin-jwt-token" stats
```

### 🌐 Different Environments

```bash
# Local development (default)
python admin_cli.py stats

# Production server
python admin_cli.py --url "https://your-api.vercel.app" stats
```

### 📊 Example Output

```
📊 Platform Statistics
==================================================
👥 Total Users: 1,234
📄 Total Documents: 456
🃏 Total Flashcards: 7,890
💬 Total Conversations: 2,345
📈 Daily Active Users: 89
🔄 Reviews Today: 234

💾 Storage Usage:
   Documents: 245.6 MB
   Vector DB: 12,345 chunks
```

### 🛠️ Troubleshooting

**Connection Issues:**
```bash
# Check if API is running
python admin_cli.py health

# Try different URL
python admin_cli.py --url "http://localhost:8000" health
```

**Permission Issues:**
```bash
# If admin endpoints require authentication
python admin_cli.py --token "your-token" stats
```

### 🎯 Common Use Cases

**Daily Monitoring:**
```bash
python admin_cli.py health && python admin_cli.py stats
```

**User Investigation:**
```bash
python admin_cli.py users
python admin_cli.py user 12345678-1234-5678-9012-123456789012
```

**System Status Check:**
```bash
python admin_cli.py interactive
> health
> stats
> quit
```

## 🔄 Backend Admin Endpoints

The following admin endpoints are available in your backend:

### Platform Statistics
- `GET /api/v1/admin/stats/platform` - Platform overview
- `GET /api/v1/admin/health` - System health check

### User Management  
- `GET /api/v1/admin/users` - List users
- `GET /api/v1/admin/users/{user_id}/stats` - User details

### Authentication
- Admin endpoints may require authentication depending on your setup
- Use the `--token` flag if JWT authentication is enabled

## 🚀 Production Deployment

1. **Copy the CLI tool to your server:**
   ```bash
   scp admin_cli.py your-server:/path/to/studywise/
   ```

2. **Install dependencies:**
   ```bash
   pip install requests
   ```

3. **Create an alias for easy access:**
   ```bash
   echo "alias studywise-admin='python /path/to/studywise/admin_cli.py'" >> ~/.bashrc
   source ~/.bashrc
   ```

4. **Use the alias:**
   ```bash
   studywise-admin stats
   studywise-admin interactive
   ```

## 📈 Monitoring Scripts

You can also create monitoring scripts using the CLI:

```bash
#!/bin/bash
# daily_report.sh
echo "=== Daily StudyWise Report ===" 
python admin_cli.py health
python admin_cli.py stats
echo "Report generated: $(date)"
```

This gives you full admin access without needing the frontend dashboard!