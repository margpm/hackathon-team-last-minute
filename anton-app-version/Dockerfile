FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

# Using -u to unbuffer stdout so logs appear in docker logs immediately
CMD ["python", "-u", "-m", "app.main"]
