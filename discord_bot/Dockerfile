FROM python:3.11-slim

WORKDIR /app

# Copy and install common package first
COPY common/ ./common/
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir ./common


# Install dependencies
COPY discord_bot/app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Remove setuptools after build (contains vulnerable vendored jaraco.context)
# setuptools is only needed for building wheels, not at runtime
RUN pip uninstall -y setuptools

# Copy application
COPY discord_bot/app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run application
CMD ["python", "-m", "app.main"]
