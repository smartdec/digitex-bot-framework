from .position import Position

class Trader:
    def __init__(self, /, market):
        self.market = market
        self.balance = None
        self.leverage = None
        self.position = Position()
        self.orders = None
        self.pnl = None
        self.upnl = None

    async def change_leverage(self, leverage):
        await self.market.bot.client.change_leverage_all(
            market_id=self.market.id,
            leverage=leverage,
        )

    def on_update(self):
        pass
