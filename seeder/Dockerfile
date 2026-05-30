FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data_producer/ ./data_producer/
COPY seed.py .

CMD ["python", "seed.py"]
