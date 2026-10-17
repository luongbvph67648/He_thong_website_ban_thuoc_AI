# Build từ GỐC repo: docker build -f backend/Dockerfile .
# Cần kèm docs/spec/data/quyen.yaml (danh mục quyền) vì code đọc `../docs/spec/data/quyen.yaml` tính từ thư mục backend.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv==0.11.* && useradd --create-home --uid 1000 app
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
COPY docs/spec/data/quyen.yaml /app/docs/spec/data/quyen.yaml
RUN mkdir -p /app/backend/storage && chown -R app:app /app/backend/storage
USER app
ENV PATH="/app/backend/.venv/bin:$PATH"
EXPOSE 8000
# Sau reverse proxy (nginx trong compose) mới tin X-Forwarded-For: chỉ cho IP proxy, không dùng "*" khi cổng api ra ngoài
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
