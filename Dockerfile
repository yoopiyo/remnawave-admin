# Remnawave Node Agent — лёгкий образ для деплоя на нодах
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Запуск из корня проекта: python -m src.main
CMD ["python", "-m", "src.main"]
