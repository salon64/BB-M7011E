# Kubernetes Deployment Checklist

Use this checklist before deploying to production via Kubernetes.

## Pre-Deployment

### Security
- [ ] Generated strong `FLASK_SECRET_KEY` (32+ characters)
- [ ] Set `DEBUG=false`
- [ ] Configured HTTPS/TLS with cert-manager
- [ ] Created Kubernetes secrets properly
- [ ] Reviewed and set proper RBAC policies
- [ ] Enabled secrets encryption at rest in etcd
- [ ] Configured network policies
- [ ] Set up firewall rules at infrastructure level
- [ ] Reviewed Keycloak security settings
- [ ] Enabled audit logging in Kubernetes
- [ ] Configured PodSecurityPolicy or Pod Security Standards

### Kubernetes Configuration
- [ ] Updated all service URLs in values.yaml
- [ ] Verified Keycloak configuration
- [ ] Set correct domain name in ingress
- [ ] Configured resource requests and limits appropriately
- [ ] Set up proper health check intervals (livenessProbe, readinessProbe)
- [ ] Configured correct replica count for HA
- [ ] Set correct image registry and pull secrets if needed
- [ ] Verified namespace configuration
- [ ] Reviewed image pull policy settings
- [ ] Set up node affinity/pod affinity if needed

### Infrastructure
- [ ] Kubernetes cluster is healthy and up-to-date
- [ ] All backend services are deployed and running
- [ ] Keycloak is accessible and healthy
- [ ] Database backups are configured and tested
- [ ] Monitoring (Prometheus) is configured
- [ ] Logging (ELK/Loki) is configured
- [ ] DNS records are set up
- [ ] Load balancer/Ingress controller is configured (Traefik)
- [ ] Certificate issuer (cert-manager) is set up
- [ ] Storage is configured if needed
- [ ] Network policies are in place

### Testing
- [ ] Tested all routes locally before K8s deployment
- [ ] Verified authentication works with Keycloak
- [ ] Tested admin functions
- [ ] Tested user functions
- [ ] Tested item management
- [ ] Tested transaction viewing
- [ ] Load tested application (at least 50 concurrent users)
- [ ] Tested pod restart/failover scenarios
- [ ] Verified health checks work correctly
- [ ] Tested graceful shutdown
- [ ] Tested ingress routing and TLS

## Kubernetes Deployment Steps

### 1. Build and Push Docker Image

```bash
# Build image with version tag
docker build -t your-registry/barcode-buddy-frontend:v1.0.0 .
docker push your-registry/barcode-buddy-frontend:v1.0.0

# Tag as latest
docker tag your-registry/barcode-buddy-frontend:v1.0.0 your-registry/barcode-buddy-frontend:latest
docker push your-registry/barcode-buddy-frontend:latest
```

- [ ] Image built successfully
- [ ] Image pushed to registry
- [ ] Version tagged properly

### 2. Prepare Kubernetes Manifests

```bash
# Generate production secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Update secrets.yaml with generated key
# Update deployment.yaml with correct image
# Update ingress.yaml with correct domain
# Update configmap.yaml if needed
```

- [ ] Secrets updated
- [ ] Deployment updated
- [ ] Ingress updated
- [ ] ConfigMap reviewed

### 3. Create Namespace

```bash
kubectl create namespace barcode-buddy
```

- [ ] Namespace created

### 4. Deploy Secrets First

```bash
kubectl apply -f k8s/secrets.yaml -n barcode-buddy
kubectl get secrets -n barcode-buddy
```

- [ ] Secrets deployed
- [ ] Secrets verified

### 5. Deploy ConfigMap

```bash
kubectl apply -f k8s/configmap.yaml -n barcode-buddy
kubectl get configmap -n barcode-buddy
```

- [ ] ConfigMap deployed
- [ ] ConfigMap verified

### 6. Deploy Application

```bash
kubectl apply -f k8s/deployment.yaml -n barcode-buddy
kubectl get deployments -n barcode-buddy
```

- [ ] Deployment created
- [ ] Pods starting

### 7. Wait for Pods

