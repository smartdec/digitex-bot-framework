import asyncio
import datetime
from decimal import Decimal
from functools import wraps

import pytz

from digitex_engine_client import messages_pb2 as proto

def handle_explicit_field_name(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if len(args) == 2:
            obj, field_name = args
            if obj is None:
                return None
            if not hasattr(obj, field_name):
                return None
            if not obj.HasField(field_name):
                return None
            value = getattr(obj, field_name)
        elif len(args) == 1:
            value = args[0]
        else:
            raise TypeError(f'expected at most 2 arguments, got {len(args)}')
        return f(value, **kwargs)
    return wrapper

@handle_explicit_field_name
def decimal_from_proto(proto_decimal):
    return Decimal(proto_decimal.value64).scaleb(-proto_decimal.scale)

def decimal_to_proto(decimal):
    if decimal is None:
        return None
    if not isinstance(decimal, Decimal):
        decimal = Decimal(decimal)
    negative, digits, exponent = decimal.as_tuple()
    value = 0
    for digit in digits:
        value *= 10
        value += digit
    if negative:
        value = -value
    scale = -exponent
    return proto.Decimal(value64=value, scale=scale)

def datetime_from_proto(timestamp):
    if timestamp == 0:
        return None
    timestamp /= 1_000_000
    return datetime.datetime.fromtimestamp(timestamp, tz=pytz.UTC)

def datetime_now_utc():
    return datetime.datetime.now(pytz.UTC)

def round_price(price, step, direction):
    if price is None:
        return None
    remainder = price % step
    if direction == 'down':
        return price - remainder
    elif direction == 'up':
        return price + step - remainder
    elif direction == 'closest':
        remainder = price.remainder_near(step)
        return price - remainder
    else:
        raise ValueError('Unsupported rounding direction: ' + str(direction))

class CombineAsyncIterators:
    def __init__(self, *iters):
        self.iters = iters
        self.queue = []
        self.make_next_future()
        self.nexts = [None] * len(iters)

    def make_next_future(self):
        self.next_future = asyncio.get_event_loop().create_future()

    def install_nexts(self):
        for i, iter in enumerate(self.iters):
            if self.nexts[i] is not None:
                continue
            self.nexts[i] = asyncio.ensure_future(iter.__anext__())
            self.nexts[i].add_done_callback(self.done_callback)

    def done_callback(self, next):
        self.queue.append(next)
        for i in range(len(self.nexts)):
            if self.nexts[i] is next:
                self.nexts[i] = None
        if not self.next_future.done():
            self.next_future.set_result(None)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            if self.queue:
                return self.queue.pop(0).result()
            self.install_nexts()
            await self.next_future
            res = self.queue.pop(0)
            self.make_next_future()
            return res.result()
        except StopAsyncIteration:
            for next in self.nexts:
                if next is not None:
                    next.cancel()
            raise
