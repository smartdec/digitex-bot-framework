import asyncio

from digitex_bot_framework import *

market = Market.BTC_USD
trader = market.trader
order_book = market.order_book

order = None

async def place_order():
    global order
    while market.rounded_spot_price() is None or trader.position.type is None:
        print('Waiting for spot price or position...')
        await asyncio.sleep(1)
    if trader.position.type == PositionType.LONG:
        side = OrderSide.SELL
        price = order_book.best_ask_price()
    else:
        side = OrderSide.BUY
        price = order_book.best_bid_price()
    if price is not None:
        order = Order(price=price, quantity=4, side=side)
        await trader.orders.place(order)

async def on_order_book_update():
    global order
    if order is None:
        return
    if order.side == OrderSide.BUY:
        if order_book.best_bid_price() != order.price:
            await trader.orders.cancel_all()
    else:
        if order_book.best_ask_price() != order.price:
            await trader.orders.cancel_all()

order_book.on_update = on_order_book_update

async def on_order_update(this_order):
    global order
    print('Order', this_order.id, 'is', this_order.status)
    if this_order is not order:
        return
    if order.status in (OrderStatus.FILLED, OrderStatus.CANCELED):
        await place_order()
    elif order.status is OrderStatus.REJECTED:
        await asyncio.sleep(1)
        await place_order()

Order.on_update = on_order_update

async def main():
    bot = Bot(
        host='ws.testnet.digitexfutures.com',
        token='your-token-here'
    )
    await bot.add_market(market)
    await place_order()

asyncio.ensure_future(main())
asyncio.get_event_loop().run_forever()
