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
*   A Supabase project with the required database functions and tables.

### Configuration

The service requires a `.env` file in the root directory with the following variables:

```
SUPABASE_URL="your_supabase_project_url"
SUPABASE_KEY="your_supabase_service_role_key"
PRODUCTS_SERVICE_URL="http://localhost:8001"
```

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
