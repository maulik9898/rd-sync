# Stage 1: Build dependencies
FROM python:3.10-slim as builder

# Set working directory
WORKDIR /app

# Install poetry and dependencies
RUN pip install poetry==1.8.2

# Copy only dependency files
COPY poetry.lock pyproject.toml ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Export dependencies to requirements.txt
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# Stage 2: Runtime
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    CONFIG_PATH=/config/config.yaml

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder /app/requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY rd_sync rd_sync/

# Create config and log directories
RUN mkdir -p /config /logs && \
    chown -R nobody:nogroup /config /logs

# Switch to non-root user
USER nobody

# Use tini as entrypoint
ENTRYPOINT ["/usr/bin/tini", "--"]

# Set the default command with config path
CMD ["python", "-m", "rd_sync.main", "--config", "/config/config.yaml"]
