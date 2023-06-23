"""This module contains the RankingRpcClient class."""
import uuid
import pika


class RankingRpcClient:
    """A RPC client that sends a message to the Ranking Service
    through the message queue."""

    def __init__(self):
        """Initializes the RPC client."""
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='message_queue')
        )
        self.response = None
        self.corr_id = None

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
            routing_key='ranking_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=str(limit)
        )
        while self.response is None:
            self.connection.process_data_events(time_limit=None)
        return self.response.decode()
