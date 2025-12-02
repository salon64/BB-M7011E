# ArgoCD Installation for LTU M7011E

This directory contains the Helm chart for installing ArgoCD in the LTU M7011E course environment.

## 📋 Installation

1. **Install ArgoCD using Helm:**
   ```bash
   helm install argocd -f values.yaml -n argocd --create-namespace .
   ```

2. **Access ArgoCD:**
   - Web UI: https://argocd.ltu-m7011e-10.se
   - Port forward (alternative): `kubectl port-forward svc/argocd-server -n argocd 8080:443`

3. **Get initial admin password:**
   ```bash
   kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d && echo
   ```

## ArgoCD CLI login 

* **Login command** use the following command to access ArgoCD CLI, switch out your specific credentials if needed: `argocd login argocd.ltu-m7011e-10.se --username admin --password f3gzY3oi9ekJHRaX --insecure`

## ArgoCD creating the application

* **Deploy dev app** use the following command to create the app within argocd. This is done manually since I couldn't get it to work through the UI(it wouldn't recognize it as a helm). Command for creating app(for dev):

```bash
argocd app create payment-service-dev \
  --repo https://github.com/salon64/BB-M7011E.git \
  --revision feat/payment-service \
  --path payment_service/k8s \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace payment-service-dev \
  --values ../../environments/dev/values.yaml \
  --sync-policy automated \
  --auto-prune \
  --self-heal
```

Creating the namespace:

```bash
kubectl create namespace payment-service-dev
```

Create secrets for the supabase keys from the .env file

```bash
kubectl create secret generic payment-service-secrets \
  --from-env-file=/Users/justin/Documents/1-Projekt/M7011E/BB-M7011E/payment_service/.env \
  -n payment-service-dev
```
To delete secrets:

```bash
kubectl delete secret payment-service-secrets -n payment-service-dev
```

Syncing the namespace:

```bash
argocd app sync payment-service-dev
```

* **Deploy staging app**

```bash
argocd app create payment-service-staging \
  --repo https://github.com/salon64/BB-M7011E.git \
  --revision feat/payment-service \
  --path payment_service/k8s \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace payment-service-staging \
  --values ../../environments/staging/values.yaml \
  --sync-policy automated \
  --auto-prune \
  --self-heal
```

* **Deploy production app**

```bash
argocd app create payment-service-prod \
  --repo https://github.com/salon64/BB-M7011E.git \
  --revision feat/payment-service \
  --path payment_service/k8s \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace payment-service-prod \
  --values ../../environments/production/values.yaml \
  --sync-policy manual  # Keep manual for production!
```

## 🔧 Configuration

Update `values.yaml` with specific settings:
- `argocd.domain`: Assigned ArgoCD domain
- `argocd.email`: Email for Let's Encrypt certificates

## Troubleshooting Guide

This guide is based on common issues encountered during the development of this service.

### 1. 404 Page Not Found at ArgoCD Domain

If you get a 404 error when accessing your ArgoCD domain:

* **Cause** the ingress isn't being rendered properly.

* **Solution steps:**

    1. **Check if ArgoCD pods are running:**
    ```bash
    kubectl get pods -n argocd
    ```

    2. **Check if ingress exists:**
    ```bash
    kubectl get ingress -n argocd
    ```

    3. **If no ingress found, manually apply templates:**
    ```bash
    helm template argocd . --namespace argocd | kubectl apply -f -
    ```

    4. **Verify ingress was created:**
    ```bash
    kubectl get ingress -n argocd
    # Should show argocd-server with your domain and an address
    ```

    5. **Check ingress status:**
    ```bash
    kubectl describe ingress argocd-server -n argocd
    ```
