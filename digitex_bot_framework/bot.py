import asyncio
import logging

import digitex_engine_client

from .util import CombineAsyncIterators

logger = logging.getLogger('digitex_bot_framework')

class Bot:
    client_class = digitex_engine_client.WsClient

    def __init__(self, *args, **kwargs):
        self.markets = dict()
        self.currency_pairs = dict()

        self.client = None
        self.client_args = args
        self.client_kwargs = kwargs

        asyncio.ensure_future(self.listen())

    async def ensure_client(self):
        if self.client is None:
            await self.connect()

    async def connect(self):
        if self.client is not None:
            # Attempt to close it, but don't bother too much.
            try:
                await self.client.close()
            except:
                logger.exception('Failed to tear down the previous connection')

        if 'host' in self.client_kwargs:
            logger.info('Connecting to %s', self.client_kwargs['host'])
        else:
            logger.info('Connecting')

        try:
            self.client = self.client_class(*self.client_args, **self.client_kwargs)
            await self.client.ping(market_id=1)
        except:
            logger.exception('Failed to connect')
            raise

    async def add_market(self, market):
        await self.ensure_client()
        logger.info('Adding market %s', market)
        self.markets[market.id] = market
        market.bot = self
        if market.currency_pair.id not in self.currency_pairs:
            self.add_currency_pair(market.currency_pair)
        await self.client.subscribe(market_id=market.id)
        await self.client.order_book_request(market_id=market.id)
        await self.client.get_trader_status(market_id=market.id)

    def add_currency_pair(self, currency_pair):
        logger.info('Adding currency pair %s', currency_pair)
        self.currency_pairs[currency_pair.id] = currency_pair
        self.currency_pairs[currency_pair.code] = currency_pair

    def run(self):
        asyncio.get_event_loop().run_forever()

    def handle_message(self, message):
        if message.market_id not in self.markets:
            return
        market = self.markets[message.market_id]
        market.handle_message(message)

    async def listen(self):
        await self.ensure_client()
        while True:
            trading_listener = await self.client.subscribe_to_trading_events()
            market_data_listener = await self.client.subscribe_to_market_data_events()
            async for message in CombineAsyncIterators(trading_listener, market_data_listener):
                self.handle_message(message)
            logger.warning('End of event stream, reconnecting')
            await self.connect()
            markets = self.markets.copy()
            for market in markets.values():
                await self.add_market(market)
