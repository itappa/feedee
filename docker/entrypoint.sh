#!/bin/sh
set -e

echo "Preparing static files directory..."
mkdir -p /app/staticfiles

if [ ! -w /app/staticfiles ]; then
    echo "Error: /app/staticfiles is not writable"
    ls -ld /app /app/staticfiles || true
    exit 1
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120
