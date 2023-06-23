"""
This script fetches the current prices of the cryptocurrencies and
stores them in a CSV file. The script runs every minute.
"""
import json
import logging
import os

from typing import Dict, List, Optional, Union

import pika
import requests


PRICES_API_KEY = os.environ.get('PRICES_API_KEY')
PRICES_API_URL = (
    'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
)

MESSAGE_QUEUE_HOST = os.environ.get('MESSAGE_QUEUE_HOST')

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.WARNING,
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


parameters = {'aux': 'date_added', 'convert': 'USD'}
headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': PRICES_API_KEY}

APISymbol = Dict[str, List]


connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='message_queue')
)
logger.warning(connection)
channel = connection.channel()
logger.warning(channel)
channel.queue_declare(queue='prices_queue')


def get_price_from_symbol(symbol: APISymbol) -> float:
    """Return the price from a symbol object.

    The symbol object structure is defined by the coinmarketcap.
    """
    return symbol['quote']['USD']['price']


def get_ranked_crypto(rank: int, symbol: str, price: float) -> dict:
    """Return a ranked cryptocurrency."""
    return {'Rank': rank, 'Symbol': symbol, 'Price USD': price}


def on_request(ch, method, props, body):
    """Callback function to fetch prices of symbols and publish them."""
    symbol_rankings_str = body.decode()
    symbol_rankings = symbol_rankings_str.split(',')

    parameters['symbol'] = symbol_rankings_str

    response = requests.get(PRICES_API_URL, headers=headers, params=parameters)

    if response.status_code == 200:
        data = response.json()['data']
        logger.warning(data)

        ranked_symbols_prices = []
        for rank, symbol in enumerate(symbol_rankings, 1):
            try:
                ranked_symbols_prices.append(
                    get_ranked_crypto(
                        rank, symbol, get_price_from_symbol(data[symbol])
                    )
                )
            except KeyError:
                logger.error(
                    'Symbol %s not found in the response: %s',
                    symbol,
                    response.text,
                )

        msg = json.dumps(ranked_symbols_prices)

        ch.basic_publish(
            exchange='',
            routing_key=props.reply_to,
            body=msg,
            properties=pika.BasicProperties(
                correlation_id=props.correlation_id
            ),
        )
    else:
        logger.error(
            'Error fetching cryptocurrencies prices: %s', response.text
        )

    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='prices_queue', on_message_callback=on_request)

logger.warning('Price service is running. Waiting for RPC requests...')
channel.start_consuming()
