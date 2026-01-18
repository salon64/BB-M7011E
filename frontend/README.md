# Barcode Buddy Frontend

A modern, responsive web frontend for the Barcode Buddy microservice system built with Flask. This application provides a complete user interface for managing items, users, transactions, and payments.

**Deployment**: Kubernetes only (see `k8s/` directory)

## Features

- 🔐 **Authentication** - Keycloak integration with JWT tokens
- 📦 **Item Management** - Create, edit, and manage inventory items with barcode support
- 👥 **User Management** - User accounts with balance tracking
- 💳 **Transactions** - Complete transaction history and payment processing
- 🎨 **Modern UI** - Clean, dark-themed interface with responsive design
- 🔒 **Role-Based Access** - Admin and user roles with different permissions
- 🚀 **Production Ready** - Containerized and deployed via Kubernetes

## Tech Stack

- **Backend**: Flask 3.0
- **Frontend**: HTML5, CSS3 (no JavaScript framework)
- **Authentication**: Keycloak (OAuth2/OIDC)
- **Container**: Docker
- **Orchestration**: Kubernetes (required)
- **WSGI Server**: Gunicorn
- **Ingress**: Traefik with cert-manager

## Project Structure

```
frontend/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker container configuration
├── .dockerignore              # Docker ignore file
├── .env.example               # Environment variables template
├── templates/                 # HTML templates
│   ├── base.html             # Base template with layout
│   ├── index.html            # Homepage
│   ├── login.html            # Login page
│   ├── dashboard.html        # Main dashboard
│   ├── 404.html              # 404 error page
│   ├── 500.html              # 500 error page
│   ├── items/                # Item templates
│   │   ├── list.html
│   │   ├── create.html
│   │   └── edit.html
│   ├── users/                # User templates
│   │   ├── list.html
│   │   ├── create.html
│   │   └── view.html
│   ├── transactions/         # Transaction templates
│   │   ├── list.html
│   │   └── view.html
│   └── payments/             # Payment templates
│       └── debit.html
└── k8s/                      # Kubernetes deployment (required)
    ├── deployment.yaml       # Deployment and Service
    ├── secrets.yaml          # Secrets (template)
    ├── configmap.yaml        # Configuration
    ├── ingress.yaml          # Ingress configuration (Traefik)
    ├── values.yaml           # Helm values
    └── Chart.yaml            # Helm chart metadata
```

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured and connected to your cluster
- Docker (for building images)
- All backend services deployed:
  - User Service
  - Item Service  
  - Payment Service
- Keycloak instance running
- Traefik Ingress Controller
- cert-manager for TLS certificates

## Deployment

### Quick Start

See [QUICKSTART.md](./QUICKSTART.md) for Kubernetes deployment options:

1. **Helm**: `helm install frontend ./k8s --values k8s/values.yaml`
2. **kubectl**: `kubectl apply -f k8s/`
3. **ArgoCD**: Automatic GitOps-based deployment

### Full Documentation

See [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) for complete pre-deployment checklist.

## Local Development Setup (Development Only)

For development and testing only - production deployments must use Kubernetes.

### 1. Setup Virtual Environment

```bash
python -m venv venv

# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

Required environment variables:

```env
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here  # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
DEBUG=true  # Set to false in production

# Microservice URLs (adjust ports as needed)
ITEMS_SERVICE_URL=http://localhost:8001
USERS_SERVICE_URL=http://localhost:8002
TRANSACTIONS_SERVICE_URL=http://localhost:8003

# Keycloak Configuration
KC_URL=https://keycloak.ronstad.se
KC_REALM=BB
KC_CLIENT_ID=public-user

# Security
INSECURE=false  # Set to true only for development with self-signed certs
```

### 5. Run Development Server

```bash
# Using Flask development server
python app.py

# Or using Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 --reload app:app
```

The application will be available at `http://localhost:5000`

## Docker Deployment

### 1. Build Docker Image

```bash
# Build the image
docker build -t barcode-buddy-frontend:latest .

# Tag for your registry (optional)
docker tag barcode-buddy-frontend:latest your-registry/barcode-buddy-frontend:latest
```

### 2. Run Container Locally

