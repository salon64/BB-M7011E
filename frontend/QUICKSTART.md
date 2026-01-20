# Quick Start Guide - Barcode Buddy Frontend

## Deployment via Kubernetes (Required)

This frontend is designed to be deployed exclusively through Kubernetes.

### Prerequisites

- Kubernetes cluster running
- kubectl configured and connected to your cluster
- All backend services deployed (user-service, item-service, payment-service)
- Keycloak instance running
- ArgoCD (optional, for GitOps deployments)

### Option 1: Deploy with Helm

```bash
# From the project root
helm install frontend ./frontend/k8s \
  --namespace default \
  --values frontend/k8s/values.yaml
```

### Option 2: Deploy with kubectl

```bash
# Apply all Kubernetes manifests
kubectl apply -f frontend/k8s/

# Verify deployment
kubectl get pods -l app=frontend
kubectl get svc barcode-buddy-frontend
kubectl get ingress barcode-buddy-frontend
```

### Option 3: Deploy with ArgoCD (Recommended)

The project includes ArgoCD configuration for GitOps-based deployment. Commit your changes and ArgoCD will automatically sync.

```bash
# Check ArgoCD status
argocd app get barcode-buddy-frontend
```

## Verify Deployment

```bash
# Check pod status
kubectl get pods -l app=frontend

# Check logs
kubectl logs -l app=frontend -f

# Test health endpoint
kubectl port-forward svc/barcode-buddy-frontend 5000:80
curl http://localhost:5000/health
```

## Configuration

Update `frontend/k8s/values.yaml` with your configuration:

```yaml
frontend:
  domain: www.ronstad.se
  image: olleronstad/bb_frontend
  tag: latest

ingress:
  enabled: true
  certIssuer: "letsencrypt-prod"
```

## Local Development

For development purposes only, you can run locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run development server
python app.py
```

**Note**: Local development is for testing only. All production deployments must use Kubernetes.
  -e TRANSACTIONS_SERVICE_URL="http://transactions-service:8003" \
  barcode-buddy-frontend:latest
```

Visit `http://localhost:5000` 🎉

## Option 3: Kubernetes (Production)

### Step 1: Generate Secret Key

```bash
# Generate secret
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Update secrets.yaml
sed -i "s/CHANGE_THIS_TO_A_RANDOM_SECRET_KEY/$SECRET_KEY/g" k8s/secrets.yaml
```

### Step 2: Update Image

Edit `k8s/deployment.yaml` and change:
```yaml
image: your-registry/barcode-buddy-frontend:latest
```

### Step 3: Deploy

```bash
# Create namespace
kubectl create namespace barcode-buddy

# Deploy everything
kubectl apply -f k8s/ -n barcode-buddy

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=barcode-buddy-frontend -n barcode-buddy --timeout=60s
```

### Step 4: Access

```bash
# Port forward for testing
kubectl port-forward -n barcode-buddy service/barcode-buddy-frontend 5000:80

# Or configure ingress and visit your domain
```

Visit `http://localhost:5000` 🎉

## First Login

### Create Your First User

1. Go to homepage
2. Click "Sign Up"
3. Fill in the form
4. Login with your credentials

**Note**: To make yourself an admin, add the `bb_admin` role in Keycloak.

## Verify Everything Works

### Test Checklist

- [ ] Login works
- [ ] Dashboard loads
- [ ] Can view items list
- [ ] Can create item (if admin)
- [ ] Can view transactions
- [ ] Can make payment
- [ ] Logout works

## Troubleshooting

### Can't connect to microservices?

Check if services are running:

```bash
# Local
curl http://localhost:8001/health  # Items service
curl http://localhost:8002/health  # Users service
curl http://localhost:8003/health  # Transactions service

# Kubernetes
kubectl get pods -n barcode-buddy
kubectl get svc -n barcode-buddy
```

### Login fails?

1. Check Keycloak is accessible
2. Verify `KC_URL`, `KC_REALM`, `KC_CLIENT_ID` in environment
3. Ensure user exists in Keycloak

### Application won't start?

Check logs:

```bash
# Docker
docker logs bb-frontend

# Kubernetes
kubectl logs -l app=barcode-buddy-frontend -n barcode-buddy
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Configure HTTPS/TLS for production
- Set up monitoring and logging
- Configure backup procedures
- Review security checklist in README

## Need Help?

1. Check application logs
2. Verify all services are running
3. Review README.md troubleshooting section
4. Check Kubernetes events: `kubectl get events -n barcode-buddy`
