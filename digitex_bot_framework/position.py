class Position:
    def __init__(self):
        self.contracts = None
        self.volume = None
        self.liquidation_volume = None
        self.bankruptcy_volume = None
        self.type = None
        self.margin = None

    def on_update(self):
        pass
