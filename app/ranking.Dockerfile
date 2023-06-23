FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ranking_service.py .

ENV API_KEY=2b0bb2d89738ebb181a478c4e45d99a24ce44896c0f558f402cf00184d07f427
ENV MESSAGE_QUEUE_HOST=message_queue

CMD ["python", "ranking_service.py"]
