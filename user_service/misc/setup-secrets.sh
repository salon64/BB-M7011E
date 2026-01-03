#!/bin/bash
# Setup Keycloak secrets for user-service

NAMESPACE="bb"

# Keycloak credentials
KEYCLOAK_ADMIN_USER="admin"
KEYCLOAK_ADMIN_PASS="TODO"
KEYCLOAK_CLIENT_ID="user-service"
KEYCLOAK_CLIENT_SECRET="TODO"  # Update this with your actual client secret

# Create or update keycloak-secret in the bb namespace
kubectl create secret generic keycloak-secret \
  --namespace="$NAMESPACE" \
  --from-literal=KEYCLOAK_ADMIN_USER="$KEYCLOAK_ADMIN_USER" \
  --from-literal=KEYCLOAK_ADMIN_PASS="$KEYCLOAK_ADMIN_PASS" \
  --from-literal=KEYCLOAK_CLIENT_ID="$KEYCLOAK_CLIENT_ID" \
  --from-literal=KEYCLOAK_CLIENT_SECRET="$KEYCLOAK_CLIENT_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✓ keycloak-secret created/updated in namespace $NAMESPACE"
