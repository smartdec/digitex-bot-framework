from .util import decimal_from_proto, datetime_from_proto

class OrderBook:
    def __init__(self):
        self.bids = None
        self.asks = None

    def best_bid_price(self):
        if self.bids is None:
            return None
        return max(self.bids, default=None)

    def best_ask_price(self):
        if self.asks is None:
            return None
        return min(self.asks, default=None)

    def on_update(self):
        pass

class OrderBookEntry:
    def from_proto(message):
        self = OrderBookEntry()
        self.price = decimal_from_proto(message, 'price')
        self.quantity = decimal_from_proto(message, 'quantity')
        self.entry_time = datetime_from_proto(message.entry_timestamp)
        return self

    def __repr__(self):
        return f'OrderBookEntry(price={self.price}, quantity={self.quantity}, entry_time={self.entry_time})'
