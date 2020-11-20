import asyncio
from decimal import Decimal

import uuid

from .trader import Trader
from .trade import Trade
from .util import decimal_from_proto, datetime_from_proto, round_price
from .enums import PositionType, OrderSide, OrderType, OrderDuration, OrderStatus
from .order_book import OrderBook, OrderBookEntry
from .order import Order, Orders
from .tick import Tick
from .currency_pair import CurrencyPair

class Market:
    def __init__(self, /, id, currency_pair, tick):
        self.id = id
        self.trader = Trader(market=self)
        self.trader.orders = Orders(market=self)
        self.order_book = OrderBook()
        self.bot = None
        self.currency_pair = currency_pair
        self.tick = tick
        self.last_trade = None

        self.order_type = Order
        self.scheduled_events = []

    def rounded_spot_price(self, direction='closest'):
        spot_price = self.currency_pair.mark_price
        return round_price(spot_price, self.tick.size, direction)

    def schedule_event(self, event):
        if event not in self.scheduled_events:
            self.scheduled_events.append(event)

    def emit_event(self, event):
        res = event()
        if res is None:
            return
        if asyncio.iscoroutine(res):
            asyncio.create_task(res)
            return
        raise TypeError('Unsupported event return type: ' + type(res))

    def handle_message(self, message):
        which_one = message.WhichOneof('kontent')
        if which_one == 'trader_status_msg':
            self.handle_trader_status_msg(message.trader_status_msg)
        elif which_one == 'trader_balance_msg':
            self.handle_trader_balance_msg(message.trader_balance_msg)
        elif which_one == 'exchange_rate_msg':
            self.handle_exchange_rate_msg(message.exchange_rate_msg)
        elif which_one == 'order_book_msg':
            self.handle_order_book_msg(message.order_book_msg)
        elif which_one == 'order_book_updated_msg':
            self.handle_order_book_updated_msg(message.order_book_updated_msg)
        elif which_one == 'order_status_msg':
            self.handle_order_status_msg(message.order_status_msg, message)
        elif which_one == 'order_filled_msg':
            self.handle_order_status_msg(message.order_filled_msg, message)
        elif which_one == 'order_canceled_msg':
            self.handle_order_canceled_msg(message.order_canceled_msg, message)
        elif which_one == 'leverage_msg':
            self.handle_leverage_msg(message.leverage_msg, message)
        # else:
            # print('Unhandled message:')
            # print(message)

        for event in self.scheduled_events:
            self.emit_event(event)
        self.scheduled_events.clear()

    def handle_mark_price(self, message):
        self.currency_pair.mark_price = decimal_from_proto(message, 'mark_price')
        self.schedule_event(self.currency_pair.on_update)

    def create_order_from_message(self, message):
        return self.order_type(
            price=decimal_from_proto(message, 'price'),
            quantity=decimal_from_proto(message, 'quantity'),
            side=OrderSide.from_proto(message.side),
            type=OrderType.from_proto(message.order_type),
            duration=OrderDuration.from_proto(message.duration),
            market=self,
            id=uuid.UUID(bytes=message.orig_client_id),
        )

    def handle_order(self, message, outer_message=None, forced_status=None):
        id = uuid.UUID(bytes=message.orig_client_id)
        order = self.trader.orders.look_up_by_id(id)
        have_seen_this_order_before = order is not None
        if not have_seen_this_order_before:
            order = self.create_order_from_message(message)

        if hasattr(message, 'status'):
            order.status = OrderStatus.from_proto(message.status)
        elif forced_status is not None:
            order.status = forced_status
        elif not have_seen_this_order_before:
            if decimal_from_proto(message, 'orig_quantity') != order.quantity:
                order.status = OrderStatus.PARTIAL
            else:
                order.status = OrderStatus.ACCEPTED

        if outer_message is not None and outer_message.error_code != 0:
            order.error_code = outer_message.error_code

        statuses_to_keep = (OrderStatus.ACCEPTED, OrderStatus.PARTIAL)
        if have_seen_this_order_before and order.status not in statuses_to_keep:
            self.trader.orders.remove(order)
        elif not have_seen_this_order_before and order.status in statuses_to_keep:
            self.trader.orders.add(order)

        return order, have_seen_this_order_before


    def handle_order_status_msg(self, message, outer_message):
        if outer_message.error_code == 0:
            self.handle_balance(message)
            self.handle_position(message)
            self.handle_order_margin(message)

        order, have_seen_this_order_before = self.handle_order(message, outer_message)
        self.schedule_event(order.on_update)

    def handle_order_filled_message(self, message, outer_message):
        self.handle_position(message)
        self.handle_balance(message)
        self.handle_order_margin(message)

        order, have_seen_this_order_before = self.handle_order(message, outer_message)
        order.quantity = decimal_from_proto(message, 'orig_quantity')
        order.quantity -= decimal_from_proto(message, 'quantity')
        order.quantity -= decimal_from_proto(message, 'dropped_quantity')

        self.schedule_event(order.on_update)

    def handle_order_canceled_msg(self, message, outer_message):
        self.handle_order_margin(message)
        self.handle_mark_price(message)
        self.handle_balance(message)

        self.trader.position.margin = decimal_from_proto(message, 'position_margin')
        self.schedule_event(self.trader.position.on_update)

        status = OrderStatus.from_proto(message.status)

        for order_msg in message.orders:
            order, have_seen_this_order_before = self.handle_order(
                order_msg,
                outer_message,
                forced_status=status
            )
            self.schedule_event(order.on_update)

    def handle_leverage_msg(self, message, outer_message):
        self.handle_leverage(message)
        if outer_message.error_code == 0:
            self.handle_balance(message)
            self.handle_position(message)
            self.handle_order_margin(message)
            self.handle_last_trade(message)

    def handle_last_trade(self, message):
        if self.last_trade is None:
            self.last_trade = Trade()
        self.last_trade.price = decimal_from_proto(message, 'last_trade_price')
        self.last_trade.quantity = decimal_from_proto(message, 'last_trade_quantity')
        self.last_trade.time = datetime_from_proto(message.last_trade_timestamp)

        self.schedule_event(self.last_trade.on_update)

    def handle_position(self, message):
        self.trader.position.contracts = decimal_from_proto(message, 'position_contracts')
        self.trader.position.volume = decimal_from_proto(message, 'position_volume')
        self.trader.position.liquidation_volume = decimal_from_proto(message, 'position_liquidation_volume')
        self.trader.position.bankruptcy_volume = decimal_from_proto(message, 'position_bankruptcy_volume')
        self.trader.position.type = PositionType.from_proto(message.position_type)
        self.trader.position.margin = decimal_from_proto(message, 'position_margin')

        self.schedule_event(self.trader.position.on_update)

    def handle_order_margin(self, message):
        orders = self.trader.orders
        orders.margin = decimal_from_proto(message, 'order_margin')
        orders.buy_margin = decimal_from_proto(message, 'buy_order_margin')
        orders.sell_margin = decimal_from_proto(message, 'sell_order_margin')

        self.schedule_event(orders.on_margins_update)

    def handle_leverage(self, message):
        leverage = message.leverage
        if leverage == 0:
            return
        self.trader.leverage = leverage

        self.schedule_event(self.trader.on_update)

    def handle_balance(self, message):
        self.trader.balance = decimal_from_proto(message, 'trader_balance')
        self.trader.upnl = decimal_from_proto(message, 'upnl')
        self.trader.pnl = decimal_from_proto(message, 'pnl')
        # self.trader.accum_quantity = decimal_from_proto(message, 'accum_quantity')
        self.schedule_event(self.trader.on_update)

    def populate_orderbook(target, source):
        for proto_entry in source:
            entry = OrderBookEntry.from_proto(proto_entry)
            if entry.quantity == 0 and entry.price in target:
                del target[entry.price]
            else:
                target[entry.price] = entry

    def handle_order_book_msg(self, message):
        if self.order_book.bids is not None:
            self.order_book.bids.clear()
            self.order_book.asks.clear()
        else:
            self.order_book.bids = dict()
            self.order_book.asks = dict()
        Market.populate_orderbook(self.order_book.bids, message.bids)
        Market.populate_orderbook(self.order_book.asks, message.asks)

        self.handle_last_trade(message)
        self.handle_mark_price(message)
        self.schedule_event(self.order_book.on_update)

    def handle_order_book_updated_msg(self, message):
        if self.order_book.bids is not None:
            Market.populate_orderbook(self.order_book.bids, message.bid_updates)
            Market.populate_orderbook(self.order_book.asks, message.ask_updates)
            self.schedule_event(self.order_book.on_update)
        else:
            asyncio.create_task(self.bot.client.order_book_request(market_id=self.id))

        self.handle_last_trade(message)
        self.handle_last_trade(message)

    def handle_exchange_rate_msg(self, message):
        if message.currency_pair_id not in self.bot.currency_pairs:
            return
        currency_pair = self.bot.currency_pairs[message.currency_pair_id]

        # Note: this should not use handle_mark_price(), because we're
        # not necesserily updating this market's currency pair.
        currency_pair.mark_price = decimal_from_proto(message, 'mark_price')
        currency_pair.sell_price = decimal_from_proto(message, 'sell_price')
        currency_pair.buy_price = decimal_from_proto(message, 'buy_price')
        currency_pair.unreliable = message.unreliable != 0

        self.schedule_event(currency_pair.on_update)

    def handle_trader_status_msg(self, message):
        self.handle_balance(message)
        self.handle_mark_price(message)
        self.handle_last_trade(message)
        self.handle_order_margin(message)
        self.handle_position(message)
        self.handle_leverage(message)

        for order_msg in message.orders:
            order, have_seen_this_order_before = self.handle_order(order_msg)
            self.schedule_event(order.on_update)

    def handle_trader_balance_msg(self, message):
        self.handle_balance(message)
        self.handle_last_trade(message)
        self.handle_order_margin(message)
        self.handle_position(message)

