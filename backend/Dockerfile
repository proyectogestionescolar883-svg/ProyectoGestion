FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=proyecto.settings

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN addgroup --system app \
    && adduser --system --ingroup app --no-create-home app \
    && mkdir -p /app/media /app/staticfiles \
    && DJANGO_SECRET_KEY=build-placeholder DB_PASSWORD=build-placeholder python manage.py collectstatic --noinput \
    && chown -R app:app /app/media /app/staticfiles

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import socket; socket.create_connection(('127.0.0.1', 8000), 3).close()"]

CMD ["gunicorn", "proyecto.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
