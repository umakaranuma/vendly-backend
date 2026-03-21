FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# mysqlclient build/runtime deps + default-mysql-client requested by deployment.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-mysql-client \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "gunicorn vendly_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
