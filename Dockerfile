FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set the correct app directory
WORKDIR /app/fastapi-project/project

EXPOSE 80

CMD ["uvicorn", "readfile:app", "--host", "0.0.0.0", "--port", "80"]