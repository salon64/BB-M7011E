# Motivation: Why is This a Dynamic Web System?

- The system provides real-time, user-specific content and updates (e.g., balances, transaction history).
- User interactions (buying, logging in/out) immediately affect the data and UI for all users (e.g., balance updates, transaction records).
- Authentication and authorization are dynamic, adapting to user roles and session state.
- The backend is composed of microservices that communicate and update each other dynamically.
- Social network bots (Discord and Telegram) allow users to interact with the system in real time from multiple platforms, making the system even more dynamic and accessible.

---

# High-Level Architecture

## Microservices Overview

```mermaid
flowchart LR
    subgraph User
        A[Web Client]
        B["Card Reader (TODO)"]
        I["Discord (TODO)"]
        J["Telegram (TODO)"]
    end
    subgraph Backend
        C["User Service"]
        D["Payment Service"]
        E["Item Service"]
        F["Keycloak (Auth)"]
        G["Discord Bot (TODO)"]
        H["Supabase/DB"]
        K["Telegram Bot (TODO)"]
    end
    A -- REST/HTTPS --> C
    A -- REST/HTTPS --> D
    A -- REST/HTTPS --> E
    B -- REST/HTTPS --> C
    I -- API --> G
    J -- API --> K
    G -- REST/HTTPS --> C
    G -- REST/HTTPS --> D
    G -- REST/HTTPS --> E
    K -- REST/HTTPS --> C
    K -- REST/HTTPS --> D
    K -- REST/HTTPS --> E
    C -- gRPC/REST --> F
    D -- gRPC/REST --> F
    E -- gRPC/REST --> F
    C -- SQL/REST --> H
    D -- SQL/REST --> H
    E -- SQL/REST --> H
    A -- OIDC --> F
```

---

## GitOps CI/CD Pipeline

```mermaid
flowchart TD
    Dev[Developer Push/PR] --> CI[CI: Test, Lint, Build]
    CI --> Docker["Build & Push Docker Images (this is done in GitHub Actions/cicd)"]
    Docker --> ArgoCD[ArgoCD Watches Repo, Deploys Changes]
    ArgoCD --> K8s[Kubernetes Cluster]
```

---

## Security Model & Secure Request Flow

```mermaid
sequenceDiagram
    participant User
    participant Keycloak
    participant API
    participant DB

    User->>Keycloak: Login (username/password or card)
    Keycloak-->>User: JWT Token
    User->>API: Request with JWT (Authorization: Bearer)
    API->>Keycloak: Validate JWT (JWKS)
    API->>DB: Query/Update (if authorized)
    API-->>User: Data/Confirmation
```

- All service-to-service and user-to-service communication is over HTTPS.
- JWT tokens are validated using Keycloak’s JWKS endpoint.
- Role-based access control enforced in each microservice.

---

## Monitoring, Metrics, Logs, Traces

todo? do we have this yet?

---

# Database Schemas

> _Insert graphical ER diagrams or schema diagrams here. You can generate these using tools like dbdiagram.io, SQLDBM, or from your ORM/database migration files._

**Example:**

```mermaid
erDiagram
    USERS {
        int id PK
        string first_name
        string last_name
        bool active
        int balance
    }
    KEYCLOAK_USERS {
        string id PK
        string username
        string email
        string role
        string first_name
        string last_name
    }
    EXPEL_USERS {
        string id PK
        string first_name
        string last_name
        string card_id
        datetime membership_expires
    }
    TRANSACTIONS {
        int id PK
        int user_id FK
        int item_id FK
        datetime timestamp
    }
    ITEMS {
        int id PK
        string name
        bool active
        int price
        int barcode_id
    }
    USERS ||--o{ TRANSACTIONS : makes
    ITEMS ||--o{ TRANSACTIONS : involved_in
    USERS ||--|| KEYCLOAK_USERS : "auth (external)"
    USERS ||--|| EXPEL_USERS : "xp-el (external)"
    %% External table styling workaround: use dashed border and gray fill
    style KEYCLOAK_USERS fill:#e0e0e0,stroke:#666,stroke-width:2,stroke-dasharray: 5 5
    style EXPEL_USERS fill:#e0e0e0,stroke:#666,stroke-width:2,stroke-dasharray: 5 5
```


![schema in suppabase](image.png)
---

_Fill in each section with your system’s specifics and generated diagrams as needed._
