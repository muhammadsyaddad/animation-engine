pgvector | 2025-11-28 14:51:01.674 | 
pgvector | 2025-11-28 14:51:01.674 | PostgreSQL Database directory appears to contain a database; Skipping initialization
pgvector | 2025-11-28 14:51:01.674 | 
pgvector | 2025-11-28 14:51:01.713 | 2025-11-28 07:51:01.711 UTC [1] LOG:  starting PostgreSQL 16.2 (Debian 16.2-1.pgdg120+2) on x86_64-pc-linux-gnu, compiled by gcc (Debian 12.2.0-14) 12.2.0, 64-bit
pgvector | 2025-11-28 14:51:01.713 | 2025-11-28 07:51:01.711 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
pgvector | 2025-11-28 14:51:01.713 | 2025-11-28 07:51:01.711 UTC [1] LOG:  listening on IPv6 address "::", port 5432
pgvector | 2025-11-28 14:51:01.719 | 2025-11-28 07:51:01.718 UTC [1] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
pgvector | 2025-11-28 14:51:01.732 | 2025-11-28 07:51:01.732 UTC [28] LOG:  database system was shut down at 2025-11-28 07:50:58 UTC
pgvector | 2025-11-28 14:51:01.743 | 2025-11-28 07:51:01.741 UTC [1] LOG:  database system is ready to accept connections
api      | 2025-11-28 14:51:01.905 | ==================================================
api      | 2025-11-28 14:51:01.909 | PYTHON_SHA256=8d3ed8ec5c88c1c95f5e558612a725450d2452813ddad5e58fdb1a53b1209b78
api      | 2025-11-28 14:51:01.909 | HOSTNAME=265f2e2853f3
api      | 2025-11-28 14:51:01.909 | PYTHON_VERSION=3.11.14
api      | 2025-11-28 14:51:01.909 | ANTHROPIC_API_KEY=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
api      | 2025-11-28 14:51:01.909 | APPLY_LOCAL_SCHEMA=true
api      | 2025-11-28 14:51:01.909 | PWD=/app
api      | 2025-11-28 14:51:01.909 | DB_PORT=5432
api      | 2025-11-28 14:51:01.909 | DB_USER=ai
api      | 2025-11-28 14:51:01.909 | HOME=/app
api      | 2025-11-28 14:51:01.909 | LANG=C.UTF-8
api      | 2025-11-28 14:51:01.909 | GPG_KEY=A035C8C19219BA821ECEA86B64E628F8D684696D
api      | 2025-11-28 14:51:01.909 | DB_HOST=pgvector
api      | 2025-11-28 14:51:01.909 | SHLVL=1
api      | 2025-11-28 14:51:01.909 | APP_DIR=/app
api      | 2025-11-28 14:51:01.909 | PRINT_ENV_ON_LOAD=True
api      | 2025-11-28 14:51:01.909 | DOCKERIZE_VERSION=v0.7.0
api      | 2025-11-28 14:51:01.909 | WAIT_FOR_DB=True
api      | 2025-11-28 14:51:01.909 | PATH=/opt/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
api      | 2025-11-28 14:51:01.909 | DB_DATABASE=ai
api      | 2025-11-28 14:51:01.909 | DB_PASS=ai
api      | 2025-11-28 14:51:01.909 | AUTH_SECRET=H0M2yq3ZlCwD9pUt7rXj5VEgfpC4qQXvH1zK2sYt9NMb6Wn8RLa7YrczZb8sQ2vX
api      | 2025-11-28 14:51:01.909 | _=/usr/bin/printenv
api      | 2025-11-28 14:51:01.909 | ==================================================
api      | 2025-11-28 14:51:01.913 | 2025/11/28 07:51:01 Waiting for: tcp://pgvector:5432
api      | 2025-11-28 14:51:01.913 | 2025/11/28 07:51:01 Connected to tcp://pgvector:5432
api      | 2025-11-28 14:51:01.918 | [entrypoint] Applying local schema: /app/db/schema_local.sql
api      | 2025-11-28 14:51:02.015 | CREATE EXTENSION
api      | 2025-11-28 14:51:02.015 | CREATE EXTENSION
api      | 2025-11-28 14:51:02.015 | psql:/app/db/schema_local.sql:21: NOTICE:  extension "pgcrypto" already exists, skipping
api      | 2025-11-28 14:51:02.015 | psql:/app/db/schema_local.sql:22: NOTICE:  extension "uuid-ossp" already exists, skipping
api      | 2025-11-28 14:51:02.016 | CREATE EXTENSION
api      | 2025-11-28 14:51:02.016 | psql:/app/db/schema_local.sql:23: NOTICE:  extension "citext" already exists, skipping
api      | 2025-11-28 14:51:02.018 | CREATE TABLE
api      | 2025-11-28 14:51:02.018 | psql:/app/db/schema_local.sql:36: NOTICE:  relation "users" already exists, skipping
api      | 2025-11-28 14:51:02.020 | COMMENT
api      | 2025-11-28 14:51:02.021 | COMMENT
api      | 2025-11-28 14:51:02.022 | COMMENT
api      | 2025-11-28 14:51:02.023 | COMMENT
api      | 2025-11-28 14:51:02.024 | CREATE INDEX
api      | 2025-11-28 14:51:02.024 | CREATE TABLE
api      | 2025-11-28 14:51:02.024 | psql:/app/db/schema_local.sql:44: NOTICE:  relation "idx_users_email" already exists, skipping
api      | 2025-11-28 14:51:02.024 | psql:/app/db/schema_local.sql:55: NOTICE:  relation "profiles" already exists, skipping
api      | 2025-11-28 14:51:02.026 | COMMENT
api      | 2025-11-28 14:51:02.034 | COMMENT
api      | 2025-11-28 14:51:02.036 | COMMENT
api      | 2025-11-28 14:51:02.037 | psql:/app/db/schema_local.sql:76: NOTICE:  relation "agent_runs" already exists, skipping
api      | 2025-11-28 14:51:02.038 | CREATE TABLE
api      | 2025-11-28 14:51:02.039 | COMMENT
api      | 2025-11-28 14:51:02.042 | COMMENT
api      | 2025-11-28 14:51:02.043 | psql:/app/db/schema_local.sql:81: NOTICE:  relation "idx_agent_runs_user_id" already exists, skipping
api      | 2025-11-28 14:51:02.044 | CREATE INDEX
api      | 2025-11-28 14:51:02.045 | CREATE INDEX
api      | 2025-11-28 14:51:02.045 | CREATE INDEX
api      | 2025-11-28 14:51:02.045 | psql:/app/db/schema_local.sql:82: NOTICE:  relation "idx_agent_runs_created_at" already exists, skipping
api      | 2025-11-28 14:51:02.045 | psql:/app/db/schema_local.sql:83: NOTICE:  relation "idx_agent_runs_state" already exists, skipping
api      | 2025-11-28 14:51:02.051 | CREATE FUNCTION
api      | 2025-11-28 14:51:02.053 | DROP TRIGGER
api      | 2025-11-28 14:51:02.058 | CREATE TRIGGER
api      | 2025-11-28 14:51:02.060 | CREATE TABLE
api      | 2025-11-28 14:51:02.062 | COMMENT
api      | 2025-11-28 14:51:02.062 | psql:/app/db/schema_local.sql:114: NOTICE:  relation "datasets" already exists, skipping
api      | 2025-11-28 14:51:02.067 | COMMENT
api      | 2025-11-28 14:51:02.068 | COMMENT
api      | 2025-11-28 14:51:02.069 | CREATE INDEX
api      | 2025-11-28 14:51:02.069 | psql:/app/db/schema_local.sql:120: NOTICE:  relation "idx_datasets_user_id" already exists, skipping
api      | 2025-11-28 14:51:02.070 | CREATE INDEX
api      | 2025-11-28 14:51:02.070 | CREATE INDEX
api      | 2025-11-28 14:51:02.070 | psql:/app/db/schema_local.sql:121: NOTICE:  relation "idx_datasets_created_at" already exists, skipping
api      | 2025-11-28 14:51:02.070 | psql:/app/db/schema_local.sql:122: NOTICE:  relation "idx_datasets_filename" already exists, skipping
api      | 2025-11-28 14:51:02.071 | CREATE TABLE
api      | 2025-11-28 14:51:02.071 | psql:/app/db/schema_local.sql:138: NOTICE:  relation "artifacts" already exists, skipping
api      | 2025-11-28 14:51:02.073 | COMMENT
api      | 2025-11-28 14:51:02.074 | COMMENT
api      | 2025-11-28 14:51:02.076 | COMMENT
api      | 2025-11-28 14:51:02.077 | CREATE INDEX
api      | 2025-11-28 14:51:02.077 | CREATE INDEX
api      | 2025-11-28 14:51:02.077 | psql:/app/db/schema_local.sql:144: NOTICE:  relation "idx_artifacts_run_id" already exists, skipping
api      | 2025-11-28 14:51:02.077 | psql:/app/db/schema_local.sql:145: NOTICE:  relation "idx_artifacts_kind" already exists, skipping
api      | 2025-11-28 14:51:02.078 | CREATE INDEX
api      | 2025-11-28 14:51:02.078 | psql:/app/db/schema_local.sql:146: NOTICE:  relation "idx_artifacts_created_at" already exists, skipping
api      | 2025-11-28 14:51:02.087 | CREATE VIEW
api      | 2025-11-28 14:51:02.088 | COMMENT
api      | 2025-11-28 14:51:02.090 | CREATE TABLE
api      | 2025-11-28 14:51:02.090 | psql:/app/db/schema_local.sql:195: NOTICE:  relation "chat_sessions" already exists, skipping
api      | 2025-11-28 14:51:02.095 | COMMENT
api      | 2025-11-28 14:51:02.096 | COMMENT
api      | 2025-11-28 14:51:02.099 | CREATE FUNCTION
api      | 2025-11-28 14:51:02.102 | DROP TRIGGER
api      | 2025-11-28 14:51:02.102 | CREATE TRIGGER
api      | 2025-11-28 14:51:02.103 | CREATE INDEX
api      | 2025-11-28 14:51:02.103 | psql:/app/db/schema_local.sql:214: NOTICE:  relation "idx_chat_sessions_user_id" already exists, skipping
api      | 2025-11-28 14:51:02.105 | CREATE INDEX
api      | 2025-11-28 14:51:02.105 | CREATE TABLE
api      | 2025-11-28 14:51:02.105 | psql:/app/db/schema_local.sql:215: NOTICE:  relation "idx_chat_sessions_created_at" already exists, skipping
api      | 2025-11-28 14:51:02.105 | psql:/app/db/schema_local.sql:230: NOTICE:  relation "chat_messages" already exists, skipping
api      | 2025-11-28 14:51:02.107 | COMMENT
api      | 2025-11-28 14:51:02.109 | COMMENT
api      | 2025-11-28 14:51:02.109 | COMMENT
api      | 2025-11-28 14:51:02.110 | CREATE INDEX
api      | 2025-11-28 14:51:02.110 | psql:/app/db/schema_local.sql:236: NOTICE:  relation "idx_chat_messages_session_created" already exists, skipping
api      | 2025-11-28 14:51:02.110 | psql:/app/db/schema_local.sql:237: NOTICE:  relation "idx_chat_messages_user_id" already exists, skipping
api      | 2025-11-28 14:51:02.111 | CREATE INDEX
api      | 2025-11-28 14:51:02.112 | Running: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
api      | 2025-11-28 14:51:02.380 | INFO:     Will watch for changes in these directories: ['/app']
api      | 2025-11-28 14:51:02.380 | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
api      | 2025-11-28 14:51:02.381 | INFO:     Started reloader process [1] using WatchFiles
api      | 2025-11-28 14:51:05.861 | DEBUG **************** Agent ID: web_search_agent ****************              
api      | 2025-11-28 14:51:05.864 | DEBUG ****************** Agent ID: agno_assist *******************              
api      | 2025-11-28 14:51:05.866 | DEBUG ***************** Agent ID: finance_agent ******************              
api      | 2025-11-28 14:51:06.155 | INFO:     Started server process [15]
api      | 2025-11-28 14:51:06.155 | INFO:     Waiting for application startup.
api      | 2025-11-28 14:51:06.155 | INFO:     Application startup complete.
api      | 2025-11-28 14:53:51.814 | INFO:     192.168.65.1:49610 - "POST /v1/auth/login HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:57.763 | INFO:     192.168.65.1:44065 - "OPTIONS /v1/health HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:57.775 | INFO:     192.168.65.1:44065 - "GET /v1/health HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:57.776 | INFO:     192.168.65.1:38529 - "OPTIONS /v1/health HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:57.781 | INFO:     192.168.65.1:38529 - "GET /v1/health HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:57.825 | INFO:     192.168.65.1:38529 - "OPTIONS /v1/teams HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:57.829 | INFO:     192.168.65.1:38529 - "GET /v1/teams HTTP/1.1" 404 Not Found
api      | 2025-11-28 14:53:57.867 | INFO:     192.168.65.1:38529 - "GET /v1/teams HTTP/1.1" 404 Not Found
api      | 2025-11-28 14:53:57.985 | INFO:     192.168.65.1:38529 - "OPTIONS /v1/agents HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:57.986 | INFO:     192.168.65.1:44065 - "OPTIONS /v1/agents HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:57.988 | INFO:     192.168.65.1:38529 - "GET /v1/agents HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:57.990 | INFO:     192.168.65.1:44065 - "GET /v1/agents HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:58.098 | INFO:     192.168.65.1:44065 - "OPTIONS /v1/chat/sessions?user_only=true HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:58.100 | INFO:     192.168.65.1:38529 - "GET /v1/health HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:58.118 | INFO:     192.168.65.1:44065 - "GET /v1/chat/sessions?user_only=true HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:58.321 | INFO:     192.168.65.1:44065 - "GET /v1/chat/sessions?user_only=true HTTP/1.1" 200 OK
api      | 2025-11-28 14:53:58.546 | INFO:     192.168.65.1:44065 - "GET /v1/teams HTTP/1.1" 404 Not Found
api      | 2025-11-28 14:53:58.598 | INFO:     192.168.65.1:44065 - "GET /v1/agents HTTP/1.1" 200 OK
api      | 2025-11-28 14:54:03.860 | INFO:     192.168.65.1:22940 - "GET /v1/health HTTP/1.1" 200 OK
api      | 2025-11-28 14:54:03.942 | INFO:     192.168.65.1:22940 - "GET /v1/teams HTTP/1.1" 404 Not Found
api      | 2025-11-28 14:54:03.949 | INFO:     192.168.65.1:22940 - "GET /v1/agents HTTP/1.1" 200 OK
api      | 2025-11-28 14:54:03.991 | INFO:     192.168.65.1:22940 - "GET /v1/chat/sessions?user_only=true HTTP/1.1" 200 OK
api      | 2025-11-28 14:54:21.679 | INFO:     192.168.65.1:23161 - "POST /v1/datasets/upload HTTP/1.1" 201 Created
api      | 2025-11-28 14:54:29.414 | INFO:     192.168.65.1:37821 - "OPTIONS /v1/agents/animation_agent/runs HTTP/1.1" 200 OK
api      | 2025-11-28 14:54:29.438 | INFO:     192.168.65.1:37821 - "POST /v1/agents/animation_agent/runs HTTP/1.1" 200 OK
api      | 2025-11-28 14:54:30.240 | WARNING:  WatchFiles detected changes in 'artifacts/work/f00e1fa1-8aa3-4b47-83c3-d44b7341a68f/scene_69f370.py'. Reloading...
api      | 2025-11-28 14:54:30.255 | INFO:     Shutting down
api      | 2025-11-28 14:54:30.356 | INFO:     Waiting for connections to close. (CTRL+C to force quit)
pgvector | 2025-11-28 14:56:01.787 | 2025-11-28 07:56:01.787 UTC [26] LOG:  checkpoint starting: time
pgvector | 2025-11-28 14:56:04.734 | 2025-11-28 07:56:04.734 UTC [26] LOG:  checkpoint complete: wrote 32 buffers (0.2%); 0 WAL file(s) added, 0 removed, 0 recycled; write=2.931 s, sync=0.009 s, total=2.947 s; sync files=27, longest=0.006 s, average=0.001 s; distance=102 kB, estimate=102 kB; lsn=0/1EF6418, redo lsn=0/1EF63E0
pgvector | 2025-11-28 15:01:01.807 | 2025-11-28 08:01:01.806 UTC [26] LOG:  checkpoint starting: time
pgvector | 2025-11-28 15:01:02.396 | 2025-11-28 08:01:02.394 UTC [26] LOG:  checkpoint complete: wrote 6 buffers (0.0%); 0 WAL file(s) added, 0 removed, 0 recycled; write=0.524 s, sync=0.032 s, total=0.589 s; sync files=6, longest=0.021 s, average=0.006 s; distance=4 kB, estimate=92 kB; lsn=0/1EF7448, redo lsn=0/1EF7410
api      | 2025-11-28 15:14:47.577 | INFO:     Waiting for background tasks to complete. (CTRL+C to force quit)
pgvector | 2025-11-28 15:20:26.605 | 2025-11-28 08:20:26.601 UTC [1] LOG:  received fast shutdown request
pgvector | 2025-11-28 15:20:26.618 | 2025-11-28 08:20:26.607 UTC [1] LOG:  aborting any active transactions
pgvector | 2025-11-28 15:20:26.625 | 2025-11-28 08:20:26.625 UTC [1] LOG:  background worker "logical replication launcher" (PID 31) exited with exit code 1
pgvector | 2025-11-28 15:20:26.629 | 2025-11-28 08:20:26.629 UTC [26] LOG:  shutting down
pgvector | 2025-11-28 15:20:26.633 | 2025-11-28 08:20:26.632 UTC [26] LOG:  checkpoint starting: shutdown immediate
pgvector | 2025-11-28 15:20:26.651 | 2025-11-28 08:20:26.650 UTC [26] LOG:  checkpoint complete: wrote 0 buffers (0.0%); 0 WAL file(s) added, 0 removed, 0 recycled; write=0.001 s, sync=0.001 s, total=0.021 s; sync files=0, longest=0.000 s, average=0.000 s; distance=0 kB, estimate=83 kB; lsn=0/1EF74F8, redo lsn=0/1EF74F8
pgvector | 2025-11-28 15:20:26.666 | 2025-11-28 08:20:26.664 UTC [1] LOG:  database system is shut down
pgvector | 2025-11-29 00:43:22.094 | 
pgvector | 2025-11-29 00:43:22.095 | PostgreSQL Database directory appears to contain a database; Skipping initialization
pgvector | 2025-11-29 00:43:22.095 | 
pgvector | 2025-11-29 00:43:22.481 | 2025-11-28 17:43:22.481 UTC [1] LOG:  starting PostgreSQL 16.2 (Debian 16.2-1.pgdg120+2) on x86_64-pc-linux-gnu, compiled by gcc (Debian 12.2.0-14) 12.2.0, 64-bit
pgvector | 2025-11-29 00:43:22.482 | 2025-11-28 17:43:22.481 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
pgvector | 2025-11-29 00:43:22.482 | 2025-11-28 17:43:22.482 UTC [1] LOG:  listening on IPv6 address "::", port 5432
api      | 2025-11-29 00:43:22.504 | ==================================================
pgvector | 2025-11-29 00:43:22.505 | 2025-11-28 17:43:22.505 UTC [1] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
pgvector | 2025-11-29 00:43:22.528 | 2025-11-28 17:43:22.528 UTC [29] LOG:  database system was shut down at 2025-11-28 08:20:26 UTC
api      | 2025-11-29 00:43:22.536 | PYTHON_SHA256=8d3ed8ec5c88c1c95f5e558612a725450d2452813ddad5e58fdb1a53b1209b78
api      | 2025-11-29 00:43:22.537 | HOSTNAME=265f2e2853f3
api      | 2025-11-29 00:43:22.537 | PYTHON_VERSION=3.11.14
api      | 2025-11-29 00:43:22.537 | ANTHROPIC_API_KEY=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
api      | 2025-11-29 00:43:22.537 | APPLY_LOCAL_SCHEMA=true
api      | 2025-11-29 00:43:22.537 | PWD=/app
api      | 2025-11-29 00:43:22.537 | DB_PORT=5432
api      | 2025-11-29 00:43:22.537 | DB_USER=ai
api      | 2025-11-29 00:43:22.537 | HOME=/app
api      | 2025-11-29 00:43:22.537 | LANG=C.UTF-8
api      | 2025-11-29 00:43:22.537 | GPG_KEY=A035C8C19219BA821ECEA86B64E628F8D684696D
api      | 2025-11-29 00:43:22.537 | DB_HOST=pgvector
api      | 2025-11-29 00:43:22.537 | SHLVL=1
api      | 2025-11-29 00:43:22.537 | APP_DIR=/app
api      | 2025-11-29 00:43:22.537 | PRINT_ENV_ON_LOAD=True
api      | 2025-11-29 00:43:22.537 | DOCKERIZE_VERSION=v0.7.0
api      | 2025-11-29 00:43:22.537 | WAIT_FOR_DB=True
api      | 2025-11-29 00:43:22.537 | PATH=/opt/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
api      | 2025-11-29 00:43:22.537 | DB_DATABASE=ai
api      | 2025-11-29 00:43:22.537 | DB_PASS=ai
api      | 2025-11-29 00:43:22.537 | AUTH_SECRET=H0M2yq3ZlCwD9pUt7rXj5VEgfpC4qQXvH1zK2sYt9NMb6Wn8RLa7YrczZb8sQ2vX
api      | 2025-11-29 00:43:22.537 | _=/usr/bin/printenv
api      | 2025-11-29 00:43:22.537 | ==================================================
pgvector | 2025-11-29 00:43:22.576 | 2025-11-28 17:43:22.575 UTC [1] LOG:  database system is ready to accept connections
api      | 2025-11-29 00:43:22.629 | 2025/11/28 17:43:22 Waiting for: tcp://pgvector:5432
api      | 2025-11-29 00:43:22.641 | 2025/11/28 17:43:22 Connected to tcp://pgvector:5432
api      | 2025-11-29 00:43:22.648 | [entrypoint] Applying local schema: /app/db/schema_local.sql
api      | 2025-11-29 00:43:22.938 | psql:/app/db/schema_local.sql:21: NOTICE:  extension "pgcrypto" already exists, skipping
api      | 2025-11-29 00:43:22.939 | CREATE EXTENSION
api      | 2025-11-29 00:43:22.939 | CREATE EXTENSION
api      | 2025-11-29 00:43:22.939 | psql:/app/db/schema_local.sql:22: NOTICE:  extension "uuid-ossp" already exists, skipping
api      | 2025-11-29 00:43:22.940 | CREATE EXTENSION
api      | 2025-11-29 00:43:22.940 | psql:/app/db/schema_local.sql:23: NOTICE:  extension "citext" already exists, skipping
api      | 2025-11-29 00:43:22.944 | CREATE TABLE
api      | 2025-11-29 00:43:22.944 | psql:/app/db/schema_local.sql:36: NOTICE:  relation "users" already exists, skipping
api      | 2025-11-29 00:43:22.951 | COMMENT
api      | 2025-11-29 00:43:22.954 | COMMENT
api      | 2025-11-29 00:43:22.955 | COMMENT
api      | 2025-11-29 00:43:22.956 | COMMENT
api      | 2025-11-29 00:43:22.961 | CREATE INDEX
api      | 2025-11-29 00:43:22.961 | CREATE TABLE
api      | 2025-11-29 00:43:22.961 | psql:/app/db/schema_local.sql:44: NOTICE:  relation "idx_users_email" already exists, skipping
api      | 2025-11-29 00:43:22.961 | psql:/app/db/schema_local.sql:55: NOTICE:  relation "profiles" already exists, skipping
api      | 2025-11-29 00:43:22.963 | COMMENT
api      | 2025-11-29 00:43:22.964 | COMMENT
api      | 2025-11-29 00:43:22.965 | COMMENT
api      | 2025-11-29 00:43:22.965 | CREATE TABLE
api      | 2025-11-29 00:43:22.965 | psql:/app/db/schema_local.sql:76: NOTICE:  relation "agent_runs" already exists, skipping
api      | 2025-11-29 00:43:22.966 | COMMENT
api      | 2025-11-29 00:43:22.967 | COMMENT
api      | 2025-11-29 00:43:22.968 | CREATE INDEX
api      | 2025-11-29 00:43:22.968 | psql:/app/db/schema_local.sql:81: NOTICE:  relation "idx_agent_runs_user_id" already exists, skipping
api      | 2025-11-29 00:43:22.969 | CREATE INDEX
api      | 2025-11-29 00:43:22.969 | psql:/app/db/schema_local.sql:82: NOTICE:  relation "idx_agent_runs_created_at" already exists, skipping
api      | 2025-11-29 00:43:22.970 | CREATE INDEX
api      | 2025-11-29 00:43:22.970 | psql:/app/db/schema_local.sql:83: NOTICE:  relation "idx_agent_runs_state" already exists, skipping
api      | 2025-11-29 00:43:22.990 | CREATE FUNCTION
api      | 2025-11-29 00:43:22.994 | DROP TRIGGER
api      | 2025-11-29 00:43:22.997 | psql:/app/db/schema_local.sql:114: NOTICE:  relation "datasets" already exists, skipping
api      | 2025-11-29 00:43:22.997 | CREATE TRIGGER
api      | 2025-11-29 00:43:22.997 | CREATE TABLE
api      | 2025-11-29 00:43:22.999 | COMMENT
api      | 2025-11-29 00:43:23.000 | COMMENT
api      | 2025-11-29 00:43:23.000 | COMMENT
api      | 2025-11-29 00:43:23.001 | psql:/app/db/schema_local.sql:120: NOTICE:  relation "idx_datasets_user_id" already exists, skipping
api      | 2025-11-29 00:43:23.001 | psql:/app/db/schema_local.sql:121: NOTICE:  relation "idx_datasets_created_at" already exists, skipping
api      | 2025-11-29 00:43:23.001 | psql:/app/db/schema_local.sql:122: NOTICE:  relation "idx_datasets_filename" already exists, skipping
api      | 2025-11-29 00:43:23.001 | CREATE INDEX
api      | 2025-11-29 00:43:23.001 | CREATE INDEX
api      | 2025-11-29 00:43:23.001 | CREATE INDEX
api      | 2025-11-29 00:43:23.002 | psql:/app/db/schema_local.sql:138: NOTICE:  relation "artifacts" already exists, skipping
api      | 2025-11-29 00:43:23.002 | CREATE TABLE
api      | 2025-11-29 00:43:23.003 | COMMENT
api      | 2025-11-29 00:43:23.003 | COMMENT
api      | 2025-11-29 00:43:23.004 | psql:/app/db/schema_local.sql:144: NOTICE:  relation "idx_artifacts_run_id" already exists, skipping
api      | 2025-11-29 00:43:23.004 | COMMENT
api      | 2025-11-29 00:43:23.004 | CREATE INDEX
api      | 2025-11-29 00:43:23.005 | psql:/app/db/schema_local.sql:145: NOTICE:  relation "idx_artifacts_kind" already exists, skipping
api      | 2025-11-29 00:43:23.005 | psql:/app/db/schema_local.sql:146: NOTICE:  relation "idx_artifacts_created_at" already exists, skipping
api      | 2025-11-29 00:43:23.005 | CREATE INDEX
api      | 2025-11-29 00:43:23.005 | CREATE INDEX
api      | 2025-11-29 00:43:23.022 | CREATE VIEW
api      | 2025-11-29 00:43:23.023 | COMMENT
api      | 2025-11-29 00:43:23.024 | psql:/app/db/schema_local.sql:195: NOTICE:  relation "chat_sessions" already exists, skipping
api      | 2025-11-29 00:43:23.024 | CREATE TABLE
api      | 2025-11-29 00:43:23.025 | COMMENT
api      | 2025-11-29 00:43:23.026 | COMMENT
api      | 2025-11-29 00:43:23.027 | CREATE FUNCTION
api      | 2025-11-29 00:43:23.028 | DROP TRIGGER
api      | 2025-11-29 00:43:23.029 | psql:/app/db/schema_local.sql:214: NOTICE:  relation "idx_chat_sessions_user_id" already exists, skipping
api      | 2025-11-29 00:43:23.029 | CREATE TRIGGER
api      | 2025-11-29 00:43:23.029 | CREATE INDEX
api      | 2025-11-29 00:43:23.030 | CREATE INDEX
api      | 2025-11-29 00:43:23.030 | CREATE TABLE
api      | 2025-11-29 00:43:23.030 | psql:/app/db/schema_local.sql:215: NOTICE:  relation "idx_chat_sessions_created_at" already exists, skipping
api      | 2025-11-29 00:43:23.030 | psql:/app/db/schema_local.sql:230: NOTICE:  relation "chat_messages" already exists, skipping
api      | 2025-11-29 00:43:23.033 | COMMENT
api      | 2025-11-29 00:43:23.034 | COMMENT
api      | 2025-11-29 00:43:23.034 | COMMENT
api      | 2025-11-29 00:43:23.035 | CREATE INDEX
api      | 2025-11-29 00:43:23.035 | CREATE INDEX
api      | 2025-11-29 00:43:23.035 | psql:/app/db/schema_local.sql:236: NOTICE:  relation "idx_chat_messages_session_created" already exists, skipping
api      | 2025-11-29 00:43:23.035 | psql:/app/db/schema_local.sql:237: NOTICE:  relation "idx_chat_messages_user_id" already exists, skipping
api      | 2025-11-29 00:43:23.039 | Running: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
api      | 2025-11-29 00:43:23.539 | INFO:     Will watch for changes in these directories: ['/app']
api      | 2025-11-29 00:43:23.539 | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
api      | 2025-11-29 00:43:23.541 | INFO:     Started reloader process [1] using WatchFiles
api      | 2025-11-29 00:43:31.542 | DEBUG **************** Agent ID: web_search_agent ****************              
api      | 2025-11-29 00:43:31.544 | DEBUG ****************** Agent ID: agno_assist *******************              
api      | 2025-11-29 00:43:31.546 | DEBUG ***************** Agent ID: finance_agent ******************              
api      | 2025-11-29 00:43:31.768 | INFO:     Started server process [15]
api      | 2025-11-29 00:43:31.768 | INFO:     Waiting for application startup.
api      | 2025-11-29 00:43:31.769 | INFO:     Application startup complete.
pgvector | 2025-11-29 00:48:22.870 | 2025-11-28 17:48:22.869 UTC [27] LOG:  checkpoint starting: time
pgvector | 2025-11-29 00:48:24.303 | 2025-11-28 17:48:24.302 UTC [27] LOG:  checkpoint complete: wrote 16 buffers (0.1%); 0 WAL file(s) added, 0 removed, 0 recycled; write=1.417 s, sync=0.009 s, total=1.434 s; sync files=13, longest=0.007 s, average=0.001 s; distance=79 kB, estimate=79 kB; lsn=0/1F0B390, redo lsn=0/1F0B358
api      | 2025-11-29 01:04:22.693 | WARNING:  WatchFiles detected changes in 'agents/tools/video_manim.py'. Reloading...
api      | 2025-11-29 01:04:22.736 | INFO:     Shutting down
api      | 2025-11-29 01:04:22.843 | INFO:     Waiting for application shutdown.
api      | 2025-11-29 01:04:22.873 | INFO:     Application shutdown complete.
api      | 2025-11-29 01:04:22.875 | INFO:     Finished server process [15]
api      | 2025-11-29 01:04:27.326 | DEBUG **************** Agent ID: web_search_agent ****************              
api      | 2025-11-29 01:04:27.330 | DEBUG ****************** Agent ID: agno_assist *******************              
api      | 2025-11-29 01:04:27.333 | DEBUG ***************** Agent ID: finance_agent ******************              
api      | 2025-11-29 01:04:27.663 | INFO:     Started server process [20]
api      | 2025-11-29 01:04:27.663 | INFO:     Waiting for application startup.
api      | 2025-11-29 01:04:27.664 | INFO:     Application startup complete.
api      | 2025-11-29 01:06:36.225 | INFO:     192.168.65.1:63206 - "POST /v1/auth/login HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:41.785 | INFO:     192.168.65.1:26179 - "OPTIONS /v1/health HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:41.785 | INFO:     192.168.65.1:32856 - "OPTIONS /v1/health HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:41.794 | INFO:     192.168.65.1:26179 - "GET /v1/health HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:41.807 | INFO:     192.168.65.1:32856 - "GET /v1/health HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:41.833 | INFO:     192.168.65.1:32856 - "OPTIONS /v1/teams HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:41.838 | INFO:     192.168.65.1:32856 - "GET /v1/teams HTTP/1.1" 404 Not Found
api      | 2025-11-29 01:06:41.920 | INFO:     192.168.65.1:26179 - "OPTIONS /v1/agents HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:41.928 | INFO:     192.168.65.1:32856 - "GET /v1/teams HTTP/1.1" 404 Not Found
api      | 2025-11-29 01:06:41.975 | INFO:     192.168.65.1:32856 - "GET /v1/agents HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:42.164 | INFO:     192.168.65.1:32856 - "GET /v1/agents HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:42.164 | INFO:     192.168.65.1:26179 - "OPTIONS /v1/chat/sessions?user_only=true HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:42.188 | INFO:     192.168.65.1:43231 - "GET /v1/health HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:42.193 | INFO:     192.168.65.1:32856 - "GET /v1/chat/sessions?user_only=true HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:42.307 | INFO:     192.168.65.1:32856 - "GET /v1/teams HTTP/1.1" 404 Not Found
api      | 2025-11-29 01:06:42.419 | INFO:     192.168.65.1:32856 - "GET /v1/agents HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:42.470 | INFO:     192.168.65.1:32856 - "GET /v1/chat/sessions?user_only=true HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:46.830 | INFO:     192.168.65.1:32856 - "GET /v1/health HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:46.899 | INFO:     192.168.65.1:32856 - "GET /v1/teams HTTP/1.1" 404 Not Found
api      | 2025-11-29 01:06:46.915 | INFO:     192.168.65.1:32856 - "GET /v1/agents HTTP/1.1" 200 OK
api      | 2025-11-29 01:06:46.960 | INFO:     192.168.65.1:32856 - "GET /v1/chat/sessions?user_only=true HTTP/1.1" 200 OK
api      | 2025-11-29 01:07:01.018 | INFO:     192.168.65.1:29984 - "POST /v1/datasets/upload HTTP/1.1" 201 Created
api      | 2025-11-29 01:07:09.137 | INFO:     192.168.65.1:46812 - "OPTIONS /v1/agents/animation_agent/runs HTTP/1.1" 200 OK
api      | 2025-11-29 01:07:09.161 | INFO:     192.168.65.1:46812 - "POST /v1/agents/animation_agent/runs HTTP/1.1" 200 OK
api      | 2025-11-29 01:07:10.044 | WARNING:  WatchFiles detected changes in 'artifacts/work/b5017e36-a4c4-4642-bf6f-cd4f702190e2/scene_f3aac9.py'. Reloading...
api      | 2025-11-29 01:07:10.066 | INFO:     Shutting down
api      | 2025-11-29 01:07:10.168 | INFO:     Waiting for connections to close. (CTRL+C to force quit)
pgvector | 2025-11-29 01:08:22.427 | 2025-11-28 18:08:22.427 UTC [27] LOG:  checkpoint starting: time
pgvector | 2025-11-29 01:08:23.564 | 2025-11-28 18:08:23.564 UTC [27] LOG:  checkpoint complete: wrote 12 buffers (0.1%); 0 WAL file(s) added, 0 removed, 0 recycled; write=1.126 s, sync=0.005 s, total=1.138 s; sync files=12, longest=0.003 s, average=0.001 s; distance=13 kB, estimate=73 kB; lsn=0/1F0EA68, redo lsn=0/1F0EA30
api      | 2025-11-29 01:10:16.719 | INFO:     Waiting for application shutdown.
api      | 2025-11-29 01:10:16.719 | INFO:     Application shutdown complete.
api      | 2025-11-29 01:10:16.719 | INFO:     Finished server process [20]
api      | 2025-11-29 01:10:17.120 | WARNING:  WatchFiles detected changes in 'artifacts/work/97dc58dc-15e8-477c-8487-9a0f9e06b0ae/scene_2d5e7a.py', 'artifacts/work/b5017e36-a4c4-4642-bf6f-cd4f702190e2/scene_f3aac9.py'. Reloading...
api      | 2025-11-29 01:10:19.694 | DEBUG **************** Agent ID: web_search_agent ****************              
api      | 2025-11-29 01:10:19.696 | DEBUG ****************** Agent ID: agno_assist *******************              
api      | 2025-11-29 01:10:19.698 | DEBUG ***************** Agent ID: finance_agent ******************              
api      | 2025-11-29 01:10:19.977 | INFO:     Started server process [105]
api      | 2025-11-29 01:10:19.977 | INFO:     Waiting for application startup.
api      | 2025-11-29 01:10:19.978 | INFO:     Application startup complete.
api      | 2025-11-29 01:10:22.566 | DEBUG **************** Agent ID: web_search_agent ****************              
api      | 2025-11-29 01:10:22.569 | DEBUG ****************** Agent ID: agno_assist *******************              
api      | 2025-11-29 01:10:22.572 | DEBUG ***************** Agent ID: finance_agent ******************              
api      | 2025-11-29 01:10:22.841 | INFO:     Started server process [115]
api      | 2025-11-29 01:10:22.841 | INFO:     Waiting for application startup.
api      | 2025-11-29 01:10:22.841 | INFO:     Application startup complete.
api      | 2025-11-29 01:10:22.842 | INFO:     192.168.65.1:30093 - "OPTIONS /v1/chat/sessions HTTP/1.1" 200 OK
api      | 2025-11-29 01:10:22.877 | INFO:     192.168.65.1:30093 - "POST /v1/chat/sessions HTTP/1.1" 201 Created
api      | 2025-11-29 01:10:23.038 | INFO:     192.168.65.1:30093 - "OPTIONS /v1/chat/sessions/10eec8dc-8a25-4356-93e7-74af91827766 HTTP/1.1" 200 OK
api      | 2025-11-29 01:10:23.044 | INFO:     192.168.65.1:49367 - "OPTIONS /v1/chat/sessions/10eec8dc-8a25-4356-93e7-74af91827766/messages HTTP/1.1" 200 OK
api      | 2025-11-29 01:10:23.087 | INFO:     192.168.65.1:49367 - "POST /v1/chat/sessions/10eec8dc-8a25-4356-93e7-74af91827766/messages HTTP/1.1" 500 Internal Server Error
api      | 2025-11-29 01:10:23.124 | ERROR:    Exception in ASGI application
api      | 2025-11-29 01:10:23.124 | Traceback (most recent call last):
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/engine/base.py", line 1964, in _exec_single_context
api      | 2025-11-29 01:10:23.124 |     self.dialect.do_execute(
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/engine/default.py", line 945, in do_execute
api      | 2025-11-29 01:10:23.124 |     cursor.execute(statement, parameters)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/psycopg/cursor.py", line 97, in execute
api      | 2025-11-29 01:10:23.124 |     raise ex.with_traceback(None)
api      | 2025-11-29 01:10:23.124 | psycopg.ProgrammingError: cannot adapt type 'dict' using placeholder '%s' (format: AUTO)
api      | 2025-11-29 01:10:23.124 | 
api      | 2025-11-29 01:10:23.124 | The above exception was the direct cause of the following exception:
api      | 2025-11-29 01:10:23.124 | 
api      | 2025-11-29 01:10:23.124 | Traceback (most recent call last):
api      | 2025-11-29 01:10:23.124 |   File "/app/api/persistence/chat_repository.py", line 288, in create_chat_message
api      | 2025-11-29 01:10:23.124 |     row = session.execute(
api      | 2025-11-29 01:10:23.124 |           ^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/orm/session.py", line 2365, in execute
api      | 2025-11-29 01:10:23.124 |     return self._execute_internal(
api      | 2025-11-29 01:10:23.124 |            ^^^^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/orm/session.py", line 2260, in _execute_internal
api      | 2025-11-29 01:10:23.124 |     result = conn.execute(
api      | 2025-11-29 01:10:23.124 |              ^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/engine/base.py", line 1416, in execute
api      | 2025-11-29 01:10:23.124 |     return meth(
api      | 2025-11-29 01:10:23.124 |            ^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/sql/elements.py", line 523, in _execute_on_connection
api      | 2025-11-29 01:10:23.124 |     return connection._execute_clauseelement(
api      | 2025-11-29 01:10:23.124 |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/engine/base.py", line 1638, in _execute_clauseelement
api      | 2025-11-29 01:10:23.124 |     ret = self._execute_context(
api      | 2025-11-29 01:10:23.124 |           ^^^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/engine/base.py", line 1843, in _execute_context
api      | 2025-11-29 01:10:23.124 |     return self._exec_single_context(
api      | 2025-11-29 01:10:23.124 |            ^^^^^^^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/engine/base.py", line 1983, in _exec_single_context
api      | 2025-11-29 01:10:23.124 |     self._handle_dbapi_exception(
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/engine/base.py", line 2352, in _handle_dbapi_exception
api      | 2025-11-29 01:10:23.124 |     raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/engine/base.py", line 1964, in _exec_single_context
api      | 2025-11-29 01:10:23.124 |     self.dialect.do_execute(
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/sqlalchemy/engine/default.py", line 945, in do_execute
api      | 2025-11-29 01:10:23.124 |     cursor.execute(statement, parameters)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/psycopg/cursor.py", line 97, in execute
api      | 2025-11-29 01:10:23.124 |     raise ex.with_traceback(None)
api      | 2025-11-29 01:10:23.124 | sqlalchemy.exc.ProgrammingError: (psycopg.ProgrammingError) cannot adapt type 'dict' using placeholder '%s' (format: AUTO)
api      | 2025-11-29 01:10:23.124 | [SQL: 
api      | 2025-11-29 01:10:23.124 |         insert into public.chat_messages (session_id, user_id, role, content, extra_json)
api      | 2025-11-29 01:10:23.124 |         values (%(session_id)s, %(user_id)s, %(role)s, %(content)s, %(extra_json)s)
api      | 2025-11-29 01:10:23.124 |         returning id, session_id, user_id, role, content, extra_json, created_at
api      | 2025-11-29 01:10:23.124 |         ]
api      | 2025-11-29 01:10:23.124 | [parameters: {'session_id': '10eec8dc-8a25-4356-93e7-74af91827766', 'user_id': None, 'role': 'agent', 'content': "Animation intent detected (chart_type=unknown, confidence=0.45). Entering animation pipeline.Analyzing prompt for chart spec and generating code...Da ... (932 characters truncated) ... 416 frame(s) written...Preview progress: 1436 frame(s) written...Preview progress: 1445 frame(s) written...Preview generated.Starting Manim render...", 'extra_json': {'images': [{'url': '/static/previews/preview-local-demo-1-4d0f8e/GenScene0000.png', 'revised_prompt': ''}, {'url': '/static/previews/preview-local-de ... (480 characters truncated) ... mo-1-4d0f8e/GenScene0024.png', 'revised_prompt': ''}, {'url': '/static/previews/preview-local-demo-1-4d0f8e/GenScene0028.png', 'revised_prompt': ''}]}}]
api      | 2025-11-29 01:10:23.124 | (Background on this error at: https://sqlalche.me/e/20/f405)
api      | 2025-11-29 01:10:23.124 | 
api      | 2025-11-29 01:10:23.124 | The above exception was the direct cause of the following exception:
api      | 2025-11-29 01:10:23.124 | 
api      | 2025-11-29 01:10:23.124 | Traceback (most recent call last):
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, in run_asgi
api      | 2025-11-29 01:10:23.124 |     result = await app(  # type: ignore[func-returns-value]
api      | 2025-11-29 01:10:23.124 |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
api      | 2025-11-29 01:10:23.124 |     return await self.app(scope, receive, send)
api      | 2025-11-29 01:10:23.124 |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/fastapi/applications.py", line 1054, in __call__
api      | 2025-11-29 01:10:23.124 |     await super().__call__(scope, receive, send)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/applications.py", line 112, in __call__
api      | 2025-11-29 01:10:23.124 |     await self.middleware_stack(scope, receive, send)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/middleware/errors.py", line 187, in __call__
api      | 2025-11-29 01:10:23.124 |     raise exc
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/middleware/errors.py", line 165, in __call__
api      | 2025-11-29 01:10:23.124 |     await self.app(scope, receive, _send)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/middleware/cors.py", line 93, in __call__
api      | 2025-11-29 01:10:23.124 |     await self.simple_response(scope, receive, send, request_headers=headers)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/middleware/cors.py", line 144, in simple_response
api      | 2025-11-29 01:10:23.124 |     await self.app(scope, receive, send)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/middleware/exceptions.py", line 62, in __call__
api      | 2025-11-29 01:10:23.124 |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
api      | 2025-11-29 01:10:23.124 |     raise exc
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
api      | 2025-11-29 01:10:23.124 |     await app(scope, receive, sender)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/routing.py", line 714, in __call__
api      | 2025-11-29 01:10:23.124 |     await self.middleware_stack(scope, receive, send)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/routing.py", line 734, in app
api      | 2025-11-29 01:10:23.124 |     await route.handle(scope, receive, send)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/routing.py", line 288, in handle
api      | 2025-11-29 01:10:23.124 |     await self.app(scope, receive, send)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/routing.py", line 76, in app
api      | 2025-11-29 01:10:23.124 |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
api      | 2025-11-29 01:10:23.124 |     raise exc
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
api      | 2025-11-29 01:10:23.124 |     await app(scope, receive, sender)
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/routing.py", line 73, in app
api      | 2025-11-29 01:10:23.124 |     response = await f(request)
api      | 2025-11-29 01:10:23.124 |                ^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/fastapi/routing.py", line 301, in app
api      | 2025-11-29 01:10:23.124 |     raw_response = await run_endpoint_function(
api      | 2025-11-29 01:10:23.124 |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/fastapi/routing.py", line 214, in run_endpoint_function
api      | 2025-11-29 01:10:23.124 |     return await run_in_threadpool(dependant.call, **values)
api      | 2025-11-29 01:10:23.124 |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/starlette/concurrency.py", line 37, in run_in_threadpool
api      | 2025-11-29 01:10:23.124 |     return await anyio.to_thread.run_sync(func)
api      | 2025-11-29 01:10:23.124 |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/anyio/to_thread.py", line 56, in run_sync
api      | 2025-11-29 01:10:23.124 |     return await get_async_backend().run_sync_in_worker_thread(
api      | 2025-11-29 01:10:23.124 |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/anyio/_backends/_asyncio.py", line 2470, in run_sync_in_worker_thread
api      | 2025-11-29 01:10:23.124 |     return await future
api      | 2025-11-29 01:10:23.124 |            ^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/opt/venv/lib/python3.11/site-packages/anyio/_backends/_asyncio.py", line 967, in run
api      | 2025-11-29 01:10:23.124 |     result = context.run(func, *args)
api      | 2025-11-29 01:10:23.124 |              ^^^^^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/app/api/routes/chat.py", line 311, in create_message
api      | 2025-11-29 01:10:23.124 |     msg = create_chat_message(
api      | 2025-11-29 01:10:23.124 |           ^^^^^^^^^^^^^^^^^^^^
api      | 2025-11-29 01:10:23.124 |   File "/app/api/persistence/chat_repository.py", line 302, in create_chat_message
api      | 2025-11-29 01:10:23.124 |     raise ChatRepositoryError(f"Failed to create chat message: {e}") from e
api      | 2025-11-29 01:10:23.124 | api.persistence.chat_repository.ChatRepositoryError: Failed to create chat message: (psycopg.ProgrammingError) cannot adapt type 'dict' using placeholder '%s' (format: AUTO)
api      | 2025-11-29 01:10:23.124 | [SQL: 
api      | 2025-11-29 01:10:23.124 |         insert into public.chat_messages (session_id, user_id, role, content, extra_json)
api      | 2025-11-29 01:10:23.124 |         values (%(session_id)s, %(user_id)s, %(role)s, %(content)s, %(extra_json)s)
api      | 2025-11-29 01:10:23.124 |         returning id, session_id, user_id, role, content, extra_json, created_at
api      | 2025-11-29 01:10:23.124 |         ]
api      | 2025-11-29 01:10:23.124 | [parameters: {'session_id': '10eec8dc-8a25-4356-93e7-74af91827766', 'user_id': None, 'role': 'agent', 'content': "Animation intent detected (chart_type=unknown, confidence=0.45). Entering animation pipeline.Analyzing prompt for chart spec and generating code...Da ... (932 characters truncated) ... 416 frame(s) written...Preview progress: 1436 frame(s) written...Preview progress: 1445 frame(s) written...Preview generated.Starting Manim render...", 'extra_json': {'images': [{'url': '/static/previews/preview-local-demo-1-4d0f8e/GenScene0000.png', 'revised_prompt': ''}, {'url': '/static/previews/preview-local-de ... (480 characters truncated) ... mo-1-4d0f8e/GenScene0024.png', 'revised_prompt': ''}, {'url': '/static/previews/preview-local-demo-1-4d0f8e/GenScene0028.png', 'revised_prompt': ''}]}}]
api      | 2025-11-29 01:10:23.124 | (Background on this error at: https://sqlalche.me/e/20/f405)
api      | 2025-11-29 01:10:23.129 | INFO:     192.168.65.1:30093 - "GET /v1/chat/sessions/10eec8dc-8a25-4356-93e7-74af91827766 HTTP/1.1" 200 OK
api      | 2025-11-29 01:10:23.166 | INFO:     192.168.65.1:30093 - "OPTIONS /v1/chat/sessions/10eec8dc-8a25-4356-93e7-74af91827766/messages?ascending=true HTTP/1.1" 200 OK
api      | 2025-11-29 01:10:23.183 | INFO:     192.168.65.1:30093 - "GET /v1/chat/sessions/10eec8dc-8a25-4356-93e7-74af91827766/messages?ascending=true HTTP/1.1" 200 OK
api      | 2025-11-29 01:10:25.203 | INFO:     192.168.65.1:30093 - "GET /v1/chat/sessions/10eec8dc-8a25-4356-93e7-74af91827766 HTTP/1.1" 200 OK
api      | 2025-11-29 01:10:25.218 | INFO:     192.168.65.1:30093 - "GET /v1/chat/sessions/10eec8dc-8a25-4356-93e7-74af91827766/messages?ascending=true HTTP/1.1" 200 OK
