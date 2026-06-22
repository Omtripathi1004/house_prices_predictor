# Python base image
FROM python:3.11

# Environment settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        gfortran \
        libopenblas-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade \
        pip \
        setuptools \
        wheel \
        meson \
        ninja && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Change this path if your FastAPI app is elsewhere
WORKDIR /app/fastapi-project/project

# Expose FastAPI port
EXPOSE 80

# Start FastAPI
CMD ["uvicorn", "readfile:app", "--host", "0.0.0.0", "--port", "80"]