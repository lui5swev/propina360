FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/backend-fastapi

COPY backend-fastapi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend-fastapi/app ./app

RUN mkdir -p /data

ENV PROPINA360_DB_URL=sqlite:////data/propina360.db
ENV PROPINA360_SIGNING_KEY=change-me-local

EXPOSE 18765

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18765"]