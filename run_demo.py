import asyncio
import random
import datetime
from trading.strategy import Strategy
from trading.execution import PaperExecutor

class DemoExecutor(PaperExecutor):
    def __init__(self, event_queue: asyncio.Queue):
        super().__init__(event_queue)
        self.fills_list = []

    async def place_market_order(self, symbol: str, side: str, quantity: int, price: float = None):
        fill = await super().place_market_order(symbol, side, quantity, price)
        self.fills_list.append(fill)
        return fill

async def produce_synthetic_ticks(queue: asyncio.Queue, n: int = 200, base_price: float = 10.0):
    """Produce n synthetic ticks that oscillate around base_price."""
    ts = datetime.datetime.now()
    price = base_price
    for i in range(n):
        # small random walk with occasional jumps
        price += random.uniform(-0.1, 0.1)
        if i % 50 == 0:
            price += random.uniform(-0.8, 0.8)
        tick = {
            'type': 'tick',
            'datetime': str(ts + datetime.timedelta(milliseconds=10 * i)),
            'open': round(price + random.uniform(-0.02, 0.02), 4),
            'high': round(price + random.uniform(0, 0.05), 4),
            'low': round(price - random.uniform(0, 0.05), 4),
            'close': round(price, 4),
            'volume': random.randint(1, 1000)
        }
        await queue.put(tick)
        # very short sleep to simulate high-frequency ticks
        await asyncio.sleep(0.001)

async def main():
    queue = asyncio.Queue()
    executor = DemoExecutor(queue)
    strategy = Strategy(queue, executor)

    # start strategy
    strategy_task = asyncio.create_task(strategy.run())
    # produce ticks
    await produce_synthetic_ticks(queue, n=400, base_price=10.0)
    # give some time for strategy to process remaining events
    await asyncio.sleep(0.5)

    # stop strategy gracefully
    strategy.stop()
    await asyncio.sleep(0.1)
    # print summary
    print("Simulation finished")
    print(f"Total fills: {len(executor.fills_list)}")
    for f in executor.fills_list:
        print(f"{f['order_id']}: {f['side'].upper()} {f['quantity']} @ {f['price']}")
    print("Final positions:", await executor.get_positions())

if __name__ == '__main__':
    asyncio.run(main())
