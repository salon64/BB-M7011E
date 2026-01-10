#!/bin/bash
set -e

# Configuration
ENV="${ENV:-dev}"  # dev, staging, prod, or "all"
TAG="${TAG:-latest}"
SKIP_BUILD="${SKIP_BUILD:-false}"

echo "🚀 BB-M7011E Full Deployment"
echo "============================"
echo "Environment: $ENV"
echo "Tag: $TAG"
echo "Skip Build: $SKIP_BUILD"
echo ""

# Function to deploy to a specific environment
deploy_to_env() {
  local env=$1
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📍 Deploying to: $env"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  # Step 1: Setup cluster (namespaces + secrets)
  ENV=$env ./scripts/setup-cluster.sh
  
  # Step 2: Deploy services
  ENV=$env TAG=$TAG ./scripts/deploy-services.sh
}

# Deploy to specified environment(s)
if [ "$ENV" = "all" ]; then
  echo "🌍 Deploying to ALL environments (dev, staging, prod)"
  read -p "⚠️  This will deploy to dev, staging, AND production. Continue? (yes/no) " -r
  echo
  if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Deployment cancelled"
    exit 0
  fi
  
  # Build once, deploy to all environments
  if [ "$SKIP_BUILD" != "true" ]; then
    echo ""
    echo "🏗️  Building images once for all environments..."
    TAG=$TAG ./scripts/build-and-push.sh
  fi
  
  deploy_to_env "dev"
  deploy_to_env "staging"
  deploy_to_env "prod"
  
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "✅ Successfully deployed to ALL environments!"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
  # Deploy to single environment
  if [ "$SKIP_BUILD" != "true" ]; then
    echo "🏗️  Step 1: Building and pushing images..."
    TAG=$TAG ./scripts/build-and-push.sh
  else
    echo "⏭️  Skipping build (SKIP_BUILD=true)"
  fi
  
  deploy_to_env "$ENV"
  
  echo ""
  echo "✅ Deployment to $ENV complete!"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Quick Status Check:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$ENV" = "all" ]; then
  for e in dev staging prod; do
    echo ""
    echo "Environment: $e"
    kubectl get pods -n user-service-$e -n payment-service-$e -n item-service-$e 2>/dev/null || echo "  No pods found for $e"
  done
else
  kubectl get pods -n user-service-$ENV -n payment-service-$ENV -n item-service-$ENV
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Usage examples:"
echo "  Deploy to dev:        ENV=dev ./scripts/deploy-all.sh"
echo "  Deploy to staging:    ENV=staging ./scripts/deploy-all.sh"
echo "  Deploy to prod:       ENV=prod ./scripts/deploy-all.sh"
echo "  Deploy to all:        ENV=all ./scripts/deploy-all.sh"
echo "  Skip build:           SKIP_BUILD=true ENV=staging ./scripts/deploy-all.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
