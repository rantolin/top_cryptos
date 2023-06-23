"""
This script fetches the current top crypto currencies by 24-hour
volume from CoinMarketCap.
"""
import logging
import os

import requests
import pika


API_KEY = os.environ.get('API_KEY')
API_URL = 'https://min-api.cryptocompare.com/data/top/totalvolfull'
PAGE_SIZE = 100

MESSAGE_QUEUE_HOST = os.environ.get('MESSAGE_QUEUE_HOST')

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.WARNING,
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': API_KEY}
parameters = {'tsym': 'USD'}

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='message_queue')
)
channel = connection.channel()
channel.queue_declare(queue='ranking_queue')


def get_number_pages(limit: int, page_size: int = PAGE_SIZE) -> int:
    """Returns the number of pages to fetch.

    :param limit: The total number of cryptos to fetch.
    :param page_size: The number of cryptos to fetch per page.
    :return: The number of pages to fetch.
    """
    return (limit + page_size - 1) // page_size


def get_limit_per_page(
    page: int, total_limit: int, page_size: int = PAGE_SIZE
) -> int:
    """Returns the limit of cryptos to fetch given the page number.

    :param page: The page number.
    :param total_limit: The total number of cryptos to fetch.
    :param page_size: The number of cryptos to fetch per page.
    :return: The limit of cryptos to fetch.
    """
    if (1 + page) * page_size > total_limit:
        limit = total_limit % page_size
        if limit == 0:
            limit = page_size
        return limit

    return page_size


def on_request(ch, method, props, body):
    """Callback function to fetch ranked symbols and publish them."""
    limit = int(body.decode())

    num_pages = get_number_pages(limit)

    symbols = []
    for page in range(num_pages):
        parameters['page'] = page
        parameters['limit'] = get_limit_per_page(page, limit)

        response = requests.get(API_URL, headers=headers, params=parameters)

        if response.status_code == 200:
            data = response.json()
            symbols += [coin['CoinInfo']['Name'] for coin in data['Data']]

        else:
            logger.error(
                'Error fetching ranked cryptocurrencies for page <%s>.', page
            )

    msg = ','.join(symbols)

    ch.basic_publish(
        exchange='',
        routing_key=props.reply_to,
        body=msg,
        properties=pika.BasicProperties(
            correlation_id=props.correlation_id
        ),
    )

    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='ranking_queue', on_message_callback=on_request)

logger.warning('Ranking service is running. Waiting for RPC request...')
channel.start_consuming()
