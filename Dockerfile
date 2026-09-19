# ─────────────────────────────────────────────────────────────
#  ICP to MTP Analysis and Reporting Tool
#  Dockerfile — Nginx (SSL, port 443) + Streamlit (port 8501)
# ─────────────────────────────────────────────────────────────

FROM python:3.11-slim

LABEL maintainer="Sagemcom"
LABEL description="ICP to MTP Analysis and Reporting Tool"
LABEL version="2.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=127.0.0.1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# ── Dépendances système ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    openssl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── Certificat SSL auto-signé (généré à la construction) ────
# Pour la production, montez vos vrais certificats via volume :
#   -v /path/to/cert.pem:/etc/nginx/ssl/cert.pem
#   -v /path/to/key.pem:/etc/nginx/ssl/key.pem
RUN mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
      -keyout /etc/nginx/ssl/key.pem \
      -out    /etc/nginx/ssl/cert.pem \
      -subj "/C=FR/ST=IDF/L=Paris/O=Sagemcom/CN=icp-mtp-tool"

# ── Configuration nginx ──────────────────────────────────────
COPY docker/nginx.conf /etc/nginx/nginx.conf

# ── Application Python ───────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# ── Volumes ──────────────────────────────────────────────────
VOLUME ["/app/telecom_config.json"]

# ── Port exposé : HTTPS 443 interne au container ────────────
EXPOSE 443

# ── Healthcheck ──────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,ssl; \
        ctx=ssl.create_default_context(); \
        ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE; \
        urllib.request.urlopen('https://localhost/', context=ctx)" || exit 1

# ── Entrypoint : démarre nginx + streamlit ───────────────────
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
