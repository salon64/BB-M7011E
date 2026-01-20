FROM python:3.11-slim AS builder

WORKDIR /app

# Create and activate a virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy and install common package first
COPY common /app/common
RUN rm -rf /app/common/bb_common.egg-info && pip install --no-cache-dir /app/common

# Install dependencies into the virtual environment
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the production image
FROM python:3.11-slim

WORKDIR /app
# Copy the virtual environment from the builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY frontend/ .

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user and switch to it
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
