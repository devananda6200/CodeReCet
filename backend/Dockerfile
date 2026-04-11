FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    git-lfs \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install and configure Git LFS
RUN git lfs install --skip-repo

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Extract model if ZIP file exists (for Git LFS builds)
RUN if [ -f models/best.pt.zip ]; then \
    unzip -q models/best.pt.zip -d models/ && \
    rm models/best.pt.zip; \
    fi

RUN mkdir -p /app/backend/data/uploads /app/backend/data/snapshots /app/backend/data/alerts /app/backend/models

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

