# 🚀 StudyWise AI - MVP Deployment Guide

## 📋 Overview

This guide explains how to deploy and manage the **Minimum Viable Product (MVP)** version of StudyWise AI, which includes only stable, fully-functional features while keeping development features separate.

## 🎯 MVP Features (Enabled)

### ✅ Core Functionality
- **Flashcard System**: Complete FSRS spaced repetition algorithm
- **Dashboard**: User interface and navigation
- **API Documentation**: Interactive Swagger docs

### 🚧 Development Features (Hidden in MVP)
- **Study Methods**: FeynmanMode (in development)
- **Chat Interface**: AI chat system (API endpoints incomplete)
- **Document Manager**: PDF/DOCX processing (external dependencies required)
- **Advanced Analytics**: User statistics (API endpoints incomplete)

## 🔧 Deployment Configurations

### Frontend Configuration

#### 1. MVP Mode (Production-Ready)
```bash
# Build MVP version
cd /Users/renatoboemer/code/developer/study-wise-frontend
npm run build:mvp

# Preview MVP build
npm run preview:mvp

# Development with MVP features only
npm run dev:mvp
```

#### 2. Development Mode (All Features)
```bash
# Full development mode with all features
npm run dev

# Build with development features
npm run build:dev
```

### Backend Configuration

#### 1. MVP Mode
```bash
# Start backend in MVP mode (hides incomplete features)
cd /Users/renatoboemer/code/developer/study-wise-ai
MVP_MODE=true python start_local_demo.py
```

#### 2. Development Mode
```bash
# Start backend with all features (including incomplete ones)
python start_local_demo.py
```

## 🌐 Deployment Strategies

### Option 1: Separate Deployments
```
🏗️ Production MVP:
- Domain: studywise.ai
- Features: Flashcards + Dashboard only
- Stable and user-ready

🛠️ Development/Staging:
- Domain: dev.studywise.ai
- Features: All features enabled
- For testing and development
```

### Option 2: Environment Variables
```
🔧 Single Deployment with Feature Flags:
- Use environment variables to control features
- Easy to toggle features on/off
- Gradual feature rollout capability
```

## 📦 Build Commands Summary

| Command | Environment | Features | Use Case |
|---------|-------------|----------|----------|
| `npm run build:mvp` | MVP | Flashcards only | Production deployment |
| `npm run build:dev` | Development | All features | Testing/staging |
| `npm run build:production` | Production | Stable features | Full production |

## 🚀 Quick MVP Deployment

### Step 1: Build MVP Frontend
```bash
cd /Users/renatoboemer/code/developer/study-wise-frontend
npm run build:mvp
```

### Step 2: Start MVP Backend
```bash
cd /Users/renatoboemer/code/developer/study-wise-ai
MVP_MODE=true python start_local_demo.py
```

### Step 3: Test MVP Features
- ✅ Dashboard: http://localhost:8081/dashboard
- ✅ Flashcards: http://localhost:8081/flashcards
- ✅ API Docs: http://localhost:8000/docs
- ❌ Study Methods: Hidden/disabled
- ❌ Chat: Hidden/disabled
- ❌ Documents: Hidden/disabled

## 🔄 Feature Development Workflow

### 1. Development Phase
```bash
# Work on new features in development mode
npm run dev              # Frontend with all features
python start_local_demo.py    # Backend with all features
```

### 2. Feature Completion
```bash
# Update MVP configuration to enable new feature
# Edit src/config/mvp.ts:
studyMethods: true,  // Enable when FeynmanMode is complete
```

### 3. MVP Update
```bash
# Deploy updated MVP with new stable feature
npm run build:mvp
MVP_MODE=false python start_local_demo.py  # Include new features
```

## 🔐 Environment Security

### MVP Environment Variables
```bash
# Backend MVP mode
export MVP_MODE=true
export DEBUG=false
export LOG_LEVEL=info

# Frontend build mode
export VITE_MODE=mvp
export VITE_API_BASE_URL=https://api.studywise.ai
```

### Development Environment Variables
```bash
# Backend development mode
export MVP_MODE=false
export DEBUG=true
export LOG_LEVEL=debug

# Frontend development mode
export VITE_MODE=development
export VITE_API_BASE_URL=http://localhost:8000
```

## 📊 Feature Status Dashboard

| Feature | MVP Status | Development Status | API Ready | Notes |
|---------|------------|--------------------|-----------|-------|
| Flashcards | ✅ Enabled | ✅ Complete | ✅ Yes | FSRS algorithm working |
| Dashboard | ✅ Enabled | ✅ Complete | ✅ Yes | Basic navigation and stats |
| Study Methods | ❌ Hidden | 🔄 In Progress | 🔄 Partial | FeynmanMode 70% complete |
| Chat Interface | ❌ Hidden | 🔄 In Progress | ❌ No | API endpoints needed |
| Documents | ❌ Hidden | 🔄 In Progress | ❌ No | External services required |
| Analytics | ❌ Hidden | 🔄 In Progress | ❌ No | API endpoints needed |

## 🎯 Next Steps

1. **Deploy MVP**: Use the commands above to deploy a clean, stable version
2. **Complete Features**: Finish development of FeynmanMode and other features
3. **Gradual Rollout**: Enable features one by one as they become stable
4. **User Feedback**: Collect feedback on MVP to guide development priorities

## 🔍 Monitoring & Debugging

### Check Current Configuration
```bash
# Frontend: Check what features are enabled
# Look for logs in browser console showing feature flags

# Backend: Check MVP mode
curl http://localhost:8000/demo | grep -i "status"
```

### Troubleshooting
- **404 Errors**: Expected for disabled features in MVP mode
- **Missing Navigation**: Check if features are enabled in MVP config
- **Build Issues**: Ensure correct mode is set (`mvp` vs `development`)

---

**🎉 You now have a clean separation between MVP (production-ready) and development versions!**

This approach allows you to:
- Deploy stable features immediately
- Continue development without affecting users
- Gradually roll out new features as they're completed
- Maintain clean, professional user experience