```bash
docker run -d \
  --name barcode-buddy-frontend \
  -p 5000:5000 \
  -e FLASK_SECRET_KEY="your-secret-key" \
  -e ITEMS_SERVICE_URL="http://items-service:8001" \
  -e USERS_SERVICE_URL="http://user-service:8004" \
  -e TRANSACTIONS_SERVICE_URL="http://transactions-service:8003" \
  -e KC_URL="https://keycloak.ronstad.se" \
  -e KC_REALM="BB" \
  -e KC_CLIENT_ID="public-user" \
  barcode-buddy-frontend:latest
```

### 3. Test the Container

```bash
# Check if container is running
docker ps

# View logs
docker logs barcode-buddy-frontend

# Test health endpoint
curl http://localhost:5000/health
```

### 4. Push to Registry

```bash
# Push to your container registry
docker push your-registry/barcode-buddy-frontend:latest
```

## Kubernetes Deployment

### 1. Prepare Secrets

First, generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Edit `k8s/secrets.yaml` and replace the placeholder with your generated key:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: frontend-secrets
type: Opaque
stringData:
  flask-secret-key: "YOUR_GENERATED_SECRET_KEY_HERE"
```

### 2. Update Configuration

Edit `k8s/configmap.yaml` if needed to match your service names and URLs:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config
data:
  ITEMS_SERVICE_URL: "http://items-service:8001"
  USERS_SERVICE_URL: "http://user-service:8004"
  TRANSACTIONS_SERVICE_URL: "http://transactions-service:8003"
  KC_URL: "https://keycloak.ronstad.se"
  KC_REALM: "BB"
  KC_CLIENT_ID: "public-user"
```

### 3. Update Deployment

Edit `k8s/deployment.yaml`:

- Replace `your-registry/barcode-buddy-frontend:latest` with your actual image
- Adjust resource limits if needed
- Update service URLs if they differ from defaults

### 4. Configure Ingress

Edit `k8s/ingress.yaml`:

```yaml
spec:
  rules:
  - host: barcode-buddy.yourdomain.com  # Change to your domain
```

For HTTPS with cert-manager:

```yaml
metadata:
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - barcode-buddy.yourdomain.com
    secretName: barcode-buddy-tls
```

### 5. Deploy to Kubernetes

```bash
# Create namespace (optional)
kubectl create namespace barcode-buddy

# Apply all manifests
kubectl apply -f k8s/secrets.yaml -n barcode-buddy
kubectl apply -f k8s/configmap.yaml -n barcode-buddy
kubectl apply -f k8s/deployment.yaml -n barcode-buddy
kubectl apply -f k8s/ingress.yaml -n barcode-buddy
```

### 6. Verify Deployment

```bash
# Check pods
kubectl get pods -n barcode-buddy

# Check service
kubectl get svc -n barcode-buddy

# Check ingress
kubectl get ingress -n barcode-buddy

# View logs
kubectl logs -f deployment/barcode-buddy-frontend -n barcode-buddy

# Check pod status in detail
kubectl describe pod <pod-name> -n barcode-buddy
```

### 7. Access the Application

Once the ingress is configured:
- Visit `http://barcode-buddy.yourdomain.com` (or your configured domain)
- Or use port forwarding for testing:

```bash
kubectl port-forward -n barcode-buddy service/barcode-buddy-frontend 5000:80
# Then visit http://localhost:5000
```

## Kubernetes Troubleshooting

### Pod Not Starting

```bash
# Describe pod for events
kubectl describe pod <pod-name> -n barcode-buddy

# Check logs
kubectl logs <pod-name> -n barcode-buddy

# Check previous logs if pod crashed
kubectl logs <pod-name> -n barcode-buddy --previous
```

### Service Connection Issues

```bash
# Test service connectivity from within cluster
kubectl run -it --rm debug --image=busybox --restart=Never -n barcode-buddy -- sh
# Inside the pod:
wget -O- http://barcode-buddy-frontend/health
```

### Update Deployment

```bash
# Update image
kubectl set image deployment/barcode-buddy-frontend \
  frontend=your-registry/barcode-buddy-frontend:new-tag \
  -n barcode-buddy

# Or apply updated manifests
kubectl apply -f k8s/deployment.yaml -n barcode-buddy

# Force rollout
kubectl rollout restart deployment/barcode-buddy-frontend -n barcode-buddy
```

