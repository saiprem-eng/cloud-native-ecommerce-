# ═══════════════════════════════════════════════════════════════════
# E-Commerce Microservices Platform
# User Service | Product Service | Order Service
# Stack: FastAPI + AWS Cognito + DynamoDB + S3 + ECR + EKS
# ═══════════════════════════════════════════════════════════════════

## 🏗️ Architecture Overview

```
                        ┌─────────────────────────────┐
                        │      AWS ALB (Ingress)        │
                        │   (EKS Load Balancer Ctrl)   │
                        └──────────────┬──────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
   │   User Service   │   │ Product Service  │   │  Order Service   │
   │   Port: 8001     │   │   Port: 8002     │   │   Port: 8003     │
   │   FastAPI        │   │   FastAPI        │◄──│   FastAPI        │
   └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
            │                      │                       │
            ▼                      ├──────▶ DynamoDB        ▼
     AWS Cognito              S3 (images)      products   DynamoDB
    (User Pool)                                           orders
```

### Microservices

| Service | Port | Storage | Responsibility |
|---|---|---|---|
| **User Service** | 8001 | AWS Cognito | Registration, login, JWT auth, profile |
| **Product Service** | 8002 | DynamoDB + S3 | Product CRUD, image upload, search |
| **Order Service** | 8003 | DynamoDB | Order lifecycle, stock validation |

### Inter-Service Communication
- Order Service calls **Product Service** via REST to validate products and check stock
- All services expose `/health` and `/ready` endpoints for K8s probes
- Services discover each other using **Kubernetes internal DNS** (`http://service-name:port`)

---

## 📁 Project Structure

```
hersheys/
├── user-service/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── schemas.py           # Request/Response models
│   │   ├── routers/
│   │   │   ├── auth.py          # Register, login, logout, password reset
│   │   │   └── users.py         # Profile CRUD
│   │   └── services/
│   │       └── cognito_service.py  # AWS Cognito SDK wrapper
│   ├── Dockerfile               # Multi-stage, non-root
│   ├── requirements.txt
│   └── .env.example
│
├── product-service/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── schemas.py
│   │   ├── routers/
│   │   │   └── products.py      # CRUD + search + S3 upload URL
│   │   └── services/
│   │       └── product_service.py  # DynamoDB + S3 service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── order-service/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── schemas.py
│   │   ├── routers/
│   │   │   └── orders.py        # Order lifecycle
│   │   └── services/
│   │       └── order_service.py # DynamoDB + HTTP to Product Service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── k8s/
│   ├── shared.yaml              # Namespace, ConfigMap, Secrets, ServiceAccounts
│   ├── user-service.yaml        # Deployment + Service + HPA
│   ├── product-service.yaml     # Deployment + Service + HPA
│   ├── order-service.yaml       # Deployment + Service + HPA
│   └── ingress.yaml             # AWS ALB Ingress
│
├── scripts/
│   ├── build-and-push.sh        # Build images & push to ECR
│   └── deploy-eks.sh            # Deploy to EKS
│
└── docker-compose.yml           # Local development
```

---

## 🚀 Quick Start

### Option 1: Local Development (Docker Compose)

```bash
# 1. Copy and fill env files for each service
cp user-service/.env.example user-service/.env
cp product-service/.env.example product-service/.env
cp order-service/.env.example order-service/.env

# 2. Fill in your AWS credentials and Cognito/DynamoDB/S3 settings in each .env

# 3. Start all services
docker-compose up --build

# Services available at:
# User Service:    http://localhost:8001/docs
# Product Service: http://localhost:8002/docs
# Order Service:   http://localhost:8003/docs
```

---

## 🐳 ECR: Build & Push

```bash
# Prerequisites: AWS CLI configured, Docker running
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="us-east-1"
export IMAGE_TAG="v1.0.0"

chmod +x scripts/build-and-push.sh
./scripts/build-and-push.sh
```

This script will:
1. Authenticate Docker with ECR
2. Create ECR repositories (if not exist) with image scanning enabled
3. Build each service for `linux/amd64` (EKS-compatible)
4. Tag and push to ECR

---

## ☸️ EKS: Deploy

### Prerequisites

1. EKS cluster running (with AWS Load Balancer Controller installed)
2. IRSA configured (see IAM section below)
3. Images pushed to ECR

