"""
This module contains the main FastAPI application and its endpoints.

The application is a simple API endpoint that returns the top N
cryptocurrencies based on their market capitalization. The data is
fetched from the CoinMarketCap and CryptoCompare APIs and processed
based on the parameters provided by the user.
"""
import csv
import json
import logging
import uuid

from io import StringIO
from typing import List, Optional

import pika
import uvicorn

from fastapi import FastAPI, Query


logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.WARNING,
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

app = FastAPI()


class PricesRpcClient:
    """A RPC client that sends a message to the Pricing Service."""

    def __init__(self):
        """Initializes the RPC client."""
        self.response = None
        self.corr_id = None

        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='message_queue')
        )
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(queue='')
        self.callback_queue = result.method.queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True,
        )

    def on_response(self, ch, method, props, body):
        """Callback function that prints the message from the queue."""
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, limit: int) -> str:
        """Sends a message to the message queue."""
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='prices_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=str(limit)
        )
        while self.response is None:
            self.connection.process_data_events(time_limit=None)
        return self.response.decode()


class RankingRpcClient:
    """A RPC client that sends a message to the Ranking Service."""

    def __init__(self):
        """Initializes the RPC client."""
        self.response = None
        self.corr_id = None

        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='message_queue')
        )
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(queue='')
        self.callback_queue = result.method.queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True,
        )

    def on_response(self, ch, method, props, body):
        """Callback function that prints the message from the queue."""
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, symbols: List[str]) -> str:
        """Sends a message to the message queue."""
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='ranking_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=str(symbols)
        )
        while self.response is None:
            self.connection.process_data_events(time_limit=None)
        return self.response.decode()


def json_to_csv(json_data: dict) -> str:
    """Converts a JSON object to a CSV string."""
    csv_data = StringIO()
    headers = list(json_data[0].keys())
    writer = csv.DictWriter(csv_data, fieldnames=headers)
    writer.writeheader()
    writer.writerows(json_data)
    cvs_string = csv_data.getvalue()
    return cvs_string


@app.get("/")
def get_crypto_prices(
    limit: int = Query(
        ...,
        ge=1,
        description="Number of top cryptocurrency types to return",
    ),
    datetime: Optional[str] = Query(
        'NOW',
        description="Timestamp of the returned information (default: NOW)",
    ),
    format: Optional[str] = Query(
        'CSV', description="Output format [JSON|CSV] (default: CSV)"
    )
):
    """Returns ranked prices of the top N cryptocurrencies."""

    if datetime == 'NOW':
        ranking_rpc_client = RankingRpcClient()
        ranked_symbols = ranking_rpc_client.call(limit)

        prices_rpc_client = PricesRpcClient()
        response = prices_rpc_client.call(ranked_symbols)
        response = json.loads(response)

    else:
        return {
            "error": "This service does not support historical data YET!"
        }, 501

    if format == 'CSV':
        response = json_to_csv(response)
    elif format == 'JSON':
        pass
    else:
        return {"error": "Invalid format. Format must be CSV or JSON"}, 403

    return response, 200


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6667)
