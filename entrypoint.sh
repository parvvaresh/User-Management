
1.08 KiB
#!/usr/bin/env bash
# Django Application Entrypoint Script
# This script handles database migrations and starts the application server

set -e

# ============================================================================
# Configuration
# ============================================================================

DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_TIMEOUT=${DB_TIMEOUT:-30}
STARTUP_PERIOD=0.1

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
  echo "ℹ️  $1"
}

log_success() {
  echo "✅  $1"
}

log_error() {
  echo "❌  $1"
}

log_wait() {
  echo "⏳  $1"
}

# Wait for a service to be available
wait_for_service() {
  local host=$1
  local port=$2
  local service_name=$3
  local timeout=$4

  log_wait "Waiting for $service_name ($host:$port)..."

  local elapsed=0
  while ! nc -z "$host" "$port" 2>/dev/null; do
    if [ $elapsed -ge $timeout ]; then
      log_error "$service_name failed to start within ${timeout}s"
      return 1
    fi
    sleep $STARTUP_PERIOD
    elapsed=$((elapsed + 1))
  done

  log_success "$service_name is ready."
}

# ============================================================================
# Main Script
# ============================================================================

echo ""
log_info "🚀 Starting Django Application"
echo ""

# Wait for database to be ready (if not using SQLite)
if [[ "$DJANGO_DB_ENGINE" != *"sqlite"* ]]; then
  if ! wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL" "$DB_TIMEOUT"; then
    log_error "Could not connect to database"
    exit 1
  fi
fi

# Apply database migrations
log_info "📦 Applying database migrations..."
if python manage.py migrate --noinput; then
  log_success "Database migrations applied."
else
  log_error "Migration failed"
  exit 1
fi

# Collect static files (optional, mainly for production)
log_info "🎨 Collecting static files..."
if python manage.py collectstatic --noinput 2>/dev/null; then
  log_success "Static files collected."
else
  log_info "Static files collection skipped or failed (continuing...)."
fi

echo ""
log_success "✨ Application ready!"
echo ""

# Execute provided command or start the development server
if [[ $# -gt 0 ]]; then
  log_info "Executing custom command: $@"
  exec "$@"
else
  log_info "Starting development server on 0.0.0.0:8000"
  exec python manage.py runserver 0.0.0.0:8000
fi