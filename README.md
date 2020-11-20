# Digitex Bot Framework

## Startup

The exact APIs used to initialize a bot has not been fleshed out yet.
For now, you do it like this:

```python
import digitex_bot_framework

bot = digitex_bot_framework.Bot(host=..., token=...)
```

Then, add one or more markets you're going to trade on:

```python
market = digitex_bot_framework.Market.BTC_USD
await bot.add_market(market)
```

That's it, from there on you can start your trading.

## API

You can trade on one or more markets, represented by the `Market` objects.
* `Market.BTC_USD`
* `Market.ETH_USD`
* `Market.XRPx10000_USD`
* `Market.XAU_USD`
* `Market.AMZN`
* `Market.BTC_USD1`

From a market, you can get to:

* `market.bot`, a reference back to the bot
* `market.tick`
    * `tick.size`, the size of one tick in the quote currency
    * `tick.price`, the price of one tick in the native currency (DGTX)
* `market.currency_pair`
* `market.rounded_spot_price()`, the current spot price (`market.currency_pair.mark_price`),
  rounded to the market's tick size. You can pass a `direction` argument, which should be
  either `up`, `down`, or `closest` (the default)
* `market.order_book`
* `market.last_trade`
    * `last_trade.price`
    * `last_trade.quantity`
    * `last_trade.time`
* `market.trader`

## Currency pair

There are a bunch of currency pairs pre-declared, such as `CurrencyPair.BTC_USD`, and
you can always get the one to use with a particular market as `market.currency_pair`.

A currency pair has:
* `currency_pair.code`, a short string identifying the currency pair (e.g. "BTC/USD")
* `currency_pair.mark_price`, `currency_pair.sell_price`, and `currency_pair.buy_price`, 
  the latest spot price values (these will initially be `None` until price info
  is received)
* `currency_pair.on_update()`, a hook you can use to listen for spot price changes

## Order book

You can get to the order book from a market using `market.order_book`.

An order book has:
* `order_book.bids`, `order_book.asks`, dictionaries mapping prices to order
  book entries (both of these dictionaries will initially be `None`)
* `order_book.best_bid_price()`, `order_book.best_ask_price()`, the best bid
  and ask prices in the order book (will be `None` if there's no such price)
* `order_book.on_update()`, a hook you can use to listen for order book updates

Each order book entry has:
* `order_book_entry.price`
* `order_book_entry.quantity`
* `order_book_entry.entry_time`

## Trader

The trader objects represents properties of the individual trader (you), as
opposed to general properties of the market. You can get to the trader from
a market using `market.trader`.

The trader has:
* `trader.balance`, `trader.pnl`, `trader.upnl`
* `trader.position`
* `trader.orders`
* `trader.leverage`, `await trader.change_leverage()`
* `trader.on_update()`

## Position

* `position.contracts`
* `position.volume`
* `position.liquidation_volume`
* `position.bankruptcy_volume`
* `position.margin`
* `position.type`, which can be `None` (unknown), `PositionType.FLAT`,
  `PositionType.LONG`, and `PositionType.SHORT`
* `position.on_update()`


## Orders

The `Orders` class is a collection of trader's orders. It addtionally provides
the following APIs:
* `orders.margin`, `orders.buy_margin`, `orders.sell_margin`
* `async orders.place(order)`
* `async orders.cancel_all()`
* `orders.on_margins_update`

Each order has the following properties:
* `order.price`
* `order.quantity`
* `order.side`, either `OrderSide.BUY` or `OrderSide.SELL`
* `order.type`, either `OrderType.LIMIT` (the default) or`OrderType.MARKET`
* `order.duration`, which you should probably leave at `OrderDuration.GTC`
* `order.status`
* `order.error_code`

Create an order by calling its constructor, then placing it into `orders`:

```python
order = Order(price=..., quantity=..., side=...)
await market.trader.orders.place(order)
```
