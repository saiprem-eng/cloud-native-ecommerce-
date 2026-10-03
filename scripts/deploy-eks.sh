#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# deploy-eks.sh
# Deploys all services to an existing EKS cluster
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:?❌ Set AWS_ACCOUNT_ID env var}"
AWS_REGION="${AWS_REGION:-us-east-1}"
EKS_CLUSTER_NAME="${EKS_CLUSTER_NAME:?❌ Set EKS_CLUSTER_NAME env var}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }

# Update kubeconfig for EKS cluster
log_info "Configuring kubectl for EKS cluster: ${EKS_CLUSTER_NAME}"
aws eks update-kubeconfig \
    --region "${AWS_REGION}" \
    --name "${EKS_CLUSTER_NAME}"
log_success "kubectl configured."

# Substitute placeholders in manifests
log_info "Substituting placeholders in K8s manifests..."
K8S_DIR="./k8s"
TMP_DIR="/tmp/ecommerce-k8s-$$"
mkdir -p "${TMP_DIR}"

for FILE in "${K8S_DIR}"/*.yaml; do
    BASENAME=$(basename "${FILE}")
    sed \
        -e "s/<AWS_ACCOUNT_ID>/${AWS_ACCOUNT_ID}/g" \
        -e "s/<AWS_REGION>/${AWS_REGION}/g" \
        -e "s|:latest|:${IMAGE_TAG}|g" \
        "${FILE}" > "${TMP_DIR}/${BASENAME}"
done
log_success "Manifests prepared in ${TMP_DIR}"

# Deploy shared resources first (namespace, configmap, etc.)
log_info "Deploying shared resources (namespace, configmap, secrets, service accounts)..."
kubectl apply -f "${TMP_DIR}/shared.yaml"
kubectl wait --for=condition=established --timeout=60s crd/horizontalpodautoscalers.autoscaling.k8s.io 2>/dev/null || true
log_success "Shared resources applied."

# Wait for namespace
kubectl wait --for=jsonpath='{.status.phase}'=Active \
    namespace/ecommerce --timeout=30s

# Deploy services
log_info "Deploying microservices..."
for SERVICE in user-service product-service order-service; do
    log_info "Deploying ${SERVICE}..."
    kubectl apply -f "${TMP_DIR}/${SERVICE}.yaml"
done
log_success "All deployments applied."

# Deploy ingress
log_info "Deploying ALB Ingress..."
kubectl apply -f "${TMP_DIR}/ingress.yaml"
log_success "Ingress applied."

# Wait for rollouts
log_info "Waiting for deployments to be ready..."
for SERVICE in user-service product-service order-service; do
    kubectl rollout status deployment/${SERVICE} -n ecommerce --timeout=300s
    log_success "${SERVICE} is ready."
done

# Get ALB endpoint
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo ""
log_info "Waiting for ALB to be provisioned (this may take 2-3 minutes)..."
sleep 30
ALB_URL=$(kubectl get ingress ecommerce-ingress -n ecommerce \
    -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "pending...")
echo ""
echo "🌐 ALB Endpoint: ${ALB_URL}"
echo ""
echo "📖 API Docs (once ALB is ready):"
echo "   User Service:    http://${ALB_URL}/api/v1/users/docs"
echo "   Product Service: http://${ALB_URL}/api/v1/products/docs"
echo "   Order Service:   http://${ALB_URL}/api/v1/orders/docs"

# Cleanup temp files
rm -rf "${TMP_DIR}"
