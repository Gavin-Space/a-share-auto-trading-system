import asyncio
import random
import datetime
import csv
from trading.strategy import Strategy
from trading.execution import PaperExecutor

class AccountExecutor(PaperExecutor):
    """Paper executor that also tracks account cash, positions, fees and calculates realized/unrealized P&L.
    Trades are recorded to self.trades and exported to a CSV at the end.
    """
    def __init__(self, event_queue: asyncio.Queue, initial_cash: float = 100000.0, fee_rate: float = 0.0003):
        super().__init__(event_queue)
        self.trades = []
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.fee_rate = fee_rate
        # positions: symbol -> {'qty': int, 'avg_price': float}
        self.positions = {}
        # last seen market price per symbol for unrealized P&L
        self.last_price = {}

    async def place_market_order(self, symbol: str, side: str, quantity: int, price: float = None):
        # Note: PaperExecutor.place_market_order will put a basic 'fill' event into the queue. We'll extend it.
        # Use provided price if given, otherwise fallback to last known price.
        if price is None:
            price = self.last_price.get(symbol, 0.0)
        # call base to create a simple fill structure (and position update there)
        fill = await super().place_market_order(symbol, side, quantity, price)

        value = price * quantity
        fee = value * self.fee_rate
        realized = 0.0

        sym_pos = self.positions.get(symbol, {'qty': 0, 'avg_price': 0.0})
        prev_qty = sym_pos['qty']
        prev_avg = sym_pos['avg_price']

        if side.lower() == 'buy':
            # increase position and update average price
            new_qty = prev_qty + quantity
            if new_qty != 0:
                new_avg = (prev_avg * prev_qty + price * quantity) / new_qty
            else:
                new_avg = 0.0
            sym_pos['qty'] = new_qty
            sym_pos['avg_price'] = new_avg
            # cash decreases by cost + fee
            self.cash -= (value + fee)
            # buying does not realize P&L
            realized = 0.0
        else:  # sell
            # decrease position; if closing from long, realize profit
            if prev_qty >= quantity:
                # normal close or partial close
                realized = (price - prev_avg) * quantity - fee
                sym_pos['qty'] = prev_qty - quantity
                # avg_price unchanged for remaining qty
            else:
                # selling more than current long -> close existing then open short for remainder
                closed_qty = prev_qty
                realized = (price - prev_avg) * closed_qty - fee
                short_qty = quantity - closed_qty
                sym_pos['qty'] = -short_qty
                sym_pos['avg_price'] = price  # average price for short position
            # cash increases by proceeds minus fee
            self.cash += (value - fee)

        self.positions[symbol] = sym_pos
        # record trade
        record = {
            'order_id': fill['order_id'],
            'datetime': datetime.datetime.utcnow().isoformat(),
            'symbol': symbol,
            'side': side.lower(),
            'quantity': quantity,
            'price': price,
            'fee': fee,
            'realized': realized,
            'cash': self.cash
        }
        self.trades.append(record)
        # publish an enhanced fill event (includes accounting fields)
        await self.event_queue.put({'type': 'fill', **record})
        return fill

    async def update_market_price(self, symbol: str, price: float):
        self.last_price[symbol] = price

    def unrealized_pnl(self):
        total = 0.0
        for s, pos in self.positions.items():
            last = self.last_price.get(s, None)
            if last is None:
                continue
            total += pos['qty'] * (last - pos['avg_price'])
        return total

    def nav(self):
        return self.cash + self.unrealized_pnl()

    def export_trades_csv(self, path: str = 'trades.csv'):
        if not self.trades:
            return
        keys = ['order_id', 'datetime', 'symbol', 'side', 'quantity', 'price', 'fee', 'realized', 'cash']
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in self.trades:
                writer.writerow(r)


async def produce_synthetic_ticks(queue: asyncio.Queue, executor: AccountExecutor | None = None, n: int = 200, base_price: float = 10.0):
    """Produce n synthetic ticks that oscillate around base_price.
    If executor is provided, update executor.last_price for symbol 'SAMPLE'.
    """
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
        if executor is not None:
            await executor.update_market_price('SAMPLE', tick['close'])
        # very short sleep to simulate high-frequency ticks
        await asyncio.sleep(0.001)


async def main():
    queue = asyncio.Queue()
    executor = AccountExecutor(queue, initial_cash=100000.0, fee_rate=0.0003)
    strategy = Strategy(queue, executor)

    # start strategy
    strategy_task = asyncio.create_task(strategy.run())
    # produce ticks
    await produce_synthetic_ticks(queue, executor=executor, n=400, base_price=10.0)
    # give some time for strategy to process remaining events
    await asyncio.sleep(0.5)

    # stop strategy gracefully
    strategy.stop()
    await asyncio.sleep(0.1)
    # print summary
    print("Simulation finished")
    print(f"Total fills: {len(executor.trades)}")
    for f in executor.trades:
        print(f"{f['order_id']}: {f['side'].upper()} {f['quantity']} @ {f['price']:.4f}  fee={f['fee']:.4f} realized={f['realized']:.4f}")
    print("Final positions:", executor.positions)
    print(f"Cash: {executor.cash:.2f}")
    print(f"Unrealized P&L: {executor.unrealized_pnl():.2f}")
    print(f"NAV: {executor.nav():.2f}")

    # export trades
    executor.export_trades_csv('trades.csv')
    print("Trades exported to trades.csv")

if __name__ == '__main__':
    asyncio.run(main())
