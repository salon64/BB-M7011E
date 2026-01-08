#!/bin/bash
set -e

# Configuration - set environment
ENV="${ENV:-dev}"  # dev, staging, or prod

echo "🔧 BB-M7011E Cluster Setup"
echo "=========================="
echo "Environment: $ENV"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
  echo "❌ Error: .env file not found!"
  echo "   Please create a .env file with your secrets"
  exit 1
fi

# Load environment variables
source .env

# 1. Create namespaces (if they don't exist)
echo "📦 Step 1: Creating namespaces..."
kubectl create namespace user-service-${ENV} 2>/dev/null || echo "✓ user-service-${ENV} namespace exists"
kubectl create namespace payment-service-${ENV} 2>/dev/null || echo "✓ payment-service-${ENV} namespace exists"
kubectl create namespace item-service-${ENV} 2>/dev/null || echo "✓ item-service-${ENV} namespace exists"
kubectl create namespace monitoring 2>/dev/null || echo "✓ monitoring namespace exists"
kubectl create namespace keycloak 2>/dev/null || echo "✓ keycloak namespace exists"

echo "✓ Namespaces ready"
echo ""

# 2. Create secrets for each service
echo "🔐 Step 2: Creating secrets..."

# Supabase and Keycloak secrets for user-service
echo "  Creating user-service-${ENV} secrets..."
kubectl create secret generic supabase-secret \
  --namespace=user-service-${ENV} \
  --from-literal=SUPABASE_KEY="${SUPABASE_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic keycloak-secret \
  --namespace=user-service-${ENV} \
  --from-literal=KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER}" \
  --from-literal=KEYCLOAK_ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD}" \
  --from-literal=KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID:-user-service}" \
  --from-literal=KEYCLOAK_CLIENT_SECRET="${KEYCLOAK_CLIENT_SECRET}" \
  --dry-run=client -o yaml | kubectl apply -f -

# Supabase and Keycloak secrets for payment-service
echo "  Creating payment-service-${ENV} secrets..."
kubectl create secret generic supabase-secret \
  --namespace=payment-service-${ENV} \
  --from-literal=SUPABASE_KEY="${SUPABASE_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic keycloak-secret \
  --namespace=payment-service-${ENV} \
  --from-literal=KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER}" \
  --from-literal=KEYCLOAK_ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD}" \
  --from-literal=KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID:-payment-service}" \
  --from-literal=KEYCLOAK_CLIENT_SECRET="${KEYCLOAK_CLIENT_SECRET}" \
  --dry-run=client -o yaml | kubectl apply -f -

# Supabase and Keycloak secrets for item-service
echo "  Creating item-service-${ENV} secrets..."
kubectl create secret generic supabase-secret \
  --namespace=item-service-${ENV} \
  --from-literal=SUPABASE_KEY="${SUPABASE_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic keycloak-secret \
  --namespace=item-service-${ENV} \
  --from-literal=KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER}" \
  --from-literal=KEYCLOAK_ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD}" \
  --from-literal=KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID:-item-service}" \
  --from-literal=KEYCLOAK_CLIENT_SECRET="${KEYCLOAK_CLIENT_SECRET}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✓ Secrets created"
echo ""

# 3. Deploy infrastructure
echo "🏗️  Step 3: Deploying infrastructure..."
if [ -f keycloak/install.sh ]; then
  echo "  Deploying Keycloak..."
  bash keycloak/install.sh
else
  echo "  ⚠️  Keycloak install script not found, skipping..."
fi

if [ -d monitoring ]; then
  echo "  Deploying monitoring..."
  kubectl apply -f monitoring/ 2>/dev/null || echo "  ⚠️  Monitoring deployment failed or already exists"
fi

echo ""
echo "✅ Cluster setup complete!"
echo ""
echo "Next steps:"
echo "  1. Build and push Docker images: ./scripts/build-and-push.sh"
echo "  2. Deploy services: ./scripts/deploy-services.sh"
echo ""
