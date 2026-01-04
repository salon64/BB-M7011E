# Payment Service

This is a FastAPI-based microservice responsible for handling all payment transactions within the Bättre Bosh ecosystem. It provides a secure and robust endpoint for debiting user accounts.

[![Coverage](https://codecov.io/gh/salon64/BB-M7011E/branch/feat%2Fpayment-service/graph/badge.svg)](https://codecov.io/gh/salon64/BB-M7011E)
[![Tests](https://github.com/salon64/BB-M7011E/workflows/Payment%20Service%20CI/badge.svg)](https://github.com/salon64/BB-M7011E/actions)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)

## Overview

The primary purpose of this service is to expose an API for processing payments. It communicates with a Supabase (PostgreSQL) database via an RPC (Remote Procedure Call) function to ensure that transactions are atomic and that business logic is handled securely at the database level.

### Key Technologies

*   **Framework**: FastAPI
*   **Language**: Python 3.11
*   **Database**: Supabase (PostgreSQL)
*   **Containerization**: Docker
*   **Testing**: Pytest

---

## Getting Started

### Prerequisites

*   Python 3.11
*   Docker
*   A Supabase project (see **Database setup** for structure)

### Configuration

The service requires a `.env` file in the root directory with the following variables:

```
SUPABASE_URL="your_supabase_project_url"
SUPABASE_KEY="your_supabase_service_role_key"
PRODUCTS_SERVICE_URL="http://localhost:8001"
```

### Database setup

1. **Supabase RPC function:**
This will walk you through creating the database function that deducts balance from a user as part of a transaction and logs the transaction in the approriate table.

    - Navigate to _Database > Functions_ within your supabase project
    - Press "Create a new function"
    - **Function:**
        - Name: `debit_use`
        - Schema: public
        - Args: [user_id_input: integer], [item_id: uuid]
        - Definition:
            ```plpgsql
            DECLARE
                current_balance INT;
                user_active BOOL;
                new_balance INT;
                item_price INT;
            BEGIN
            -- Find and Lock the User to prevent all race conditions.

            SELECT
                balance,
                active
            INTO
                current_balance,
                user_active
            FROM "Users"
            WHERE card_id = user_id_input
            FOR UPDATE;

            SELECT
                price
            INTO
                item_price
            FROM "Items"
            WHERE id = item_input
            FOR UPDATE;

            -- Run Payment Logic Checks
            IF NOT FOUND THEN
                RAISE EXCEPTION 'User not found';
            END IF;

            IF user_active = FALSE THEN
                RAISE EXCEPTION 'User is not active';
            END IF;

            IF current_balance < item_price THEN
                RAISE EXCEPTION 'Insufficient funds. Has: %, Needs: %', current_balance, amount_input;
            END IF;

            -- Create the Ledger Record
            INSERT INTO "Transaction_History"
                (user_id, item, amount_delta)
            VALUES
                (user_id_input, item_input, -item_price);

            -- Update the User's Balance
            UPDATE "Users"
            SET balance = current_balance - item_price
            WHERE card_id = user_id_input
            RETURNING balance INTO new_balance;
            
            -- Return the Result
            RETURN new_balance;
            END;
            ```
2. **Tables:**
For this information adhere to the README.md present in the database directory of the project.

---

### Running with Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t payment_service .
    ```

2.  **Run the container:**
    ```bash
    docker run -p 8002:8002 --env-file .env payment_service
    ```

---

### Running Kubernetes k8s

1. Build the docker image with the appropriate sys architecture and Push the image to the specified Docker Hub account:
    ```bash
    docker buildx build --platform linux/amd64,linux/arm64 -t justingav/payment-service:latest --push . 
    ```
2. Navigate to the k8s directory and run the following command to reload the deployment file:
    ```bash
    kubectl apply -f deployment.yaml
    ```
3. You can now view it at: ```http://localhost:8002```
4. Clean up afterwards: 
    ```bash
    kubectl delete -f deployment.yaml && kubectl apply -f deployment.yaml
    ```
### HPA 

Check HPA status:
```bash
# Check HPA across all namespaces
kubectl get hpa --all-namespaces

# Detailed HPA information
kubectl describe hpa payment-service-dev-hpa -n payment-service-dev

# Monitor real-time scaling
kubectl get hpa -n payment-service-dev -w
```
Resource usage monitoring:
```bash
# Check current CPU/memory usage
kubectl top pods -n payment-service-dev

# View pod resource requests/limits
kubectl describe deployment payment-service-dev -n payment-service-dev
```

---

### Testing endpoints and error handling

1. Run the following command `pytest tests/test_service.py -v` to run the test suite
2. If all goes well, all tests should pass.

**If you want to run tests and see the coverage report for these tests**

1. Run the following commands:
    ```bash
    cd payment_service
    pytest tests/ --cov=app --cov-report=html --cov-report=term
    ```
    or for a more detailed reporting,
    ```bash
    pytest tests/ --cov=app --cov=main --cov-report=html --cov-report=term-missing
    ```

---

### Using the service locally in the web browser

1. Go to the following web adress: http://localhost:8002/docs#/default/debit_payment_payments_debit_post

---

## Troubleshooting Guide

This guide is based on common issues encountered during the development of this service.

### 1. Error: "User not found"

*   **Cause 1**: The `user_id` you are sending in your API request does not exist in the `public.User` table. This often happens when using a placeholder ID like `"1"` instead of a real user's id.
*   **Cause 2**: The API key to the Supabase database doesn't have the required access level to perform this operation.
*   **Solution**: You can create test users in the database with simple ids. Use the proper API key, that is a API key of type `service_role`, as this provides greater access.

### 2. Error: Pydantic `Field required` error on startup

*   **Cause**: The application is missing one or more required environment variables when it starts.
*   **Solution**: Check your `.env` file and ensure all variables defined in `app/config.py` (like `SUPABASE_URL`, `SUPABASE_KEY`, `PRODUCTS_SERVICE_URL`) are present and correctly spelled.

### 3. Error: SupabaseException: Invalid URL

*   **Cause**: The Supabase client creation is done before any environment variables have been properly loaded.
*   **Solution**: In the database file, check if the Supabase client is none. If the client object is none, create it adding the urls from the `.env` file. Make the reading of the `.env` file case insensitive. Make sure the path to the env file is properly copied in the Dockerfile.

### 4. Error: Kubernetes pod: no match for platform in manifest: not found

*   **Cause**: The message "no match for platform in manifest: not found" means the Docker image was built for a different CPU architecture than the node it's trying to run on.
*   **Solution**: Rebuild and push the Docker image to include manifests for both architectures using the command:
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t <justingav/payment-service:latest> --push .
```