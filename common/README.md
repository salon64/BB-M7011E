# BB Common Package

Shared authentication and utilities for BB Microservices.

## Installation

Install the package locally in development mode:

```bash
pip install -e ./common
```

Or in a Dockerfile:

```dockerfile
COPY common /app/common
RUN pip install /app/common
```

## Usage

```python
from common.auth import require_auth, require_admin, require_bb_admin

# In your FastAPI routes:
@app.get("/protected")
async def protected_route(token_data: dict = Depends(require_auth)):
    return {"user": token_data["preferred_username"]}

@app.get("/admin-only")
async def admin_route(token_data: dict = Depends(require_admin)):
    return {"admin": token_data["preferred_username"]}

@app.get("/bb-admin-only")
async def bb_admin_route(token_data: dict = Depends(require_bb_admin)):
    return {"bb_admin": token_data["preferred_username"]}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KEYCLOAK_URL` | Base URL for Keycloak server | `https://keycloak.ronstad.se` |
| `KEYCLOAK_REALM` | Keycloak realm name | `BB` |
| `INSECURE` | Skip SSL certificate verification (dev only) | `false` |

## Exported Functions

- `require_auth` - FastAPI dependency for authenticated routes
- `require_admin` - FastAPI dependency requiring `admin` role
- `require_bb_admin` - FastAPI dependency requiring `bb_admin` role
- `verify_jwt_token` - Low-level function to verify and decode JWT tokens
- `get_jwks_client` - Get the PyJWKClient instance for the configured Keycloak
