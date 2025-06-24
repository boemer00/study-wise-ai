#!/bin/bash

# StudyWise AI - Dual Cloud Run Deployment Script
# Deploys both frontend and backend to Google Cloud Run

set -e

# Configuration
PROJECT_ID="study-wise-id"
REGION="us-central1"
BACKEND_SERVICE="studywise-api"
FRONTEND_SERVICE="studywise-frontend"

# Paths
BACKEND_PATH="/Users/renatoboemer/code/developer/study-wise-ai"
FRONTEND_PATH="/Users/renatoboemer/code/developer/study-wise-frontend"

echo "🚀 Deploying StudyWise AI (Frontend + Backend) to Google Cloud Run..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud SDK not found. Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo "📋 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Deploy Backend
echo "🔧 Deploying Backend API..."
cd $BACKEND_PATH
gcloud builds submit --tag gcr.io/$PROJECT_ID/$BACKEND_SERVICE .
gcloud run deploy $BACKEND_SERVICE \
    --image gcr.io/$PROJECT_ID/$BACKEND_SERVICE \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --port 8080

# Get backend URL
BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region=$REGION --format="value(status.url)")
echo "✅ Backend deployed: $BACKEND_URL"

# Deploy Frontend
echo "🎨 Deploying Frontend..."
cd $FRONTEND_PATH

# Update API URL in frontend (you might want to use environment variables instead)
echo "VITE_API_URL=$BACKEND_URL" > .env.production

gcloud builds submit --tag gcr.io/$PROJECT_ID/$FRONTEND_SERVICE .
gcloud run deploy $FRONTEND_SERVICE \
    --image gcr.io/$PROJECT_ID/$FRONTEND_SERVICE \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --timeout 60 \
    --max-instances 5 \
    --port 8080

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --region=$REGION --format="value(status.url)")

echo ""
echo "✅ Deployment complete!"
echo "🎨 Frontend: $FRONTEND_URL"
echo "🔧 Backend:  $BACKEND_URL"
echo ""
echo "📝 Next steps:"
echo "1. Set backend environment variables in Cloud Run console"
echo "2. Update CORS origins in backend to include: $FRONTEND_URL"
echo "3. Configure custom domains (optional)"
