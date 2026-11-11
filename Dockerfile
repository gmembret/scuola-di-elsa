FROM python:3.13-slim
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CACHE_DIR=/tmp/elsa TZ=Europe/Berlin

# Copia tutto il repository e ricostruisce la cartella app/ anche se su GitHub
# i file sono finiti tutti allo stesso livello (succede con "Upload files").
COPY . /tmp/src
RUN set -e; cd /tmp/src; \
    pip install --no-cache-dir -r requirements.txt; \
    if [ -f app/server.py ]; then \
        cp -r app /srv/app; \
    else \
        mkdir -p /srv/app/static; \
        for f in __init__.py portal.py server.py translate.py topics.py demo.py; do \
            if [ -f "$f" ]; then cp "$f" /srv/app/; fi; \
        done; \
        for f in index.html app.js styles.css sw.js manifest.webmanifest icon.svg icon-192.png icon-512.png; do \
            if [ -f "$f" ]; then cp "$f" /srv/app/static/; fi; \
        done; \
        if [ -d static ]; then cp -r static/. /srv/app/static/; fi; \
        touch /srv/app/__init__.py; \
    fi; \
    for f in server.py portal.py translate.py topics.py demo.py; do \
        if [ ! -f "/srv/app/$f" ]; then echo "ERRORE: nel repository GitHub manca il file $f (cartella app)"; exit 1; fi; \
    done; \
    for f in index.html app.js styles.css; do \
        if [ ! -f "/srv/app/static/$f" ]; then echo "ERRORE: nel repository GitHub manca il file $f (cartella app/static)"; exit 1; fi; \
    done; \
    rm -rf /tmp/src

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
