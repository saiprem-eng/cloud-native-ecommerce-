#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# build-and-push.sh
# Builds all 3 Docker images, tags them, and pushes to AWS ECR
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:?❌ Set AWS_ACCOUNT_ID env var}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_TAG="${IMAGE_TAG:-latest}"

SERVICES=("user-service" "product-service" "order-service")

# ── Colors ────────────────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }

# ── Step 1: Authenticate with ECR ─────────────────────────────────
log_info "Authenticating with AWS ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | \
    docker login --username AWS --password-stdin "${ECR_REGISTRY}"
log_success "ECR authentication successful."

# ── Step 2: Create ECR repositories if they don't exist ───────────
for SERVICE in "${SERVICES[@]}"; do
    log_info "Ensuring ECR repository exists: ${SERVICE}"
    aws ecr describe-repositories --repository-names "${SERVICE}" \
        --region "${AWS_REGION}" > /dev/null 2>&1 || \
    aws ecr create-repository \
        --repository-name "${SERVICE}" \
        --region "${AWS_REGION}" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 > /dev/null
    log_success "Repository ready: ${SERVICE}"
done

# ── Step 3: Build, tag, and push each service ─────────────────────
for SERVICE in "${SERVICES[@]}"; do
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Processing: ${SERVICE}"

    # Build
    log_info "Building Docker image..."
    docker build \
        --platform linux/amd64 \
        -t "${SERVICE}:${IMAGE_TAG}" \
        "./${SERVICE}/"
    log_success "Build complete: ${SERVICE}:${IMAGE_TAG}"

    # Tag
    ECR_IMAGE="${ECR_REGISTRY}/${SERVICE}:${IMAGE_TAG}"
    docker tag "${SERVICE}:${IMAGE_TAG}" "${ECR_IMAGE}"
    log_success "Tagged: ${ECR_IMAGE}"

    # Push
    log_info "Pushing to ECR..."
    docker push "${ECR_IMAGE}"
    log_success "Pushed: ${ECR_IMAGE}"
done

# ── Step 4: Summary ───────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ All images pushed to ECR successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo "Images available:"
for SERVICE in "${SERVICES[@]}"; do
    echo "  📦 ${ECR_REGISTRY}/${SERVICE}:${IMAGE_TAG}"
done
echo ""
echo "Next step: Update k8s manifests with your account ID and deploy:"
echo "  sed -i 's/<AWS_ACCOUNT_ID>/${AWS_ACCOUNT_ID}/g' k8s/*.yaml"
echo "  sed -i 's/<AWS_REGION>/${AWS_REGION}/g' k8s/*.yaml"
echo "  kubectl apply -f k8s/shared.yaml"
echo "  kubectl apply -f k8s/"
