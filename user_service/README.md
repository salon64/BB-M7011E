# User Service

### Key Technologies

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Keycloak
- **Containerization**: Docker
- **Orchestration**: Kubernetes (Helm)
- **Testing**: Pytest with coverage

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker
- Kubernetes cluster with kubectl configured
- Helm 3.x
- A Supabase project (see **Database Setup** below)
- A Keycloak instance

### Local Development

#### 1. Install Dependencies

```bash
cd user_service
pip install -r requirements.txt
```

#### 2. Configure Environment

Create a `.env` file in the user_service directory:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key

KEYCLOAK_URL=https://your-keycloak-instance.com
KEYCLOAK_REALM=BBosch
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=your_admin_password
KEYCLOAK_CLIENT_ID=user-service
KEYCLOAK_CLIENT_SECRET=your_client_secret
KEYCLOAK_CALLBACK_URI=http://localhost:8004/callback

# Set to 'true' to skip SSL certificate verification (dev only with self-signed certs)
INSECURE=false

LOG_LEVEL=DEBUG
```

#### 3. Run the Service Locally

```bash
# Make sure environment variables are exported
export INSECURE=true  # If using self-signed certificates
export KEYCLOAK_URL=https://your-keycloak-instance.com
export KEYCLOAK_REALM=BBosch

# Run with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8080

# Or run directly
python main.py
```

The service will be available at `http://localhost:8080`. Access the API documentation at `http://localhost:8080/docs`.

---

## Authentication

The User Service uses JWT tokens issued by Keycloak for authentication. Protected endpoints require a valid Bearer token in the Authorization header.

### Getting a Token

Use the provided helper script to obtain a token:

```bash
# Set your credentials
export KC_URL=https://your-keycloak-instance.com
export KC_REALM=BBosch
export KC_CLIENT_ID=your-client-id
export KC_CLIENT_SECRET=your-client-secret
export KC_USERNAME=your-username
export KC_PASSWORD=your-password
export KC_INSECURE=true  # Only for self-signed certs

# Get and decode token
python get_token.py
```

This script will:
- Request a token from Keycloak
- Decode the token (without verification)
- Validate the token signature using Keycloak's public keys
- Display the full token payload

### Testing Authentication

Test the `/auth/jwt` endpoint to verify token decoding:

```bash
# Get a token and test the endpoint
python test_auth_endpoint.py
```

Or manually with curl:

```bash
# Get token first
TOKEN=$(curl -s -X POST "https://keycloak.example.com/realms/BBosch/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=your-client-id" \
  -d "client_secret=your-secret" \
  -d "username=your-user" \
  -d "password=your-pass" | jq -r '.access_token')

# Test authenticated endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/auth/jwt
```

## Kubernetes Deployment

### Prerequisites: Setup Secrets

Before deploying, create the required Kubernetes secrets in the `bb` namespace:

```bash
# Navigate to user_service directory
cd user_service

# Run the setup script to create keycloak-secret
./setup-secrets.sh
```

This creates a `keycloak-secret` in the `bb` namespace with:
- `KEYCLOAK_ADMIN_USER`
- `KEYCLOAK_ADMIN_PASS`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET`

**Note:** The `supabase-secret` must already exist in the `bb` namespace with the `SUPABASE_KEY`.

If you need to update the secret values, edit [setup-secrets.sh](setup-secrets.sh) and run it again.

### Initial Deployment

Deploy the service using Helm from the project root:

```bash
helm install user-service ./user_service/k8s -n bb
```

### After Code Changes

When you make changes to the code, follow these steps:

#### 1. Build and Push New Docker Image

```bash
cd user_service
docker buildx build --platform linux/amd64,linux/arm64 -t justingav/user-service:latest --push .
```

#### 2. Update Kubernetes Deployment

```bash
# Option A: Upgrade with Helm
helm upgrade user-service ./user_service/k8s -n bb

# Option B: Restart pods to pull new image
kubectl rollout restart deployment user-service -n bb

