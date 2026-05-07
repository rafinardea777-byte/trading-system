FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# תלויות מערכת ל-pandas/yfinance/psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# יצירת תיקיית data לכתיבה (כש-DB הוא SQLite)
RUN mkdir -p data/reports

EXPOSE 7860

# נטען מ-PORT אם קיים (HF Spaces מגדיר אוטומטית), אחרת 7860 (HF default)
ENV PORT=7860
CMD python -m app.cli init-db && python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
