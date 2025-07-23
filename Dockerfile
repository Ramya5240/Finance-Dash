FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for build and PostgreSQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY project_requirements.txt requirements.txt

# Upgrade pip tools and install Python dependencies in one step
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create Streamlit config directory and config file
RUN mkdir -p ~/.streamlit \
    && echo "[server]\nheadless = true\nport = 5000\nenableCORS = false\n" > ~/.streamlit/config.toml

# Expose Streamlit port
EXPOSE 5000

# Optional health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/_stcore/health || exit 1

# Run the Streamlit app
CMD ["streamlit", "run", "main.py", "--server.port=5000", "--server.address=0.0.0.0"]