# Check rollout status
kubectl rollout status deployment user-service -n bb
```

#### 3. View Logs

```bash
# View logs
kubectl logs -f deployment/user-service -n bb

# View specific pod logs
kubectl get pods -n bb | grep user-service
kubectl logs -f <pod-name> -n bb
```

### Uninstall

```bash
helm uninstall user-service -n bb
```

---

## Testing the Service

### Option 1: Swagger UI (Recommended for Development)

Or if deployed on Kubernetes with ingress:

```
https://user-service.ltu-m7011e-10.se/docs
```

### Option 2: cURL Examples

**Note:** Most endpoints now require JWT authentication. Include the `Authorization: Bearer <token>` header for protected endpoints. See the **Authentication** section above for how to obtain a token.

#### Health Check

```bash
curl -X GET http://user-service.ltu-m7011e-10.se/health
```

#### Get Decoded JWT (Authenticated)

```bash
# Requires valid JWT token
curl -X GET http://user-service.ltu-m7011e-10.se/auth/jwt \
  -H "Authorization: Bearer <your-jwt-token>"
```

#### Create User

```bash
curl -X POST http://user-service.ltu-m7011e-10.se/users \
  -H "Content-Type: application/json" \
  -d '{
    "card_id": 12345,
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "password": "securepassword123"
  }'
```

#### Add Balance

```bash
curl -X POST "http://user-service.ltu-m7011e-10.se/user/add_balance?user_id=test-user&amount=100" \
  -H "Content-Type: application/json" \
  -d '{
    "card_id": 12345,
    "amount": 100
  }'
```

#### Set User Status

```bash
curl -X POST http://user-service.ltu-m7011e-10.se/user/set_status \
  -H "Content-Type: application/json" \
  -d '{
    "user_id_input": "12345",
    "user_status_input": true
  }'
```

#### Fetch User Info

```bash
curl -X POST http://user-service.ltu-m7011e-10.se/user/fetch_info \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 12345
  }'
```

---

## Database Setup

### Table Schema

Create the Users table in your Supabase project:

```sql
create table public."Users" (
  card_id bigint generated by default as identity not null,
  first_name text not null default ''::text,
  balance bigint not null default '0'::bigint,
  active boolean not null default true,
  last_name text not null default ''::text,
  constraint users_pkey primary key (card_id)
) TABLESPACE pg_default;
```

### Required Supabase RPC Functions

The following PostgreSQL functions must be created in your Supabase project. Navigate to **Database > Functions** in your Supabase dashboard.

#### 1. `create_user`

Creates a new user with the provided card ID.

**Parameters:**
- `card_id_input`: bigint
- `first_name_input`: text
- `last_name_input`: text

**Returns:** void

**Function Body:**

```sql
BEGIN
  INSERT INTO public."Users" (card_id, first_name, last_name, balance, active)
  VALUES (card_id_input, first_name_input, last_name_input, 0, TRUE);
END;
```

---

#### 2. `fetch_user_info`

Retrieves user information by card ID.

**Parameters:**
- `user_id_input`: bigint

**Returns:** json

**Function Body:**

```sql
DECLARE
  result json;
BEGIN
  SELECT json_build_object(
    'active', active,
    'first_name', first_name,
    'last_name', last_name,
    'balance', balance
  ) INTO result
  FROM "Users"
  WHERE card_id = user_id_input;

  IF result IS NULL THEN
    RAISE EXCEPTION 'User not found';
  END IF;

  RETURN result;
END;
```

---

#### 3. `user_status`

Updates a user's active status.

**Parameters:**
- `user_id_input`: bigint
- `user_status_input`: boolean

**Returns:** text

**Function Body:**

```sql
DECLARE
  current_status BOOLEAN;
BEGIN
  SELECT active INTO current_status
  FROM "Users"
  WHERE card_id = user_id_input
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'User not found';
  END IF;

  IF current_status = user_status_input THEN
    RAISE EXCEPTION 'User status is already active=%', current_status;
  END IF;

  UPDATE "Users"
  SET active = user_status_input
  WHERE card_id = user_id_input;

  RETURN 'User with id ' || user_id_input || ' has new status active = ' || user_status_input;