### Scale Deployment

```bash
# Scale up/down
kubectl scale deployment/barcode-buddy-frontend --replicas=3 -n barcode-buddy
```

## Configuration Details

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FLASK_SECRET_KEY` | Secret key for Flask sessions | None | Yes |
| `DEBUG` | Enable debug mode | `false` | No |
| `ITEMS_SERVICE_URL` | Items microservice URL | `http://localhost:8001` | Yes |
| `USERS_SERVICE_URL` | Users microservice URL | `http://localhost:8004` | Yes |
| `TRANSACTIONS_SERVICE_URL` | Transactions microservice URL | `http://localhost:8003` | Yes |
| `KC_URL` | Keycloak server URL | `https://keycloak.ronstad.se` | Yes |
| `KC_REALM` | Keycloak realm name | `BB` | Yes |
| `KC_CLIENT_ID` | Keycloak client ID | `public-user` | Yes |
| `INSECURE` | Skip SSL verification (dev only) | `false` | No |

### Keycloak Configuration

The application uses Keycloak for authentication. Users must exist in Keycloak with:

- **Username**: Used for login
- **Password**: User's password
- **Roles**: 
  - `bb_admin` - Full admin access
  - Regular users - Limited access to their own data

### Service Discovery

In Kubernetes, services are accessed by name:
- `http://items-service:8001`
- `http://users-service:8002`
- `http://transactions-service:8003`

Make sure these services are deployed in the same namespace or adjust the URLs to include the namespace:
- `http://items-service.barcode-buddy.svc.cluster.local:8001`

## API Endpoints

The frontend interacts with these microservice endpoints:

### Items Service
- `GET /health` - Health check
- `POST /items` - Create item (admin)
- `POST /items/list` - List items
- `POST /items/fetch_info` - Fetch item by ID
- `POST /items/fetch_by_barcode` - Fetch by barcode
- `PUT /items/update` - Update item (admin)
- `POST /items/set_status` - Set active status (admin)
- `DELETE /items/delete` - Delete item (admin)

### Users Service
- `GET /health` - Health check
- `POST /users` - Create user (public)
- `POST /user/fetch_info` - Fetch user info
- `POST /user/add_balance` - Add balance
- `POST /user/set_status` - Set active status (admin)

### Transactions Service
- `GET /health` - Health check
- `GET /transactions/history` - List transactions
- `GET /transactions/history/{id}` - Get transaction
- `POST /payments/debit` - Process payment

## User Guide

### Creating an Account

1. Visit the homepage
2. Click "Sign Up"
3. Fill in:
   - Full Name
   - Username (for login)
   - Email
   - Password (minimum 8 characters)
4. Click "Create Account"
5. Login with your credentials

### Managing Items (Admin Only)

1. Login as admin user
2. Navigate to "Items"
3. Click "+ Create Item"
4. Fill in:
   - Item Name
   - Price (in öre/cents, e.g., 1000 = 10.00 kr)
   - Barcode ID (optional)
5. Click "Create Item"

### Making a Payment

1. Login to your account
2. Go to "Make Payment" or Dashboard
3. Enter:
   - User ID (card ID)
   - Select Item from dropdown
   - Amount (auto-filled from item price)
4. Click "Process Payment"

### Viewing Transactions

1. Navigate to "Transactions"
2. View complete transaction history
3. Click "View Details" for specific transaction info
4. Filter by user ID if needed

## Security Considerations

### Production Checklist

- [ ] Generate strong `FLASK_SECRET_KEY` (32+ characters)
- [ ] Set `DEBUG=false` in production
- [ ] Use HTTPS/TLS for all traffic
- [ ] Enable Kubernetes secrets encryption at rest
- [ ] Configure proper RBAC for Kubernetes
- [ ] Set appropriate resource limits
- [ ] Enable network policies
- [ ] Use secure Keycloak configuration
- [ ] Regular security updates for base images
- [ ] Implement rate limiting at ingress level
- [ ] Configure CORS properly
- [ ] Enable audit logging

### Security Headers

Consider adding these headers via Kubernetes ingress annotations:

