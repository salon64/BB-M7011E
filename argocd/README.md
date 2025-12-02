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
