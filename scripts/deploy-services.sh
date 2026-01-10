#!/bin/bash
set -e

# Configuration
REGISTRY="${DOCKER_REGISTRY:-justingav}"
TAG="${TAG:-latest}"
ENV="${ENV:-dev}"  # dev, staging, or production

# Map prod to production for folder names
VALUES_ENV="${ENV}"
if [ "$ENV" = "prod" ]; then
  VALUES_ENV="production"
fi

echo "☸️  BB-M7011E Service Deployment"
echo "================================"
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo "Environment: $ENV"
echo ""

# Check if kubectl is configured
if ! kubectl cluster-info > /dev/null 2>&1; then
  echo "❌ kubectl is not configured. Please configure kubectl and try again."
  exit 1
fi

# Deploy services with kubectl apply
echo "📦 Deploying services..."
echo ""

echo "  Deploying user-service to ${ENV}..."
helm template user-service ./user_service/k8s \
  --namespace user-service-${ENV} \
  --values ./environments/${VALUES_ENV}/values.yaml \
  --set userService.image=$REGISTRY/user-service \
  --set userService.tag=$TAG | kubectl apply -n user-service-${ENV} -f -

echo "  Deploying payment-service to ${ENV}..."
helm template payment-service ./payment_service/k8s \
  --namespace payment-service-${ENV} \
  --values ./environments/${VALUES_ENV}/values.yaml \
  --set app.image=$REGISTRY/payment-service \
  --set app.tag=$TAG | kubectl apply -n payment-service-${ENV} -f -

echo "  Deploying item-service to ${ENV}..."
helm template item-service ./item_service/k8s \
  --namespace item-service-${ENV} \
  --values ./environments/${VALUES_ENV}/values.yaml \
  --set itemService.image=$REGISTRY/item-service \
  --set itemService.tag=$TAG | kubectl apply -n item-service-${ENV} -f -

if [ -d discord_bot/k8s ]; then
  echo "  Deploying discord-bot..."
  helm template discord-bot ./discord_bot/k8s \
    --set image.repository=$REGISTRY/discord-bot \
    --set image.tag=$TAG | kubectl apply -f - || echo "⚠️  Discord bot deployment failed or skipped"
fi

echo ""
echo "✅ All services deployed successfully!"
echo ""

# Show status
echo "📊 Service Status:"
echo ""
kubectl get pods -n user-service-${ENV}
kubectl get pods -n payment-service-${ENV}
kubectl get pods -n item-service-${ENV}
echo ""

echo "🌐 Ingresses:"
kubectl get ingress -n user-service-${ENV}
kubectl get ingress -n payment-service-${ENV}
kubectl get ingress -n item-service-${ENV}
echo ""

echo "💡 Useful commands:"
echo "  View logs:        kubectl logs -f deployment/user-service-${ENV} -n user-service-${ENV}"
echo "  Check services:   kubectl get svc -n user-service-${ENV}"
echo "  Port forward:     kubectl port-forward svc/user-service 8004:8004 -n user-service-${ENV}"
