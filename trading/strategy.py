import asyncio

class Strategy:
    """Example event-driven strategy.
    Subscribes to market ticks from the event queue and places simulated orders.
    """
    def __init__(self, event_queue: asyncio.Queue, executor):
        self.event_queue = event_queue
        self.executor = executor
        self._running = False
        self.last_price = None

    async def run(self):
        self._running = True
        while self._running:
            event = await self.event_queue.get()
            if event.get('type') == 'tick':
                await self.on_tick(event)
            elif event.get('type') == 'fill':
                await self.on_fill(event)

    async def on_tick(self, tick):
        price = tick.get('close')
        if self.last_price is None:
            self.last_price = price
            return
        # naive strategy: if price drops >0.5% from last seen, buy 1; if rises >0.5% sell 1
        change = (price - self.last_price) / self.last_price
        if change <= -0.005:
            # buy
            await self.executor.place_market_order(symbol='SAMPLE', side='buy', quantity=1, price=price)
            self.last_price = price
        elif change >= 0.005:
            await self.executor.place_market_order(symbol='SAMPLE', side='sell', quantity=1, price=price)
            self.last_price = price
        else:
            self.last_price = price

    async def on_fill(self, fill):
        # user can add logging, analytics
        pass

    def stop(self):
        self._running = False
