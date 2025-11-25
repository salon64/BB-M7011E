# Payment Service

This is a FastAPI-based microservice responsible for handling all payment transactions within the Bättre Bosh ecosystem. It provides a secure and robust endpoint for debiting user accounts.

## Overview

The primary purpose of this service is to expose an API for processing payments. It communicates with a Supabase (PostgreSQL) database via an RPC (Remote Procedure Call) function to ensure that transactions are atomic and that business logic is handled securely at the database level.

### Key Technologies

*   **Framework**: FastAPI
*   **Language**: Python 3.11
*   **Database**: Supabase (PostgreSQL)
*   **Containerization**: Docker

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
        - Args: [user_id_input: text], [amount_input: integer], [correlation_id_input: uuid]
        - Definition:
            ```plpgsql
            DECLARE
            current_balance INT;
            user_active INT;
            new_balance INT;
            BEGIN
            -- Find and Lock the User to prevent all race conditions.

            SELECT
                balance,
                active
            INTO
                current_balance,
                user_active
            FROM "User"
            WHERE id = user_id_input
            FOR UPDATE;

            -- Run Payment Logic Checks
            IF NOT FOUND THEN
                RAISE EXCEPTION 'User not found';
            END IF;

            IF user_active = 0 THEN
                RAISE EXCEPTION 'User is not active';
            END IF;

            IF current_balance < amount_input THEN
                RAISE EXCEPTION 'Insufficient funds. Has: %, Needs: %', current_balance, amount_input;
            END IF;

            -- Create the Ledger Record
            INSERT INTO "Transactions"
                (user_id, amount_delta, type, correlation_id)
            VALUES
                (user_id_input, -amount_input, 'PURCHASE', correlation_id_input);

            -- Update the User's Balance
            UPDATE "User"
            SET balance = current_balance - amount_input
            WHERE id = user_id_input
            RETURNING balance INTO new_balance;
            
            -- Return the Result
            RETURN new_balance;
            END`
            ```
2. **Tables:**
For this information adhere to the README.md present in the database directory of the project.

### Running with Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t payment-service .
    ```

2.  **Run the container:**
    ```bash
    docker run -p 8002:8002 --env-file .env payment-service
    ```

---

## Troubleshooting Guide

This guide is based on common issues encountered during the development of this service.

### 1. Error: "User not found"

*   **Cause 1**: The `user_id` you are sending in your API request does not exist in the `public.User` table. This often happens when using a placeholder ID like `"1"` instead of a real user's id.
*   **Cause 2**: The API key to the Supabase database doesn't have the required access level to perform this operation.
*   **Solution**: You can create test users in the database with simple ids. Use the proper API key, that is a API key of type `service_role`, as this provides greater access.

### 4. Error: Pydantic `Field required` error on startup

*   **Cause**: The application is missing one or more required environment variables when it starts.
*   **Solution**: Check your `.env` file and ensure all variables defined in `app/config.py` (like `SUPABASE_URL`, `SUPABASE_KEY`, `PRODUCTS_SERVICE_URL`) are present and correctly spelled.
