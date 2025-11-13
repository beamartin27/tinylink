# ---- runtime base ----
FROM python:3.12-slim

# Avoid buffering, install pip faster
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Workdir
WORKDIR /app

# System deps (optional but good practice: tzdata for correct time)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    tzdata && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency file(s) first (better layer caching)
COPY requirements.txt /app/requirements.txt

# Install Python deps
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app /app/app
COPY README.md /app/README.md

# Expose port for uvicorn
EXPOSE 8000

# Run as non-root for security
RUN useradd -m appuser
USER appuser

# Default envs (overridable at docker run)
# BASE_URL is optional; set it only when tunneling/public domain is known.
# CMD runs the API server.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
