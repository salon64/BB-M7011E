FROM python:3.11-slim AS builder

WORKDIR /app

# Create and activate a virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies into the virtual environment
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the production image
FROM python:3.11-slim

WORKDIR /app
# Copy the virtual environment from the builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Copy .env file
COPY .env .env

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user and switch to it
RUN useradd --create-home appuser
USER appuser

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8002/health')"


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]