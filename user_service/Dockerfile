FROM python:3.11-slim AS builder

WORKDIR /app

ENV PATH="/home/appuser/venv/bin:$PATH"

# Install curl and wget for debugging (as root)
RUN apt-get update && apt-get install -y curl wget && rm -rf /var/lib/apt/lists/*

# Create a non-root user and switch to it
RUN useradd --create-home appuser
USER appuser

# Create and activate a virtual environment in a user-writable location
ENV VIRTUAL_ENV=/home/appuser/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies into the virtual environment
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the production image
FROM python:3.11-slim

WORKDIR /app
# Copy the virtual environment from the builder
COPY --from=builder /home/appuser/venv /home/appuser/venv

# Copy application code
COPY . .


# Install curl and wget for debugging (as root)
USER root
RUN apt-get update && apt-get install -y curl wget && rm -rf /var/lib/apt/lists/*

ENV PATH="/home/appuser/venv/bin:$PATH"

# Create a non-root user and switch to it
RUN useradd --create-home appuser
USER appuser

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8004/health')"


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]