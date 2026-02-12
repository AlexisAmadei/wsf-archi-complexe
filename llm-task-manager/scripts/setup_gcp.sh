#!/bin/bash
# GCP Setup Script - Phase 1
# This script provisions the Cloud SQL instance and configures Secret Manager

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== LLM Task Manager - GCP Setup (Phase 1) ===${NC}\n"

# Prompt for GCP Project ID
read -p "Enter your GCP Project ID: " PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID is required${NC}"
    exit 1
fi

# Set the project
echo -e "\n${YELLOW}Setting GCP project to: $PROJECT_ID${NC}"
gcloud config set project "$PROJECT_ID"

# Variables
REGION="europe-west1"
DB_INSTANCE="llm-task-manager-db"
DB_NAME="llm_task_manager"
DB_USER="app_user"

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  DB Instance: $DB_INSTANCE"
echo "  DB Name: $DB_NAME"
echo "  DB User: $DB_USER"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Enable required APIs
echo -e "\n${YELLOW}Enabling required GCP APIs...${NC}"
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Check if Cloud SQL instance exists
echo -e "\n${YELLOW}Checking if Cloud SQL instance exists...${NC}"
if gcloud sql instances describe "$DB_INSTANCE" --project="$PROJECT_ID" 2>/dev/null; then
    echo -e "${GREEN}Cloud SQL instance already exists!${NC}"
else
    echo -e "\n${YELLOW}Creating Cloud SQL instance (this takes ~5-10 minutes)...${NC}"
    gcloud sql instances create "$DB_INSTANCE" \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region="$REGION" \
        --storage-auto-increase \
        --backup-start-time=03:00 \
        --project="$PROJECT_ID"
    
    echo -e "${GREEN}Cloud SQL instance created!${NC}"
fi

# Create database
echo -e "\n${YELLOW}Creating database...${NC}"
if gcloud sql databases describe "$DB_NAME" --instance="$DB_INSTANCE" --project="$PROJECT_ID" 2>/dev/null; then
    echo -e "${GREEN}Database already exists!${NC}"
else
    gcloud sql databases create "$DB_NAME" \
        --instance="$DB_INSTANCE" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}Database created!${NC}"
fi

# Generate strong password
echo -e "\n${YELLOW}Generating database password...${NC}"
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Create database user
echo -e "\n${YELLOW}Creating database user...${NC}"
gcloud sql users create "$DB_USER" \
    --instance="$DB_INSTANCE" \
    --password="$DB_PASSWORD" \
    --project="$PROJECT_ID" 2>/dev/null || echo "User might already exist"

# Create Secret Manager secrets
echo -e "\n${YELLOW}Creating Secret Manager secrets...${NC}"

# JWT Secret
JWT_SECRET=$(openssl rand -base64 32)
echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret \
    --data-file=- \
    --replication-policy="automatic" \
    --project="$PROJECT_ID" 2>/dev/null || echo "jwt-secret already exists"

# Database URL for production (Unix socket)
DB_URL_PROD="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${PROJECT_ID}:${REGION}:${DB_INSTANCE}"
echo -n "$DB_URL_PROD" | gcloud secrets create llm-task-manager-db-url \
    --data-file=- \
    --replication-policy="automatic" \
    --project="$PROJECT_ID" 2>/dev/null || echo "llm-task-manager-db-url already exists"

# Get project number for service account
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

# Grant Secret Manager access to Cloud Run and Cloud Build service accounts
echo -e "\n${YELLOW}Granting Secret Manager access to service accounts...${NC}"

# Cloud Run service agent
gcloud secrets add-iam-policy-binding llm-task-manager-db-url \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID" 2>/dev/null || true

gcloud secrets add-iam-policy-binding jwt-secret \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID" 2>/dev/null || true

# Cloud Build service account
gcloud secrets add-iam-policy-binding llm-task-manager-db-url \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID" 2>/dev/null || true

gcloud secrets add-iam-policy-binding jwt-secret \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID" 2>/dev/null || true

# Create .env file for local development via Cloud SQL Proxy
echo -e "\n${YELLOW}Creating .env file for local development...${NC}"
cat > .env << EOF
# Environment
ENVIRONMENT=dev
DEBUG=true

# Database - via Cloud SQL Proxy (local development)
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}

# JWT Authentication
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# GCP Configuration
GCP_PROJECT_ID=${PROJECT_ID}
GCP_REGION=${REGION}
CLOUD_SQL_INSTANCE=${PROJECT_ID}:${REGION}:${DB_INSTANCE}

# Logging
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=*
EOF

echo -e "${GREEN}.env file created!${NC}"

# Create Artifact Registry repository
echo -e "\n${YELLOW}Creating Artifact Registry repository...${NC}"
gcloud artifacts repositories describe llm-task-manager \
    --location="$REGION" \
    --project="$PROJECT_ID" 2>/dev/null || \
gcloud artifacts repositories create llm-task-manager \
    --repository-format=docker \
    --location="$REGION" \
    --description="LLM Task Manager Docker images" \
    --project="$PROJECT_ID"

echo -e "\n${GREEN}=== Phase 1 Setup Complete! ===${NC}\n"

echo -e "${YELLOW}Next steps:${NC}"
echo "1. Start Cloud SQL Proxy for local development:"
echo -e "   ${GREEN}cloud-sql-proxy ${PROJECT_ID}:${REGION}:${DB_INSTANCE} --port 5432${NC}"
echo ""
echo "2. Run database migrations (after models are created in Phase 2):"
echo -e "   ${GREEN}alembic upgrade head${NC}"
echo ""
echo "3. Your secrets have been stored in Secret Manager:"
echo "   - llm-task-manager-db-url"
echo "   - jwt-secret"
echo ""
echo -e "${YELLOW}Connection details saved in .env file${NC}"
echo ""
echo -e "${YELLOW}Cloud SQL connection info:${NC}"
echo "  Instance: ${PROJECT_ID}:${REGION}:${DB_INSTANCE}"
echo "  Database: ${DB_NAME}"
echo "  User: ${DB_USER}"
