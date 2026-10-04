FROM python:3.11-slim

LABEL maintainer="Kumari Simran <simran846@users.noreply.github.com>"
LABEL project="TurbineGuard"
LABEL description="Wind Turbine Controller Validation & Automated Test Platform"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications and install
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code, dashboard, scripts, and documentation
COPY src/ ./src/
COPY dashboard/ ./dashboard/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY docs/ ./docs/

# Install package in editable mode
RUN pip install --no-cache-dir -e .

# Create reports and data directories
RUN mkdir -p /app/reports /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "turbineguard.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
