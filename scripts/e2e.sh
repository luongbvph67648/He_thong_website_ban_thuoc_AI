#!/usr/bin/env bash
# Chạy kịch bản Playwright (frontend/e2e) trên CSDL riêng `nha_thuoc_e2e` được dựng lại từ đầu bằng seed demo.
# Cần: Postgres đang chạy (docker compose up -d db) kèm `psql`, `uv`, Node; Chromium do Playwright cài
# (npx playwright install chromium) hoặc đặt PW_CHROMIUM trỏ tới trình duyệt có sẵn.
# Không đụng vào CSDL dev `nha_thuoc`. Tham số được chuyển cho `playwright test` (ví dụ: e2e/doi-tra.spec.ts).
set -euo pipefail

GOC="$(cd "$(dirname "$0")/.." && pwd)"
PG_QUAN_TRI="${PG_QUAN_TRI:-postgresql://postgres:postgres@localhost:5432/postgres}"
TEN_DB="nha_thuoc_e2e"
export DATABASE_URL="${PG_QUAN_TRI%/*}/${TEN_DB}"
export DATABASE_URL="${DATABASE_URL/postgresql:/postgresql+asyncpg:}"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_MAT_KHAU="Admin@12345678"
export E2E_ADMIN_EMAIL="$ADMIN_EMAIL" E2E_ADMIN_MAT_KHAU="$ADMIN_MAT_KHAU"
export COOKIE_SECURE=false

psql "$PG_QUAN_TRI" -qc "DROP DATABASE IF EXISTS ${TEN_DB} WITH (FORCE)" -c "CREATE DATABASE ${TEN_DB}"
psql "${PG_QUAN_TRI%/*}/${TEN_DB}" -qc "CREATE EXTENSION IF NOT EXISTS vector"

cd "$GOC/backend"
uv run alembic upgrade head >/dev/null
uv run python -m app.seed --demo | tail -3
# Admin seed phải đổi mật khẩu ở lần đầu: bỏ cờ để kịch bản vào thẳng khu quản trị
psql "${PG_QUAN_TRI%/*}/${TEN_DB}" -qc "UPDATE nhan_vien SET phai_doi_mat_khau = false WHERE email = '${ADMIN_EMAIL}'"

uv run uvicorn app.main:app --port 8000 >/tmp/e2e-backend.log 2>&1 &
PID_BE=$!
cd "$GOC/frontend"
npm run dev >/tmp/e2e-frontend.log 2>&1 &
PID_FE=$!
trap 'kill $PID_BE $PID_FE 2>/dev/null || true' EXIT

for _ in $(seq 1 60); do
  curl -fs localhost:8000/api/v1/health >/dev/null && curl -fs localhost:5173 >/dev/null && break
  sleep 1
done
curl -fs localhost:8000/api/v1/health >/dev/null || { echo "Backend không lên (xem /tmp/e2e-backend.log)"; exit 1; }

npx playwright test "$@"
