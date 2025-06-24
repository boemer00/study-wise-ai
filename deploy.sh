#!/bin/bash

# StudyWise AI - Google Cloud Run Deployment Script

set -e

# Configuration
PROJECT_ID="your-project-id"
SERVICE_NAME="studywise-api"
REGION="us-central1"

echo "🚀 Deploying StudyWise AI to Google Cloud Run..."

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

# Build and deploy
echo "🏗️  Building and deploying..."
gcloud builds submit --config cloudbuild.yaml

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo "✅ Deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📝 Next steps:"
echo "1. Update your frontend API URL to: $SERVICE_URL"
echo "2. Set environment variables in Cloud Run console"
echo "3. Configure custom domain (optional)"