Market.BTC_USD = Market(
    id=1, currency_pair=CurrencyPair.BTC_USD,
    tick=Tick(size=Decimal('5.00'), price=Decimal('0.1000'), scale=0),
)
Market.ETH_USD = Market(
    id=2, currency_pair=CurrencyPair.ETH_USD,
    tick=Tick(size=Decimal('0.25'), price=Decimal('0.2500'), scale=2),
)
Market.XRPx10000_USD = Market(
    id=3, currency_pair=CurrencyPair.XRP_USD,
    tick=Tick(size=Decimal('1.00'), price=Decimal('0.1000'), scale=0),
)
Market.XAU_USD = Market(
    id=5, currency_pair=CurrencyPair.XAU_USD,
    tick=Tick(size=Decimal('0.50'), price=Decimal('0.0500'), scale=1),
)
Market.SPY = Market(
    id=6, currency_pair=CurrencyPair.SPY,
    tick=Tick(size=Decimal('0.1000'), price=Decimal('0.1000'), scale=4),
)
Market.EUR_USD = Market(
    id=7, currency_pair=CurrencyPair.EUR_USD,
    tick=Tick(size=Decimal('0.0001'), price=Decimal('0.1000'), scale=4),
)
Market.AMZN = Market(
    id=8, currency_pair=CurrencyPair.AMZN,
    tick=Tick(size=Decimal('1.0000'), price=Decimal('0.1000'), scale=4),
)
Market.BTC_USD1 = Market(
    id=9, currency_pair=CurrencyPair.BTC_USD,
    tick=Tick(size=Decimal('1.00'), price=Decimal('0.1000'), scale=0),
)
Market.USD_JPY = Market(
    id=10, currency_pair=CurrencyPair.USD_JPY,
    tick=Tick(size=Decimal('0.0100'), price=Decimal('0.0100'), scale=4),
)
Market.USD_RUB = Market(
    id=11, currency_pair=CurrencyPair.USD_RUB,
    tick=Tick(size=Decimal('0.0100'), price=Decimal('0.0100'), scale=4),
)
Market.FB = Market(
    id=12, currency_pair=CurrencyPair.FB,
    tick=Tick(size=Decimal('0.0100'), price=Decimal('0.0100'), scale=4),
)
Market.AAPL = Market(
    id=13, currency_pair=CurrencyPair.AAPL,
    tick=Tick(size=Decimal('0.0100'), price=Decimal('0.0100'), scale=4),
)
