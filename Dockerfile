FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_PORT=8501 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install OS dependency required by PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgl1 \
        && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate the synthetic datasets (SQLite SSOT, PDFs, knowledge graph, Chroma index)
# so the container is fully self-contained and demo-ready without an API key.
RUN python scripts/generate_bom.py \
    && python scripts/generate_documents.py \
    && python scripts/seed_graph.py \
    && python ingestion/embedder.py

EXPOSE 8501

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5)" || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]