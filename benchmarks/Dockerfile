FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy benchmark scripts
COPY . .

# Create results directory
RUN mkdir -p /app/results

# Create non-root user
RUN useradd --create-home --shell /bin/bash benchmarks && \
    chown -R benchmarks:benchmarks /app
USER benchmarks

# Default command runs all benchmarks
CMD ["python", "run_all_benchmarks.py"]
