# Monitoring Stack

Prometheus and Grafana deployment for monitoring the Envoy Supabase buffer service.

## Components

- **Prometheus**: Scrapes metrics from Envoy sidecar
- **Grafana**: Visualizes metrics and dashboards
- **IngressRoute**: Exposes Grafana at metrics.ronstad.se

## Deployment

Deploy via ArgoCD:

1. Create new Application in ArgoCD UI
2. Set path: `monitoring`
3. Set namespace: `monitoring` (or your preference)
4. Sync

## Access

- Grafana: https://metrics.ronstad.se
- Default credentials: admin / admin (change after first login)

## Prometheus Configuration

Prometheus is configured to scrape:
- Itself (localhost:9090)
- Envoy Supabase buffer (supabase-buffer:9901/stats/prometheus)

## Grafana Setup

1. Login to Grafana at https://metrics.ronstad.se
2. Prometheus datasource is pre-configured
3. Import dashboard ID **11021** (Envoy Proxy Global) for Envoy metrics
4. Create custom dashboards as needed

## Monitoring Envoy

Key metrics to watch:
- `envoy_http_downstream_rq_pending` - Pending requests (buffer pressure)
- `envoy_cluster_upstream_rq_retry` - Retry count
- `envoy_cluster_upstream_rq_timeout` - Timeout count
- `envoy_cluster_circuit_breakers_*` - Circuit breaker status
