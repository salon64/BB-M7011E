
# Supabase Buffer Service

This service provides HTTP request buffering, retries, and circuit breaking for Supabase via an Envoy proxy. All requests are routed through Envoy for reliability and observability.

---

## Usage

### How to Send Requests

If your service is deployed in the same namespace as the buffer:

```bash
http://supabase-buffer:8000
```

Example with curl:

```bash
curl -X POST http://supabase-buffer:8000/rest/v1/Items \
  -H "apikey: <YOUR_SUPABASE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Coffee","price":350}'
```

All requests flow through Envoy before reaching the actual Supabase backend (192.168.1.136:8000).

### Migration: Switching to the Buffered Service

Update your Supabase URL to use the buffered version:

| Original (Direct) | Buffered (via Envoy) |
|-------------------|----------------------|
| `http://supabase.bb.svc.cluster.local:8000` | `http://supabase-buffer.<namespace>.svc.cluster.local:8000` |

**Same namespace shorthand:**
```bash
http://supabase-buffer:8000
```

**Cross-namespace:**
```bash
http://supabase-buffer.app.svc.cluster.local:8000
```

### How to Verify Traffic is Buffered

Check Envoy metrics for active connections:

```bash
kubectl exec -n <namespace> deployment/supabase-buffer -c envoy -- \
  curl -s localhost:9901/stats | grep downstream_cx_active
```

Check request count:

```bash
kubectl exec -n <namespace> deployment/supabase-buffer -c envoy -- \
  curl -s localhost:9901/stats | grep downstream_rq_total
```

Or view real-time traffic in Grafana (Dashboard ID 11021, metric: `envoy_http_downstream_rq_total`).

---

## Features

- HTTP request buffering (max 200 pending requests)
- Automatic retries on 5xx errors
- Circuit breaking
- Prometheus metrics export
- 120s request timeout

## Monitoring

Envoy metrics endpoint:

    http://supabase-buffer:9901/stats/prometheus

Import dashboard **ID 11021** in Grafana to visualize buffer pressure, retries, and latency.
#

