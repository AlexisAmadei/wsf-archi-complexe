#!/bin/bash
# Deploy MCP Server to Cloud Run
# Usage: ./scripts/deploy_mcp.sh <PROJECT_ID>

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check project ID
PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Please provide a GCP Project ID${NC}"
    echo "Usage: $0 <PROJECT_ID>"
    exit 1
fi

REGION="europe-west1"
REGISTRY="europe-west1-docker.pkg.dev/${PROJECT_ID}/llm-task-manager"
IMAGE_TAG="${REGISTRY}/mcp:$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')"

echo -e "${GREEN}=== Deploying LLM Task Manager MCP Server ===${NC}"
echo -e "  Project:  ${PROJECT_ID}"
echo -e "  Region:   ${REGION}"
echo -e "  Image:    ${IMAGE_TAG}"
echo ""

# Step 1: Build the MCP image
echo -e "${YELLOW}[1/3] Building MCP Docker image...${NC}"
docker build \
    --target mcp \
    -t "${IMAGE_TAG}" \
    -t "${REGISTRY}/mcp:latest" \
    .

# Step 2: Push to Artifact Registry
echo -e "\n${YELLOW}[2/3] Pushing to Artifact Registry...${NC}"
docker push "${IMAGE_TAG}"
docker push "${REGISTRY}/mcp:latest"

# Step 3: Deploy to Cloud Run
echo -e "\n${YELLOW}[3/3] Deploying to Cloud Run...${NC}"
gcloud run deploy llm-task-manager-mcp \
    --image="${IMAGE_TAG}" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --port=8001 \
    --set-env-vars="ENVIRONMENT=production" \
    --set-secrets="DATABASE_URL=llm-task-manager-db-url:latest,JWT_SECRET_KEY=jwt-secret:latest" \
    --add-cloudsql-instances="${PROJECT_ID}:${REGION}:llm-task-manager-db" \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --session-affinity \
    --project="${PROJECT_ID}"

# Get service URL
MCP_URL=$(gcloud run services describe llm-task-manager-mcp \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format='value(status.url)')

echo ""
echo -e "${GREEN}=== MCP Server Deployed Successfully! ===${NC}"
echo ""
echo -e "  MCP URL: ${GREEN}${MCP_URL}${NC}"
echo -e "  SSE Endpoint: ${GREEN}${MCP_URL}/sse${NC}"
echo ""
echo -e "${YELLOW}Configuration Claude Desktop / Cursor :${NC}"
echo '  {'
echo '    "mcpServers": {'
echo '      "llm-task-manager": {'
echo "        \"url\": \"${MCP_URL}/sse\""
echo '      }'
echo '    }'
echo '  }'
echo ""
echo -e "${YELLOW}Test the connection:${NC}"
echo -e "  curl ${MCP_URL}/sse"
