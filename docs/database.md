# Database Schema

LAMS relies on PostgreSQL for robust storage. Below are the core tables designed to store configuration, timeseries metrics, and state.

## Core Tables

### `users`
- `id` (UUID, Primary Key)
- `email` (String, Unique)
- `password_hash` (String, hashed with Argon2)
- `role` (String: `ADMIN`, `USER`)
- `created_at` (Timestamp)

### `hosts`
- `id` (String, Primary Key)
- `hostname` (String)
- `ip` (String)
- `os` (String)
- `kernel_version` (String)
- `cpu_cores` (Int)
- `memory_total` (BigInt)
- `tags` (JSONB)
- `last_seen` (Timestamp)
- `status` (String: `ONLINE`, `OFFLINE`)

### `metrics` (Time-series)
- `id` (UUID, Primary Key)
- `host_id` (String, Foreign Key -> `hosts.id`)
- `timestamp` (Timestamp with Time Zone, Indexed)
- `cpu_usage` (Float)
- `memory_used` (Float)
- `disk_used` (Float)
- `temperature_cpu` (Float)
- `network_rx` (BigInt)
- `network_tx` (BigInt)

*(Indexes should be placed on `host_id` and `timestamp`)*

### `alerts`
- `id` (UUID, Primary Key)
- `host_id` (String, Foreign Key -> `hosts.id`)
- `rule_name` (String)
- `severity` (String: `WARNING`, `CRITICAL`)
- `metric_name` (String)
- `metric_value` (Float)
- `status` (String: `ACTIVE`, `RESOLVED`)
- `created_at` (Timestamp)
- `resolved_at` (Timestamp, Nullable)

### `docker_containers`
- `id` (String, Container ID, Primary Key)
- `host_id` (String, Foreign Key -> `hosts.id`)
- `name` (String)
- `image` (String)
- `state` (String)
- `status_text` (String)
