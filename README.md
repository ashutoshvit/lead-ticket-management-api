# Lead, ticket, and product management API

A small FastAPI service for managing sales leads, support tickets associated with leads, and products. PostgreSQL stores the source of truth, Redis caches product list reads, and a PostgreSQL outbox reliably queues domain events for Kafka publication.

## Start the stack

```bash
cp .env.example .env
docker compose up --build
```

On Windows PowerShell, use `Copy-Item .env.example .env` in place of `cp` if needed. The API starts at <http://localhost:8000>; interactive OpenAPI docs are at <http://localhost:8000/docs>.

The first startup creates database tables automatically. PostgreSQL data persists in the `postgres_data` Docker volume.

## API overview

All resources are under `/api/v1` and support pagination with `limit` and `offset`.

| Resource | Routes |
| --- | --- |
| Products | `GET/POST /products`, `GET/PATCH/DELETE /products/{id}` |
| Leads | `GET/POST /leads`, `GET/PATCH/DELETE /leads/{id}` |
| Tickets | `GET/POST /tickets`, `GET/PATCH/DELETE /tickets/{id}` |

Filter products and leads with `?status=...`. Filter tickets with `?status=...` and/or `?lead_id=...`. Tickets must belong to a lead and may reference a product. Lead email and product SKU are unique. Deletes return HTTP 204; duplicate emails/SKUs return HTTP 409.

### Example flow

Create a product:

```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Analytics Suite","sku":"ANALYTICS-01","price":"49.00"}'
```

Create a lead:

```bash
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Asha","last_name":"Rao","email":"asha@example.com","company":"Example Ltd"}'
```

Create a ticket using the returned IDs:

```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{"lead_id":1,"product_id":1,"subject":"Need a product demo","priority":"high"}'
```

## Events and infrastructure

Lead, ticket, and product create/update/delete operations write an event in the same PostgreSQL transaction as the record change. A background worker publishes pending outbox rows to the `lead-management.events` Kafka topic and marks them published only after broker acknowledgement. Failed deliveries remain queued and are retried. Consumers should be idempotent because a process crash after Kafka acknowledges but before the outbox update can deliver an event more than once.

Redis caches product list responses for `CACHE_TTL_SECONDS`; product writes clear the list cache. Redis outages fall back to PostgreSQL reads. `GET /health/live` reports process liveness; `GET /health/ready` checks database connectivity. The Kafka outbox worker retries broker failures independently.

## Configuration

Set values in `.env`; see `.env.example`. Compose supplies hostnames for service-to-service connections. For a locally installed API, use `localhost` in the connection URLs.

## Production notes

This starter creates tables on startup for a quick local setup. Use Alembic migrations, authentication/authorization, stricter operational monitoring, and managed credentials before production deployment. The included Kafka and Zookeeper setup is for local development.

