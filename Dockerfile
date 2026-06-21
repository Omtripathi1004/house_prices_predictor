FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    gfortran \
    libatlas-base-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

WORKDIR /app/fastapi-project/project

EXPOSE 80

CMD ["uvicorn", "readfile:app", "--host", "0.0.0.0", "--port", "80"]
