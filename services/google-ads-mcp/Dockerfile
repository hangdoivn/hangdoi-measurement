FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY . .

EXPOSE 8010
CMD ["python", "app.py"]
