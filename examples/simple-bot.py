import asyncio
import random
from decimal import Decimal

from digitex_bot_framework import *

market = Market.BTC_USD
trader = market.trader

async def place_an_order():
    last_trade = market.last_trade
    rounded_spot_price = market.rounded_spot_price()
    if rounded_spot_price is None or last_trade is None:
        print('Skipped placing an order due to unknown price')
        return

    quantity = random.randint(100, 1000)

    if rounded_spot_price < last_trade.price:
        side = OrderSide.SELL
    elif rounded_spot_price > last_trade.price:
        side = OrderSide.BUY
    else:
        if trader.position.type == PositionType.LONG:
            side = OrderSide.SELL
        elif trader.position.type == PositionType.SHORT:
            side = OrderSide.BUY
        else:
            side = random.choice([OrderSide.BUY, OrderSide.SELL])

    print(f'Placing an order for {quantity} at {rounded_spot_price}')
    order = Order(price=rounded_spot_price, quantity=quantity, side=side)
    await trader.orders.place(order)

async def on_currency_pair_update():
    if market.last_trade is not None and market.rounded_spot_price() != market.last_trade.price:
        # Better act fast!
        await place_an_order()

market.currency_pair.on_update = on_currency_pair_update

async def main():
    bot = Bot(
        host='ws.testnet.digitexfutures.com',
        token='your-token-here'
    )

    await bot.add_market(market)

    while True:
        await asyncio.sleep(5)
        await place_an_order()

asyncio.run(main())
