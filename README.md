# CloudPros Web Store

Minimal store composed of services: products (SQLite, seeded from FakeStore), carts (Redis),
orders (checkout + cart clear), users (PostgreSQL with JWT auth), and a static web UI proxied via Nginx.

## Quick Start
```bash
# Copy environment file
cp .env.example .env

# Build and start all services
docker compose up --build -d

# Open the application
open http://localhost:8080
```

## Services Architecture
- **web-ui** - Static frontend + Nginx reverse proxy (Alpine, 49.7MB)
- **products** - Product catalog API with SQLite (Alpine, 118MB)
- **carts** - Shopping cart API with Redis (Alpine, 94.1MB)
- **orders** - Order processing and checkout API (Alpine, 91.7MB)
- **users** - User authentication API with PostgreSQL (Alpine, 142MB)
- **db** - PostgreSQL database
- **redis** - Redis cache

## Containerization Features
- Multi-stage builds for minimal image sizes
- Alpine-based images for reduced footprint
- Non-root users for security (Python services run as appuser:1000)
- Health checks built into Dockerfiles
- Proper .dockerignore files to exclude unnecessary files
- Environment-based configuration

## Notes
- First start will fetch products from https://fakestoreapi.com/ and cache them locally (SQLite).
- Cart is stored in Redis, keyed by `userId` (guest or auth user id).
- Sign in / Sign up are local only; JWT token stored in localStorage.
- To reset (and reseed), run: `docker compose down -v` and then `docker compose up --build -d`.

## Orchestration, Health and Evidence

-The aim is to set up the final orchestration layer, ensure stack reproducibility, and confirm all services connect successfully and are reachable through the reverse proxy.

#### Scope
- To create a `docker-compose.yml` file with the below services
  - ###### Services
    - web-ui - also acting as a reverse-proxy
    - products
    - orders
    - carts
    - users 
    - db
    - redis
- Show understanding of `depends_on` and and `healthcheck` conditions 
and apply them properly.
- Add `env.example` file containing all required variables.
- Test the final product end-to-end.

#### Reverse-proxy used for the project and differences
- Nginx -> `docker-compose.yml`
- Traefik -> `docker-compose.traefik.yml`

#### What reverse-proxy does 

| Role             |    Brief description                              |
|------------------|---------------------------------------------------|
| Load balancing   | Distributes traffic across containers             |
| Security         | It hides the internal IP address                  |
| Caching          | Caches static files or responses to boost speed   |
| Compression      | Compress responses before sending them. `Traefik` |
| Request routing  | It routes paths or domains to different services  |

#### Acceptance:
- docker compose config result
![docker-compose-config](./images/docker-compose-config.png)

- docker compose up --build -d result 
![docker-compose-up](./images/docker-compose-up.png)

![health-status](./images/health-status.png)
I have added the health checks as part of the image. So no need for redundant healthchecks in the docker compose yml.

| Service  | Image                                    | Size    |
|----------|------------------------------------------|---------|
| web-ui   | retail-store-web-ui:latest               | 49.7MB  |
| products | retail-store-products:latest             | 118MB   |
| orders   | retail-store-orders:latest               | 91.7MB  |
| carts    | retail-store-carts:latest                | 94.1MB  |
| users    | retail-store-users:latest                | 142MB   |

**Note**: All services use Alpine Linux-based images with multi-stage builds for optimal size and security.

#### Tested the set-up using the below commands 

```bash
# Shows we can access the web-ui container 
curl -i http://localhost:8080

# Shows we can access the orders container via reverse proxy
curl -i http://localhost:8080/api/orders/health

# Shows we can access the carts container via reverse proxy
curl -i http://localhost:8080/api/carts/health

# Shows we can access the products container via reverse proxy
curl -i http://localhost:8080/api/products/health

# Shows I can retrieve the products list
curl -i http://localhost:8080/api/products/products

# Shows we can access the users container via reverse proxy
curl -i http://localhost:8080/api/users/health
```