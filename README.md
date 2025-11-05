# CloudPros Web Store

[![CI Pipeline](https://github.com/slimboi/retail-store/actions/workflows/ci.yml/badge.svg)](https://github.com/slimboi/retail-store/actions/workflows/ci.yml)

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

| Service | Version | Image Size | Docker Hub |
|---------|---------|------------|------------|
| **web-ui** | v1.0.0 | 49.7MB | [slimboi/web-ui](https://hub.docker.com/r/slimboi/web-ui) |
| **products** | v1.0.0 | 118MB | [slimboi/products](https://hub.docker.com/r/slimboi/products) |
| **carts** | v1.0.0 | 94.1MB | [slimboi/carts](https://hub.docker.com/r/slimboi/carts) |
| **orders** | v1.0.0 | 91.7MB | [slimboi/orders](https://hub.docker.com/r/slimboi/orders) |
| **users** | v1.0.0 | 142MB | [slimboi/users](https://hub.docker.com/r/slimboi/users) |
| **db** | - | - | PostgreSQL 16 |
| **redis** | - | - | Redis Alpine |

All microservices are built with Alpine Linux base images and multi-stage builds.

## Containerization Features
- Multi-stage builds for minimal image sizes
- Alpine-based images for reduced footprint
- Non-root users for security (Python services run as appuser:1000)
- Health checks built into Dockerfiles
- Proper .dockerignore files to exclude unnecessary files
- Environment-based configuration

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration and delivery:

### Automated Workflows
- **Change Detection**: Only builds services that have changed
- **Quality Gates**:
  - Python linting with Ruff (fast, modern linter)
  - Docker image building
  - Trivy security vulnerability scanning (CRITICAL/HIGH severity)
- **Docker Hub Publishing**: Automatic push to [Docker Hub](https://hub.docker.com/u/slimboi) on main branch
- **GitHub Releases**: Automated release creation with changelogs

### Image Tags
Each service is tagged with:
- `v{version}` - SemVer version from VERSION file
- `latest` - Latest stable release
- `{git-sha}` - Specific commit SHA for traceability

### Manual Workflow Dispatch
Trigger builds manually with custom parameters:
```bash
# Via GitHub UI: Actions → CI Pipeline → Run workflow
# Select service: products, carts, orders, users, web-ui, or all
# Optional: Override version (e.g., 1.2.3)
```

### Version Management
Each service maintains its version in a `VERSION` file following [SemVer](https://semver.org/):
- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality additions
- **PATCH**: Backwards-compatible bug fixes

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