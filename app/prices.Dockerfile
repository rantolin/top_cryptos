FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY prices_service.py .


ENV PRICES_API_KEY=80d994b0-43ea-4f93-8557-892986e96f2e
ENV MESSAGE_QUEUE_HOST=message_queue

CMD [ "python", "prices_service.py" ]
