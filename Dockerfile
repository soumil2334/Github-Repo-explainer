# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim-bookworm

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    gcc \
    g++ \
    build-essential \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────────────────────
COPY requirements.txt .

# Two-step install:
# Step 1 — install without dependency resolution (avoids langgraph conflict)
# Step 2 — install remaining deps that need resolution (httpx, pydantic etc.)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --no-deps -r requirements.txt && \
    pip install --no-cache-dir \
        annotated-types \
        certifi \
        charset-normalizer \
        click \
        h11 \
        httpcore \
        idna \
        sniffio \
        urllib3 \
        pydantic-core==2.41.5 \
        dataclasses-json \
        httpx-sse \
        jsonpatch \
        jsonpointer \
        marshmallow \
        mypy_extensions \
        numpy \
        orjson \
        regex \
        requests-toolbelt \
        s3transfer \
        SQLAlchemy \
        tiktoken \
        tqdm \
        typing-inspect \
        typing-inspection \
        uuid-utils \
        xxhash \
        zstandard \
        aiohappyeyeballs \
        aiosignal \
        attrs \
        frozenlist \
        multidict \
        propcache \
        yarl \
        griffe \
        mcp \
        types-requests \
        langchain-classic \
        jiter \
        distro \
        sse-starlette \
        annotated-doc

# ── Copy application code ─────────────────────────────────────────────────────
COPY . .

# ── Environment ───────────────────────────────────────────────────────────────
ENV PORT=8000
ENV WKHTMLTOPDF_PATH=/usr/bin/wkhtmltopdf

# ── Expose port ───────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Start command ─────────────────────────────────────────────────────────────
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}