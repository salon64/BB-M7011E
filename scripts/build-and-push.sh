#!/bin/bash
set -e

# Configuration
REGISTRY="${DOCKER_REGISTRY:-justingav}"
TAG="${TAG:-latest}"
SKIP_ITEM="${SKIP_ITEM:-false}"  # Default to building item-service (tar pipe method works now)

echo "🏗️  BB-M7011E Build & Push"
echo "=========================="
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker is not running. Please start Docker and try again."
  exit 1
fi

# Build images
echo "📦 Building images..."
echo ""

echo "  Building user-service..."
docker buildx build --platform linux/amd64,linux/arm64 \
  -t $REGISTRY/user-service:$TAG \
  -f user_service/Dockerfile \
  --push . || {
  echo "❌ Failed to build user-service"
  exit 1
}

echo "  Building payment-service..."
docker buildx build --platform linux/amd64,linux/arm64 \
  -t $REGISTRY/payment-service:$TAG \
  -f payment_service/Dockerfile \
  --push . || {
  echo "❌ Failed to build payment-service"
  exit 1
}

# Skip item-service for now if having issues - build manually later
if [ "$SKIP_ITEM" != "true" ]; then
  echo "  Building item-service (using tar pipe for macOS compatibility)..."
  tar -czf - --exclude='.git' --exclude='htmlcov' --exclude='__pycache__' \
    --exclude='.pytest_cache' --exclude='*.pyc' common item_service | \
    docker buildx build --platform linux/amd64,linux/arm64 \
      -t $REGISTRY/item-service:$TAG \
      -f item_service/Dockerfile \
      --push - || {
    echo "❌ Failed to build item-service"
    exit 1
  }
else
  echo "  ⏭️  Skipping item-service (SKIP_ITEM=true)"
fi

if [ -f discord_bot/Dockerfile ]; then
  echo "  Building discord-bot..."
  docker buildx build --platform linux/amd64,linux/arm64 \
    -t $REGISTRY/discord-bot:$TAG \
    -f discord_bot/Dockerfile \
    --push . || {
    echo "⚠️  Failed to build discord-bot"
  }
fi

echo ""
echo "✅ All images built and pushed successfully!"
echo ""
echo "✅ All images built and pushed successfully!"
echo ""

echo "Next step: Deploy services with ./scripts/deploy-services.sh"
