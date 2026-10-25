# ==============================================================================
# HARDENED DOCKERFILE FOR ATHENA LIBRARY WEB APPLICATION (Tiêu chí 6: Hardening)
# - Base: python:3.12-slim (minimal attack surface)
# - Security: Runs as non-root user 'appuser' (UID 10001)
# - Healthcheck: Built-in container health inspection
# ==============================================================================

FROM python:3.12-slim

# Create dedicated non-root system group and user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

# Set environment variables for Python optimization and security
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOG_DIR=/var/log/library

WORKDIR /app

# Install dependencies first (leverage Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create log directory and set permissions
RUN mkdir -p /var/log/library && \
    chown -R appuser:appgroup /var/log/library /app

# Copy application code
COPY . .

# Ensure app directory permissions are restricted to appuser
RUN chown -R appuser:appgroup /app

# Switch to unprivileged user (NON-ROOT ENFORCEMENT)
USER 10001:10001

EXPOSE 5000

# Container Healthcheck
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')" || exit 1

# Start production WSGI server with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
