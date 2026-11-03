# Backend (Django + gunicorn). O site React é servido pelo nginx (ver frontend/Dockerfile).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py ./
COPY sistema_urnas ./sistema_urnas
COPY api ./api
COPY docker/entrypoint.sh /entrypoint.sh

# /dados guarda o banco (volume); collectstatic prepara o CSS do /admin/
RUN useradd --create-home app \
 && mkdir /dados && chown app /dados \
 && sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh \
 && DJANGO_SECRET_KEY=so-para-o-build python manage.py collectstatic --noinput

ENV DJANGO_DB_PATH=/dados/db.sqlite3
USER app
VOLUME /dados
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
