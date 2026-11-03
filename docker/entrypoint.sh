#!/bin/sh
set -e

python manage.py migrate --noinput

# Cria o usuário administrador na primeira subida, se as variáveis estiverem no .env
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput --email "${DJANGO_SUPERUSER_EMAIL:-admin@exemplo.com}" || echo "(usuário administrador já existe)"
fi

exec gunicorn sistema_urnas.wsgi:application \
  --bind 0.0.0.0:8000 --workers 2 --timeout 60 --access-logfile -
