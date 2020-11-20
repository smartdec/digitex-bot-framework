from enum import Enum

from digitex_engine_client import messages_pb2 as proto

class OrderType(Enum):
    MARKET = 1
    LIMIT = 2

    def from_proto(order_type):
        if order_type == proto.TYPE_UNDEFINED:
            return None
        return OrderType(order_type)

    def to_proto(self):
        return self.value

class PositionType(Enum):
    FLAT = 0
    LONG = 1
    SHORT = 2

    def from_proto(order_position):
        return PositionType(order_position)

class OrderSide(Enum):
    BUY = 1
    SELL = 2

    def from_proto(order_side):
        if order_side == proto.SIDE_UNDEFINED:
            return None
        return OrderSide(order_side)

    def to_proto(self):
        return self.value

class OrderDuration(Enum):
    GFD = 1
    GTC = 2
    GTF = 3
    IOC = 4
    FOK = 5

    def from_proto(order_duration):
        if order_duration == proto.DURATION_UNDEFINED:
            return None
        return OrderDuration(order_duration)

    def to_proto(self):
        return self.value

class OrderStatus(Enum):
    PENDING = 1
    ACCEPTED = 2
    REJECTED = 3
    CANCELED = 4
    FILLED = 5
    PARTIAL = 6
    TERMINATED = 7
    EXPIRED = 8
    TRIGGERED = 9

    def from_proto(order_status):
        if order_status == proto.STATUS_UNDEFINED:
            return None
        return OrderStatus(order_status)

    def to_proto(self):
        return self.value
