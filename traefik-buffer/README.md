# Traefik Buffer for Supabase

Best-effort HTTP buffering with retries and observability for Supabase requests.

## Architecture

```
┌─────────────────┐         ┌─────────────────────────────┐         ┌──────────────┐
│  Your Services  │  HTTP   │         Traefik             │  HTTP   │   Supabase   │
│  (item_service, │ ──────► │  - Retry (3 attempts)       │ ──────► │              │
│   user_service) │         │  - In-flight limit (50)     │         │              │
│                 │ ◄────── │  - Timeout (120s)           │ ◄────── │              │
└─────────────────┘         └─────────────────────────────┘         └──────────────┘
                                        │
                                        │ metrics
                                        ▼
                            ┌─────────────────────┐
                            │     Prometheus      │
                            │         +           │
                            │      Grafana        │
                            └─────────────────────┘
```

## What This Provides

| Feature | Description |
|---------|-------------|
| ✅ Internal HTTP buffering | Requests routed through Traefik |
| ✅ Backpressure | In-flight request limiting (50 concurrent) |
| ✅ Retry on failures | 3 attempts with exponential backoff |
| ✅ Timeout tuning | 30s dial, 120s response timeout |
| ✅ Prometheus metrics | Full observability |
| ✅ Grafana dashboards | Visual monitoring |

## What This Does NOT Provide

| Limitation | Impact |
|------------|--------|
| ❌ No durability | Requests lost on Traefik restart |
| ❌ No message persistence | No disk-based queue |
| ❌ No guaranteed delivery | Best-effort only |

**This is acceptable only for idempotent, short-lived HTTP requests.**

## Directory Structure

```
traefik-buffer/
├── README.md                  # This file
├── argocd-application.yaml    # Argo CD Application manifests
├── infra/
│   └── traefik.yaml          # Traefik internal service + metrics
├── app/
│   └── supabase-buffer.yaml  # Supabase routing, middlewares, IngressRoute
└── monitoring/
    └── monitoring.yaml       # Prometheus + Grafana stack
```

## Prerequisites

1. **Traefik installed** with CRDs (IngressRoute, Middleware, TraefikService)
2. **Traefik configured** with:
   - `web` entryPoint enabled (port 8000)
   - Prometheus metrics enabled (port 9100)
3. **Argo CD** (optional, for GitOps deployment)

## Deployment

### Option 1: Direct kubectl apply

```bash
# Apply all manifests
kubectl apply -f traefik-buffer/infra/
kubectl apply -f traefik-buffer/app/
kubectl apply -f traefik-buffer/monitoring/
```

### Option 2: Argo CD (GitOps)

```bash
# Update repoURL in argocd-application.yaml first!
kubectl apply -f traefik-buffer/argocd-application.yaml
```

## Usage

### How Services Call Supabase

Instead of calling Supabase directly:

```python
# ❌ Old way - direct to Supabase
supabase_url = "https://your-project.supabase.co"
```

Route through Traefik:

```python
# ✅ New way - through Traefik buffer
supabase_url = "http://traefik-internal.infra.svc.cluster.local/supabase"
```

### Environment Variable Configuration

```yaml
env:
  - name: SUPABASE_URL
    value: "http://traefik-internal.infra.svc.cluster.local/supabase"
```

## Monitoring

### Access Grafana

```bash
# Port forward Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Open http://localhost:3000
# Login: admin / admin
```

### Import Traefik Dashboard

1. Go to Dashboards → Import
2. Enter dashboard ID: **17346** (Traefik v2)
3. Select Prometheus datasource
4. Click Import

### Useful Metrics

| Metric | Description |
|--------|-------------|
| `traefik_entrypoint_requests_total` | Total requests per entrypoint |
| `traefik_service_requests_total` | Requests per service |
| `traefik_service_request_duration_seconds` | Request latency |
| `traefik_service_retries_total` | Number of retries |
| `traefik_service_open_connections` | Current open connections |

## Configuration Tuning

### Adjust In-Flight Limit

Edit [app/supabase-buffer.yaml](app/supabase-buffer.yaml) middleware:

```yaml
spec:
  inFlightReq:
    amount: 100  # Increase for higher throughput
```

### Adjust Timeouts

```yaml
spec:
  forwardingTimeouts:
    dialTimeout: 60s        # Increase for slow connections
    responseHeaderTimeout: 300s  # Increase for slow queries
```

### Adjust Retry Behavior

```yaml
spec:
  retry:
    attempts: 5              # More retries
    initialInterval: 200ms   # Longer initial wait
```

## Troubleshooting

### Check Traefik logs

```bash
kubectl logs -n infra -l app=traefik -f
```

### Check routing configuration

```bash
# List IngressRoutes
kubectl get ingressroute -n app

# Describe specific route
kubectl describe ingressroute supabase-internal -n app
```

### Test connectivity

```bash
# From inside cluster
kubectl run -it --rm debug --image=curlimages/curl -- \
  curl -v http://traefik-internal.infra.svc.cluster.local/supabase/rest/v1/
```

### Check Prometheus targets

```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Open http://localhost:9090/targets
```

## Namespaces

| Namespace | Purpose |
|-----------|---------|
| `infra` | Traefik runtime services |
| `app` | Application routing (middlewares, IngressRoutes) |
| `monitoring` | Prometheus + Grafana |

## Security Considerations

1. **Grafana password**: Change default `admin/admin` in production
2. **Supabase API keys**: Consider using Kubernetes Secrets
3. **Network policies**: Add to restrict traffic flow
4. **TLS**: Enable for production deployments
