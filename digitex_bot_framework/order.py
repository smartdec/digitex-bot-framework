import uuid

from .util import decimal_to_proto
from .enums import OrderType, OrderDuration, OrderStatus

class Order:
    def __init__(
        self, /,
        price, quantity, side,
        type=OrderType.LIMIT, duration=OrderDuration.GTC,
        market=None, id=None
     ):
        self.price = price
        self.quantity = quantity
        self.side = side
        self.type = type
        self.duration = duration
        self.market = market
        self.id = id

        self.status = OrderStatus.PENDING
        self.error_code = None

    def on_update(self):
        pass

    async def cancel(self):
        # Remove it from the list, but leave it in the
        # by-id dictionary. We'll purge it from there
        # once we receive acknowledgement from the engine.
        list.remove(self.market.trader.orders, self)
        await self.market.bot.client.cancel_order(
            market_id=self.market.id,
            prev_client_id=self.id.bytes,
        )

    def __repr__(self):
        s = f'Order(id={self.id}, price={self.price}, quantity={self.quantity}, side={self.side}'
        if self.type is not OrderType.LIMIT:
            s += f', type={self.type}'
        if self.duration is not OrderDuration.GTC:
            s += f', duration={self.duration}'
        s += ')'
        return s


class Orders(list):
    def __init__(self, /, market):
        self.market = market
        self.by_id = dict()

        self.margin = None
        self.buy_margin = None
        self.sell_margin = None

    def on_margins_update(self):
        pass

    def add(self, order):
        assert order.id not in self.by_id
        self.by_id[order.id] = order
        self.append(order)

    def remove(self, order):
        del self.by_id[order.id]
        if order in self:
            super().remove(order)

    def look_up_by_id(self, id):
        return self.by_id.get(id, None)

    async def place(self, order):
        if order.market is None:
            order.market = self.market
        elif self.market is not self.market:
            raise ValueError('This order is for a different market')

        if order.id is None:
            order.id = uuid.uuid4()

        self.add(order)

        await self.market.bot.client.place_order(
            client_id=order.id.bytes,
            market_id=self.market.id,
            order_type=order.type.to_proto(),
            side=order.side.to_proto(),
            duration=order.duration.to_proto(),
            price=decimal_to_proto(order.price),
            quantity=decimal_to_proto(order.quantity)
        )

    async def cancel_all(self):
        all_orders = self[:]
        for order in all_orders:
            await order.cancel()
