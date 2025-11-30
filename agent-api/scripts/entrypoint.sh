#!/bin/bash

############################################################################
# Container Entrypoint script
############################################################################

if [[ "$PRINT_ENV_ON_LOAD" = true || "$PRINT_ENV_ON_LOAD" = True ]]; then
  echo "=================================================="
  printenv
  echo "=================================================="
fi

if [[ "$WAIT_FOR_DB" = true || "$WAIT_FOR_DB" = True ]]; then
  if command -v dockerize >/dev/null 2>&1; then
    dockerize \
      -wait "tcp://${DB_HOST}:${DB_PORT}" \
      -timeout 300s
  else
    echo "[entrypoint] dockerize not found; falling back to manual wait for ${DB_HOST}:${DB_PORT}"
    start_ts=$(date +%s)
    timeout_sec=300
    while true; do
      if (echo >/dev/tcp/"${DB_HOST}"/"${DB_PORT}") >/dev/null 2>&1; then
        echo "[entrypoint] database is up"
        break
      fi
      now_ts=$(date +%s)
      elapsed=$((now_ts - start_ts))
      if (( elapsed >= timeout_sec )); then
        echo "[entrypoint] ERROR: timed out waiting for ${DB_HOST}:${DB_PORT}" >&2
        exit 1
      fi
      sleep 2
    done
  fi
fi

if [[ "$APPLY_LOCAL_SCHEMA" = true || "$APPLY_LOCAL_SCHEMA" = True ]]; then
  SCHEMA_FILE="${APP_DIR}/db/schema_local.sql"
  if command -v psql >/dev/null 2>&1; then
    if [[ -f "$SCHEMA_FILE" ]]; then
      echo "[entrypoint] Applying local schema: $SCHEMA_FILE"
      # Build connection string
      if [[ -n "$DATABASE_URL" ]]; then
        CONN_STR="$DATABASE_URL"
      else
        DRIVER="${DB_DRIVER:-postgresql}"
        USER="${DB_USER}"
        PASS="${DB_PASS}"
        HOST="${DB_HOST}"
        PORT="${DB_PORT}"
        DB="${DB_DATABASE}"
        if [[ -n "$PASS" ]]; then
          CONN_STR="${DRIVER}://${USER}:${PASS}@${HOST}:${PORT}/${DB}"
        else
          CONN_STR="${DRIVER}://${USER}@${HOST}:${PORT}/${DB}"
        fi
      fi
      psql "$CONN_STR" -v ON_ERROR_STOP=1 -f "$SCHEMA_FILE" || {
        echo "[entrypoint] ERROR applying local schema"; exit 1;
      }
    else
      echo "[entrypoint] Local schema file not found: $SCHEMA_FILE"
    fi
  else
    echo "[entrypoint] psql not found; skipping schema apply"
  fi
fi

############################################################################
# Start App
############################################################################

case "$1" in
  chill)
    ;;
  *)
    echo "Running: $@"
    exec "$@"
    ;;
esac

echo ">>> Hello World!"
while true; do sleep 18000; done
