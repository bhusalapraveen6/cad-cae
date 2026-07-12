FROM python:3.11-slim

LABEL description="CAD-CAE FastAPI + Celery backend"

# System dependencies
RUN apt-get update && apt-get install -y \
    # Build tools
    gcc g++ make cmake \
    # CAD / mesh libraries
    libgl1-mesa-glx libglu1-mesa libxrender1 libxi6 libsm6 libxext6 \
    # gmsh dependencies
    libgmp-dev libmpfr-dev \
    # OpenCASCADE (pythonocc-core)
    libocct-data-exchange-dev \
    libocct-visualization-dev \
    # Misc
    wget curl git \
    && rm -rf /var/lib/apt/lists/*

# Try to install gmsh binary for subprocess fallback
RUN apt-get update && apt-get install -y gmsh && rm -rf /var/lib/apt/lists/* 2>/dev/null || true

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p /app/storage/uploads /app/storage/jobs /app/storage/results

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
