# MABGP backend image
FROM python:3.11-slim

# WeasyPrint (F44 PDF export) needs these native libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --upgrade pip==24.3.1 && pip install -r requirements.txt
# F44: optional higher-quality PDF backend. The native libraries it needs are
# installed above, so WeasyPrint is importable here and selected automatically.
RUN pip install weasyprint==63.1

COPY app ./app
COPY pytest.ini ./
RUN mkdir -p /app/data

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8080/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
