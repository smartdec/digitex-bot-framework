import asyncio

from digitex_bot_framework import *

market = Market.BTC_USD

order = None
side = None

async def place_order():
    global order, side
    side = OrderSide.SELL if side is OrderSide.BUY else OrderSide.BUY
    order = Order(price=None, quantity=1000, side=side, type=OrderType.MARKET)
    await market.trader.orders.place(order)

async def on_order_update(this_order):
    global order
    print('Order', this_order.id, 'is', this_order.status)
    if this_order is not order:
        return
    if order.status is OrderStatus.REJECTED:
        await asyncio.sleep(1)
        await place_order()
    elif order.status in (OrderStatus.FILLED, OrderStatus.PARTIAL):
        await place_order()

Order.on_update = on_order_update

async def main():
    bot = Bot(
        host='ws.testnet.digitexfutures.com',
        token='your-token-here',
    )
    await bot.add_market(market)
    await place_order()

asyncio.ensure_future(main())
asyncio.get_event_loop().run_forever()
