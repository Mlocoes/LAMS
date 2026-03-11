# Security Considerations

Security is paramount in LAMS due to its nature as a remote agent monitoring and administration tool.

## Transport Encryption
- **TLS (HTTPS)** is strictly enforced for all APIs. Agents are configured to reject plain HTTP connections.
- In production, it is highly recommended to place LAMS Central Server behind a reverse proxy (e.g., Nginx, Traefik) handling automatic SSL (Let's Encrypt).

## Authentication
- **Agents:** Use a long-lived Bearer Token string provisioned manually or automatically upon registration.
- **Users:** Use short-lived JWT tokens with secure workflows.
- **Passwords:** All user passwords are computationally hashed with **Argon2**, ensuring resistance to brute-force and dictionary attacks.

## Role-Based Access Control (RBAC)
- **Administrators**: Full capabilities. Can approve new agents, modify alerting rules, manage other users, and execute Docker lifecycle actions.
- **Users**: Read-only scope. Can view the web dashboard to see metrics and alerts, but cannot start/stop docker containers or modify users.
