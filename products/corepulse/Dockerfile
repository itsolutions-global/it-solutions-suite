# ==============================================================================
# IT Solutions Global Corporation — CorePulse Enterprise Production Image
# Multi-arch lightweight container (Linux amd64/arm64)
# 100% Python Standard Library. Zero external runtime dependencies.
# ==============================================================================

FROM python:3.12-alpine

LABEL org.opencontainers.image.title="CorePulse Enterprise Cockpit" \
      org.opencontainers.image.description="Autonomous Executive Cockpit & Life OS Engine" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="IT Solutions Global Corporation" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.authors="engineering@itsolutions.corp"

# Security: Create non-root system user & group
RUN addgroup -S isgc && adduser -S isgc -G isgc

WORKDIR /app

# Copy application files
COPY --chown=isgc:isgc main.py ./
COPY --chown=isgc:isgc companion.py ./
COPY --chown=isgc:isgc omnibar.py ./
COPY --chown=isgc:isgc README.md ./
COPY --chown=isgc:isgc corepulse/ ./corepulse/

# Create persistent data directory with appropriate ownership
RUN mkdir -p /app/data && chown -R isgc:isgc /app/data

# Switch to unprivileged user
USER isgc

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    COREPULSE_HOST=0.0.0.0 \
    COREPULSE_PORT=8080 \
    COREPULSE_DEBUG=False

VOLUME ["/app/data"]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health')" || exit 1

ENTRYPOINT ["python", "-u", "main.py"]