```bash
# 1. Fill in Kubernetes secrets
# Edit k8s/shared.yaml and replace <BASE64_ENCODED_VALUE> placeholders:
echo -n "us-east-1_XXXXXXXX" | base64   # COGNITO_USER_POOL_ID
echo -n "your-client-id" | base64        # COGNITO_CLIENT_ID
echo -n "your-client-secret" | base64    # COGNITO_CLIENT_SECRET

# 2. Deploy
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="us-east-1"
export EKS_CLUSTER_NAME="my-ecommerce-cluster"
export IMAGE_TAG="v1.0.0"

chmod +x scripts/deploy-eks.sh
./scripts/deploy-eks.sh
```

---

## 🔐 AWS IAM Roles (IRSA)

Each service uses **IAM Roles for Service Accounts (IRSA)** — no access keys needed in pods.

### User Service IAM Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:AdminCreateUser",
        "cognito-idp:AdminDeleteUser",
        "cognito-idp:AdminGetUser",
        "cognito-idp:AdminListGroupsForUser",
        "cognito-idp:DescribeUserPool",
        "cognito-idp:ListUsers"
      ],
      "Resource": "arn:aws:cognito-idp:REGION:ACCOUNT:userpool/POOL_ID"
    }
  ]
}
```

### Product Service IAM Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:*"],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/products"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::ecommerce-product-images/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::ecommerce-product-images"
    }
  ]
}
```

### Order Service IAM Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:*"],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/orders"
    }
  ]
}
```

---

## 🗄️ AWS DynamoDB Tables

### Products Table
```
Table Name: products
Partition Key: product_id (String)
Billing: PAY_PER_REQUEST (on-demand)
```

### Orders Table
```
Table Name: orders
Partition Key: order_id (String)
Billing: PAY_PER_REQUEST (on-demand)
```

**Create with AWS CLI:**
```bash
# Products table
aws dynamodb create-table \
    --table-name products \
    --attribute-definitions AttributeName=product_id,AttributeType=S \
    --key-schema AttributeName=product_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

# Orders table
aws dynamodb create-table \
    --table-name orders \
    --attribute-definitions AttributeName=order_id,AttributeType=S \
    --key-schema AttributeName=order_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

---

## 📡 API Reference

### User Service (port 8001)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/confirm` | Verify email with OTP |
| POST | `/api/v1/auth/login` | Login → get JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Global sign out |
| POST | `/api/v1/auth/forgot-password` | Request password reset |
| POST | `/api/v1/auth/reset-password` | Reset with OTP |
| GET | `/api/v1/users/me` | Get my profile |
| PUT | `/api/v1/users/me` | Update my profile |
| DELETE | `/api/v1/users/me` | Delete my account |
| GET | `/api/v1/users/` | List all users (admin) |

### Product Service (port 8002)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/products/` | Create product |
| GET | `/api/v1/products/` | List products (filter/paginate) |
| GET | `/api/v1/products/search?q=` | Search by keyword |
| GET | `/api/v1/products/{id}` | Get product |
| PUT | `/api/v1/products/{id}` | Update product |
| DELETE | `/api/v1/products/{id}` | Soft delete product |
| POST | `/api/v1/products/{id}/images/upload-url` | Get S3 presigned URL |

### Order Service (port 8003)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/orders/` | Place new order |
| GET | `/api/v1/orders/` | List all orders (admin) |
| GET | `/api/v1/orders/{id}` | Get order |
| GET | `/api/v1/orders/user/{user_id}` | User's orders |
| GET | `/api/v1/orders/user/{user_id}/summary` | Order stats |
| PATCH | `/api/v1/orders/{id}/status` | Update order status |

---

## 📊 Order Status Transitions

```
pending ──► confirmed ──► processing ──► shipped ──► delivered
   │              │              │
   └──────────────┴──────────────┴──────────► cancelled
                                                    
delivered ──────────────────────────────────► refunded
```

---

## 🛡️ Security Features

- ✅ **Non-root containers** — all services run as UID 1001
- ✅ **Multi-stage builds** — minimal attack surface (slim runtime images)
- ✅ **IRSA** — no hardcoded AWS credentials in pods
- ✅ **Secrets via K8s Secrets** — Cognito credentials not in ConfigMaps
- ✅ **ReadOnlyRootFilesystem** — container filesystem is read-only
- ✅ **Resource limits** — CPU and memory bounds prevent noisy neighbor issues
- ✅ **HPA** — auto-scales under load
- ✅ **HTTPS** — ALB terminates TLS with ACM certificate

---

## 🔭 Roadmap (Phase 2)

- [ ] API Gateway (AWS API GW or Kong)
- [ ] Monitoring — Prometheus + Grafana
- [ ] CI/CD — GitHub Actions pipeline
- [ ] AWS SQS/SNS for async order events
- [ ] Redis cache for product catalog
- [ ] Payment service integration