```yaml
nginx.ingress.kubernetes.io/configuration-snippet: |
  more_set_headers "X-Frame-Options: DENY";
  more_set_headers "X-Content-Type-Options: nosniff";
  more_set_headers "X-XSS-Protection: 1; mode=block";
  more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
```

## Monitoring

### Health Checks

The application provides a health endpoint:

```bash
curl http://your-domain/health
```

Response:
```json
{"status": "healthy"}
```

### Logging

Application logs are sent to stdout/stderr and can be viewed:

```bash
# Docker
docker logs barcode-buddy-frontend

# Kubernetes
kubectl logs -f deployment/barcode-buddy-frontend -n barcode-buddy
```

### Metrics

Consider integrating:
- Prometheus for metrics collection
- Grafana for visualization
- Sentry for error tracking

## Common Issues

### Cannot Connect to Microservices

**Problem**: Frontend can't reach backend services

**Solutions**:
1. Check service URLs are correct
2. Verify services are running: `kubectl get svc -n barcode-buddy`
3. Test connectivity: `kubectl exec -it <pod> -- wget -O- http://items-service:8001/health`
4. Check network policies

### Login Fails

**Problem**: Cannot authenticate with Keycloak

**Solutions**:
1. Verify Keycloak URL is accessible
2. Check realm and client ID configuration
3. Ensure user exists in Keycloak
4. Check Keycloak logs for errors
5. Verify network connectivity to Keycloak

### 500 Internal Server Error

**Problem**: Application crashes or returns 500 error

**Solutions**:
1. Check application logs: `kubectl logs <pod>`
2. Verify all environment variables are set
3. Ensure secret key is configured
4. Check microservice connectivity
5. Review error details in logs

### Session Expires Quickly

**Problem**: Users logged out frequently

**Solutions**:
1. Generate a proper `FLASK_SECRET_KEY`
2. Check if pods are restarting (loses session data)
3. Consider using Redis for session storage
4. Increase Keycloak token lifetime

## Performance Tuning

### Gunicorn Workers

Adjust workers based on CPU cores:

```python
# In Dockerfile or deployment
workers = (2 * cpu_cores) + 1
```

### Resource Limits

Adjust based on load:

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "1Gi"  # Increase if needed
    cpu: "1000m"   # Increase if needed
```

### Caching

Consider adding:
- Flask-Caching for response caching
- Redis for session storage
- CDN for static assets (if you add any)

## Development Tips

### Hot Reload

For development, use Flask's debug mode:

```bash
export DEBUG=true
python app.py
```

### Adding New Routes

1. Add route handler in `app.py`:
```python
@app.route('/new-route')
@login_required
def new_route():
    return render_template('new_template.html')
```

2. Create template in `templates/`:
```html
{% extends "base.html" %}
{% block content %}
<!-- Your content -->
{% endblock %}
```

3. Add navigation link in `base.html` if needed

### Customizing Design

All styling is in `templates/base.html` in the `<style>` section. Modify CSS variables:

```css
:root {
    --primary: #2563eb;      /* Primary color */
    --secondary: #10b981;    /* Secondary color */
    --bg: #0f172a;          /* Background */
    /* ... more variables */
}
```

## Backup and Recovery

### Database Backups

The frontend doesn't store data, but ensure your backend services have proper backup:

1. Regular Postgres backups
2. Keycloak realm exports
3. Configuration backups

### Disaster Recovery

1. Keep Kubernetes manifests in version control
2. Document all configuration changes
3. Test restore procedures regularly
4. Maintain infrastructure as code

## Contributing

When contributing:

1. Follow Python PEP 8 style guide
2. Add docstrings to functions
3. Update documentation
4. Test changes locally
5. Update Kubernetes manifests if needed

## License

[Add your license information here]

## Support

For issues and questions:
- Check logs first
- Review this documentation
- Check Kubernetes events
- Verify microservice health
- Contact your system administrator

## Changelog

### Version 1.0.0 (2026-01-09)
- Initial release
- Flask web frontend
- Keycloak authentication
- Full CRUD operations for items
- User management
- Transaction tracking
- Payment processing
- Docker support
- Kubernetes deployment manifests
- Comprehensive documentation
