#!/bin/bash
# PickleSphere - Start Django dev server with SMTP email support
# Usage: ./run_server.sh [--ngrok] [--port=PORT]
# Examples:
#   ./run_server.sh              - Start Django on :8000
#   ./run_server.sh --ngrok       - Start Django on :8000 + ngrok tunnel
#   ./run_server.sh --port=8080   - Start Django on :8080
#   ./run_server.sh --ngrok --port=8080 - Start Django on :8080 + ngrok tunnel
#
# SECURITY: Email credentials are read from your .env file (never hardcoded here).
# Copy .env.example to .env and fill in EMAIL_HOST_USER / EMAIL_HOST_PASSWORD.

PORT=8000
USE_NGROK=false

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --ngrok)
            USE_NGROK=true
            ;;
        --port=*)
            PORT="${arg#*=}"
            ;;
    esac
done

# Load credentials from .env if it exists (safe - .env is git-ignored).
# Values already set in the environment take priority over .env.
if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source ".env"
    set +a
fi

export EMAIL_BACKEND="${EMAIL_BACKEND:-django.core.mail.backends.smtp.EmailBackend}"
export EMAIL_HOST="${EMAIL_HOST:-smtp.gmail.com}"
export EMAIL_PORT="${EMAIL_PORT:-587}"
export EMAIL_USE_TLS="${EMAIL_USE_TLS:-True}"

if [ -z "$EMAIL_HOST_USER" ] || [ -z "$EMAIL_HOST_PASSWORD" ]; then
    echo "⚠️  EMAIL_HOST_USER / EMAIL_HOST_PASSWORD not set."
    echo "   Copy .env.example to .env and fill in your email credentials."
    echo ""
fi

echo "🚀 Starting PickleSphere with SMTP email support..."
echo "   Email: ${EMAIL_HOST_USER:-<not set>}"
echo "   SMTP:  ${EMAIL_HOST:-smtp.gmail.com}:${EMAIL_PORT} (TLS)"
echo "   Port:  $PORT"
echo ""

if [ "$USE_NGROK" = true ]; then
    echo "🌐 Starting ngrok tunnel to port $PORT..."
    # Start Django in background
    python manage.py runserver 0.0.0.0:$PORT &
    DJANGO_PID=$!
    sleep 2
    # Start ngrok in background (no pipe - head would kill it)
    ngrok http $PORT --log=stdout > /tmp/ngrok.log 2>&1 &
    NGROK_PID=$!
    sleep 3
    # Fetch the public URL from ngrok's local API
    NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | python -c "import sys,json; d=json.load(sys.stdin); t=d.get('tunnels',[]); print(t[0]['public_url'] if t else 'still starting...')" 2>/dev/null)
    echo ""
    echo "🔗 Public URL: $NGROK_URL"
    echo "   Dashboard: http://localhost:4040"
    echo "   Press Ctrl+C to stop both servers"
    echo ""
    # Wait for Django to finish
    wait $DJANGO_PID
    # Cleanup ngrok when Django stops
    kill $NGROK_PID 2>/dev/null
else
    python manage.py runserver 0.0.0.0:$PORT
fi
