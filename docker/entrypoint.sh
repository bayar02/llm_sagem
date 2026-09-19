#!/bin/bash
set -e

echo "[entrypoint] Démarrage nginx…"
nginx -g "daemon off;" &
NGINX_PID=$!

# Attendre que nginx soit prêt
sleep 1

echo "[entrypoint] Démarrage Streamlit sur 127.0.0.1:8501…"
streamlit run /app/app.py \
    --server.port=8501 \
    --server.address=127.0.0.1 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false &
STREAMLIT_PID=$!

# Arrêt propre si l'un des deux processus meurt
wait -n $NGINX_PID $STREAMLIT_PID
EXIT_CODE=$?
echo "[entrypoint] Processus terminé (code $EXIT_CODE). Arrêt du container."
exit $EXIT_CODE
