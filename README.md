# Top Cryptocurrency Price List
For this task, you will prototype a price list service for top crypto assets.
The service should expose an HTTP endpoint, which displays an up-to-date list of top assets and
their current prices in USD when fetched.
* The endpoint should support limit parameter which indicates how many top cryptocurrency
types should be returned.
* The endpoint should support datetime parameter which indicates the timestamp of the
returned information. An optional parameter, the default is NOW. If the request is without a
defined timestamp, the information should be the most up-to-date from the external
services (not from the historical database).
* The output should be either JSON or CSV compatible, defined by the parameter format.

Example call should look somehow like this:
```
$ curl http://localhost:6667?limit=200
Rank, Symbol, Price USD,
1, BTC, 6634.41,
2, ETH, 370.237,
3, XRP, 0.471636,
... ... ...
200, DCN, 0.000269788,
```

The ranking and price information should always be up-to-date. For example, let's say that BTC
ranking changes from #3 to #6, the list should reflect that change. The historical information
should be preserved and accessible with the help of the datetime parameter.
Send us only a link to your GitHub or GitLab repo.

## How to use the app
First we need to deploy the app:
```bash
docker-compose up --build
```
The `--build` option builds the docker images. That command also deploys the pricing, the ranking service and the queue messages service that allows RCP communication between components. Consecutives deployments of the app and services can be done by just typing `docker-compose up` if the codebase has not changed.

Once the depployment has finished you could see logs messages like this:
```
...
price_list-ranking_service-1  | XXXX-XX-XX XX:XX:XX WARNING  Ranking service is running. Waiting for RPC request...

...
price_list-prices_service-1   | YYYY-YY-YY YY:YY:YY WARNING  Price service is running. Waiting for RPC requests...

...
```
The app is ready to listening for request in the local host, `localhost`, on the port `6667`:
```bash

curl 'http://localhost:6667/?limit=1'
"Rank,Symbol,Price USD\r\n1,BTC,30086.133837815396\r\n"
curl 'http://localhost:6667/?limit=1&format=JSON'
[{"Rank":1,"Symbol":"BTC","Price USD":30096.408526724717}]%
```

## Architectural model
The solution for this exercise consists of 3 services that run independently, as requested:
- Pricing Service
- Ranking Service
- HTTP-API Service

In addition, there is a RabbitMQ messaging queue service for inter-service communication.

The HTTP-API service exposes the http endpoint that returns the list of top N cryptocurrencies (cryptos from no on) and their prices. The ranking service serves up-to-date top N cryptos. The pricing service serves the up-to-date prices of those top N cryptos.

The proccess is as follows:
1. A `GET` request is done to the http-api service with the number of cryptocurrencies to fetch, `limit=N` parameter.
2. The http-api service connects with the ranking service asking for the `N` ranked cryptos.
3. The ranking service fetches thet top `N` cryptos from *cryptocompare* (crypto provider) and serves a message with their symbols.
4. The http-api receives the list of symbols and asks for their prices to the prices service.
5. The prices service fetches the prices of the `N` cryptos from *cryptomarketcap* (crypto provider) and serves a message with the ranking index, the symbol and the price of the cryptos.
6. The http-api service recive the message with the ranking, symbol and price of the cryptos, transform it to `CSV` or `JSON` format and serves it.

All the inter-service communication is done with Remote Procedure Calls. The main reason for chosing this was simplicity. Besides, it was obvious to me that in order to avoid large volumes of data being transferred from the ranking and prices providers we had to ask first for the top N and the only the N prices.

However, implementing an asynchronous event-driven architecture (see below for more details), where the pricing and ranking services are continuously fetching information from the crypto providers, would have reduce the waiting times because the up-to-date information is already fetch.

## TODO and technical debt
- Parameter `datetime` is supported only for the `NOW` value. The functionality of fetching historical was not completed due to lack of time.
- Add a cache system with redis. Cache systems can be implemented for the API get method and for the RCP to the pricing and ranking services from the app. I didn't manage to hit the deadline with this either.
- Testing!! There are a few unit tests for functions that does not require mock any API call, just as an example on how and where to create tests. However, it is impossible to ensure the app actually does what it claims without thorough tests:
	- At least a test to check all the possible cases the API offers: CSV or JSON format, returns number of coins equal to limit provided, API fetch current prices and ranking or historical ones, and much more!. 
- RankingRpcClient and PricesRpcClient should be move to another file outside the app main file. In addition, because most of the code is similar, we should see to create an abstract class and overload the call method to avoid code duplicity.
- API keys are hardcoded within the docker files. This was the easy thing to do at first while implementing. However, leaving them like this will cause everyone using the app as it is now will use the same API keys. Values for the API keys should be provided by a configuration file or even better, in a vaulting system.
- Add healthchecks to services to make sure dependent services are deployed after their dependecies. For example, the pricing and the ranking services depend on the RabbitMQ service. This is specified as such in the docker-compose file, however, due to the lack of the RabbitMQ service healthcheck, this dependency is not respected. So, the princing and the ranking services keeps trying to deploy serveral times until the messaging server is ready.
- Implement a event-driven architecture. Once the services were completed I realise there was another, probably better, approach by using message queues and event-driven architecture:
	- **Pricing Service**: Whenever there is an update in pricing data, it publishes an event to a message queue. The service checks every minute (refreshing rate of the *coinmarketcap* API endpoint that serve current ranking) for updated prices.
	- **Ranking Service**: Similarly, whenever there is an update in ranking data, it publishes an event to another message queue. The service checks every minute (refreshing rate of the *cryptocompare* API endpoint that serve current ranking) for updated ranking.
	- **HTTP-API Service**: This service subscribes to the message queues and listens for events. It maintains a cache of the latest pricing and ranking data. Whenever it receives an event, it updates the corresponding data in its cache.
- Some code quality utilities are missing. Good practices writing code are essential and we should enforce them. A git hook with pre-commit should be install to run black (formatter) and flake8 (linter) over the code before being commited and pushed.
