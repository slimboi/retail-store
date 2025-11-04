# Multi-stage build for CloudPros Users Service
# Stage 1: Builder - Install dependencies
FROM python:3.12-alpine AS builder

WORKDIR /build

# Install build dependencies for Python packages (psycopg2, cryptography, etc.)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    openssl-dev \
    cargo \
    rust

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime - Minimal runtime image
FROM python:3.12-alpine

# Install runtime dependencies for PostgreSQL and health checks
RUN apk add --no-cache libpq wget

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser app/ ./app/

# Set PATH to include user site-packages
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8015

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget -qO- http://localhost:8015/health | grep -q ok || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8015"]
