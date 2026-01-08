# BB Common Package
# Shared authentication and utilities for BB microservices

from common.auth import (
    require_auth,
    require_admin,
    require_bb_admin,
    verify_jwt_token,
    get_jwks_client,
    security,
    KEYCLOAK_URL,
    KEYCLOAK_REALM,
    CERTS_URL,
    INSECURE,
)

from common.database import (
    get_supabase_client,
    get_supabase,
)

__all__ = [
    "require_auth",
    "require_admin",
    "require_bb_admin",
    "verify_jwt_token",
    "get_jwks_client",
    "security",
    "KEYCLOAK_URL",
    "KEYCLOAK_REALM",
    "CERTS_URL",
    "INSECURE",
    "get_supabase_client",
    "get_supabase",
]
