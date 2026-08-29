import asyncio

class PaperExecutor:
    """A very small simulated executor: places market orders and immediately returns fills.
    Publishes fill events to the provided event queue.
    """
    def __init__(self, event_queue: asyncio.Queue):
        self.event_queue = event_queue
        self.order_id = 0
        self.positions = {}

    async def place_market_order(self, symbol: str, side: str, quantity: int, price: float = None):
        self.order_id += 1
        oid = f"ORD{self.order_id}"
        # simulate immediate fill
        fill = {
            'type': 'fill',
            'order_id': oid,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
        }
        # update positions
        pos = self.positions.get(symbol, 0)
        if side.lower() == 'buy':
            pos += quantity
        else:
            pos -= quantity
        self.positions[symbol] = pos
        await self.event_queue.put(fill)
        return fill

    async def get_positions(self):
        return self.positions
