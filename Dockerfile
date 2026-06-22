# Use full Python image (not slim) to avoid apt issues
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
        libatlas-base-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt /app/requirements.txt

# Install build helpers + Python dependencies
RUN pip install --upgrade pip setuptools wheel meson ninja && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy project files
COPY . /app

# If your FastAPI project lives in a subfolder, adjust WORKDIR accordingly
WORKDIR /app/fastapi-project/project

# Expose port
EXPOSE 80

# Start Uvicorn
CMD ["uvicorn", "readfile:app", "--host", "0.0.0.0", "--port", "80"]
