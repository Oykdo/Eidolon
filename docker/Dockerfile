# =============================================================================
# Eidolon - Production Dockerfile
# =============================================================================

# Stage 1: Build
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.11-slim

LABEL maintainer="Poly-Spinor Team <contact@polyspinor.io>"
LABEL version="1.0.0"
LABEL description="Eidolon Vault System"

# Create non-root user
RUN groupadd -r vault && useradd -r -g vault vault

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 \
    libssl3 \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy application code
COPY --chown=vault:vault core/ ./core/
COPY --chown=vault:vault protocols/ ./protocols/
COPY --chown=vault:vault ui/ ./ui/
COPY --chown=vault:vault utils/ ./utils/
COPY --chown=vault:vault config/ ./config/
COPY --chown=vault:vault scripts/ ./scripts/
COPY --chown=vault:vault vault_storage/ ./vault_storage/
COPY --chown=vault:vault *.py ./

# Create necessary directories
RUN mkdir -p vault_storage/persistent vault_storage/documents vault_storage/keys vault_storage/logs vault_storage/backups \
    && chown -R vault:vault vault_storage

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV VAULT_ENV=production

# Switch to non-root user
USER vault

# Expose ports
EXPOSE 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Use tini as init system
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command
CMD ["python", "scripts/vault_launcher.py", "daemon", "--vault", "main_vault", "--interval", "60"]
