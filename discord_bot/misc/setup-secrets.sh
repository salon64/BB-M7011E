#!/bin/bash
# Setup Discord bot secrets for discord-bot service

NAMESPACE="bb"

# Discord bot token (replace with your actual token)
DISCORD_TOKEN="todo"

# Keycloak client secret for discord-to-user client (replace with your actual secret)
DISCORD_CLIENT_SECRET="TODO"

# Create or update discord-bot-secrets in the bb namespace
kubectl create secret generic discord-bot-secrets \
  --namespace="$NAMESPACE" \
  --from-literal=discord-token="$DISCORD_TOKEN" \
  --from-literal=discord-client-secret="$DISCORD_CLIENT_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✓ discord-bot-secrets created/updated in namespace $NAMESPACE"