END;
```

---

#### 4. `add_balance`

Adds balance to a user's account and records the transaction.

**Parameters:**
- `user_id_input`: bigint
- `balance_input`: bigint

**Returns:** integer (new balance)

**Function Body:**

```sql
DECLARE
  current_balance INT;
  new_balance INT;
BEGIN
  -- Find and Lock the User to prevent race conditions
  SELECT balance INTO current_balance
  FROM "Users"
  WHERE card_id = user_id_input
  FOR UPDATE;

  -- Run Payment Logic Checks
  IF NOT FOUND THEN
    RAISE EXCEPTION 'User not found';
  END IF;

  -- Create the Ledger Record
  INSERT INTO "Transaction_History" (user_id, item, amount_delta)
  VALUES (user_id_input, NULL, +balance_input);

  -- Update the User's Balance
  UPDATE "Users"
  SET balance = current_balance + balance_input
  WHERE card_id = user_id_input
  RETURNING balance INTO new_balance;
  
  -- Return the Result
  RETURN new_balance;
END;
```

---

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install pytest pytest-cov
```

### Run Tests with Coverage (from project root)

```bash
pytest user_service/tests/ --cov=user_service/app --cov-report=html --cov-report=term
```

### Run Specific Test Files

```bash
# Test authentication
pytest user_service/tests/test_auth.py -v

# Test database functions
pytest user_service/tests/test_database.py -v

# Test service endpoints
pytest user_service/tests/test_service.py -v
```

**Note:** Tests use mocked authentication. Authentication is enabled for production endpoints.

---

## Helper Scripts

The service includes several helper scripts for development and testing:

### get_token.py

Requests a JWT token from Keycloak and validates it.

```bash
python get_token.py
```

**Features:**
- Requests token using password grant
- Decodes token payload (unverified)
- Validates token signature using Keycloak's JWKS
- Displays full token information

### test_auth_endpoint.py

Tests the `/auth/jwt` endpoint with a real token.

```bash
python test_auth_endpoint.py
```

**What it does:**
1. Gets a token from Keycloak
2. Makes authenticated request to `/auth/jwt`
3. Displays the decoded JWT payload returned by the service

### setup-secrets.sh

Creates Kubernetes secrets for Keycloak configuration.

```bash
./setup-secrets.sh
```

---

## Troubleshooting

### Self-Signed Certificates

If you're using self-signed certificates in development, set `INSECURE=true`:

```bash
export INSECURE=true
```

This will disable SSL certificate verification. **Never use this in production.**

### Token Validation Errors

If you see "Failed to fetch Keycloak public keys":
1. Check `KEYCLOAK_URL` and `KEYCLOAK_REALM` are correct
2. Verify Keycloak is accessible from your service
3. Check if `INSECURE=true` is needed for self-signed certs

### Common Issues

- **404 on `/realms/{realm}/protocol/openid-connect/certs`**: Wrong Keycloak URL or realm name
- **SSL Certificate Verification Error**: Set `INSECURE=true` for dev with self-signed certs
- **401 Unauthorized**: Token expired or invalid, get a new token
- **503 Service Unavailable**: Cannot reach Keycloak, check network/URL

---

## API Endpoints

### Public Endpoints

- `GET /health` - Health check
- `GET /docs` - OpenAPI documentation

### Authenticated Endpoints

All endpoints below require a valid JWT Bearer token:

- `GET /auth/jwt` - Returns decoded JWT payload
- `POST /users` - Create new user
- `POST /user/add_balance` - Add balance to user account
- `POST /user/set_status` - Update user active status
- `POST /user/fetch_info` - Fetch user information

**Note:** Authentication is currently commented out but should be enabled in production.


### Viewing Kubernetes Resources

```bash
# Check pod status
kubectl get pods -n bb -l app=user-service

# Describe deployment
kubectl describe deployment user-service -n bb

# Check service
kubectl get svc user-service -n bb

# View ingress
kubectl get ingress user-service -n bb

# View secrets
kubectl get secrets -n bb | grep secret
```