```bash
kubectl wait --for=condition=ready pod -l app=barcode-buddy-frontend -n barcode-buddy --timeout=120s
kubectl get pods -n barcode-buddy
```

- [ ] All pods are running
- [ ] All pods passed health checks

### 8. Deploy Ingress

```bash
kubectl apply -f k8s/ingress.yaml -n barcode-buddy
kubectl get ingress -n barcode-buddy
```

- [ ] Ingress deployed
- [ ] External IP assigned
- [ ] DNS propagated

## Post-Deployment

### Verification

```bash
# Check all resources
kubectl get all -n barcode-buddy

# Check pod logs
kubectl logs -l app=barcode-buddy-frontend -n barcode-buddy

# Check events
kubectl get events -n barcode-buddy --sort-by='.lastTimestamp'
```

- [ ] All resources healthy
- [ ] No error logs
- [ ] No warning events

### Smoke Testing

Visit your domain and test:

- [ ] Homepage loads
- [ ] Can create account
- [ ] Can login
- [ ] Dashboard accessible
- [ ] Items page works
- [ ] Transactions page works
- [ ] Admin features work (if admin user)
- [ ] Logout works

### Performance Testing

```bash
# Basic load test (requires Apache Bench)
ab -n 1000 -c 10 https://your-domain.com/

# Or use other tools like k6, wrk, etc.
```

- [ ] Response times acceptable
- [ ] No errors under load
- [ ] Resources within limits

### Monitoring Setup

- [ ] Set up Prometheus metrics
- [ ] Configure Grafana dashboards
- [ ] Set up alerting rules
- [ ] Configure uptime monitoring
- [ ] Set up log aggregation

### Backup Configuration

- [ ] Kubernetes manifests in version control
- [ ] Secrets backed up securely
- [ ] Documentation updated
- [ ] Runbooks created

## Rollback Plan

If something goes wrong:

```bash
# Rollback to previous version
kubectl rollout undo deployment/barcode-buddy-frontend -n barcode-buddy

# Or deploy specific version
kubectl set image deployment/barcode-buddy-frontend \
  frontend=your-registry/barcode-buddy-frontend:v0.9.0 \
  -n barcode-buddy
```

- [ ] Rollback procedure tested
- [ ] Previous version available
- [ ] Rollback documentation ready

## Post-Deployment Monitoring

### First 24 Hours

Monitor these metrics:
- [ ] CPU usage
- [ ] Memory usage
- [ ] Request rate
- [ ] Error rate
- [ ] Response time
- [ ] Pod restarts

### First Week

- [ ] Review logs daily
- [ ] Check for any errors
- [ ] Monitor resource usage trends
- [ ] Collect user feedback
- [ ] Document any issues

## Security Audit

Within first week:
- [ ] Review access logs
- [ ] Check for unauthorized access attempts
- [ ] Verify all security headers working
- [ ] Test rate limiting
- [ ] Verify HTTPS enforcement
- [ ] Check certificate expiry dates

## Documentation

- [ ] Update architecture diagrams
- [ ] Document configuration decisions
- [ ] Create runbook for common operations
- [ ] Document troubleshooting steps
- [ ] Update team wiki/docs

## Communication

- [ ] Notify team of deployment
- [ ] Send release notes
- [ ] Update status page
- [ ] Schedule post-deployment review

## Long-term Maintenance

Set up recurring tasks:
- [ ] Weekly: Review logs and metrics
- [ ] Monthly: Security updates
- [ ] Monthly: Certificate rotation check
- [ ] Quarterly: Load testing
- [ ] Quarterly: Disaster recovery drill
- [ ] Yearly: Full security audit

## Success Criteria

Deployment is successful when:
- [ ] All pods are running and healthy
- [ ] Application is accessible via HTTPS
- [ ] All features work as expected
- [ ] No errors in logs
- [ ] Performance metrics acceptable
- [ ] Monitoring is active
- [ ] Team is notified and trained

---

## Emergency Contacts

Add your team contacts:

- On-call Engineer: _______________
- DevOps Lead: _______________
- Backend Team: _______________
- Security Team: _______________

## Notes

Add any deployment-specific notes here:

_________________________________
_________________________________
_________________________________
