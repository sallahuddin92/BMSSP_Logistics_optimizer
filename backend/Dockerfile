FROM python:3.11-slim

# Install system dependencies (including GDAL for GeoPandas)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    curl \
    libgeos-dev \
    libspatialindex-dev \
    libgdal-dev \
    gdal-bin \
    libproj-dev \
    pybind11-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies (cached if requirements.txt doesn't change)
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create cache directory
RUN mkdir -p /app/cache

# Compile BMSSP C++ extension with proper Python paths
RUN c++ -O3 -Wall -shared -std=c++17 -fPIC \
    $(python3 -m pybind11 --includes) \
    -I$(python3 -c "import sysconfig; print(sysconfig.get_path('include'))") \
    bindings.cpp -o bmssp$(python3-config --extension-suffix)

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV GRAPH_CACHE_DIR=/app/cache

# Start the application
CMD ["python3", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]